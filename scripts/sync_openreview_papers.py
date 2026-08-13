#!/usr/bin/env python3
"""Download accepted TPM 2026 papers and refresh the website paper index."""

from __future__ import annotations

import getpass
import json
import os
import re
import sys
from argparse import ArgumentParser
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
PAPERS_DIRECTORY = ROOT / "public" / "papers"
PAPERS_INDEX = ROOT / "src" / "content" / "papers.json"
SUBMISSION_INVITATION = "auai.org/UAI/2026/Workshop/TPM/-/Submission"
ACCEPTED_VENUE = "TPM 2026"
OPENREVIEW_BASE_URL = "https://api2.openreview.net"


def content_value(note: dict, field: str, default):
    value = note.get("content", {}).get(field, {})
    return value.get("value", default) if isinstance(value, dict) else value


def credentials() -> tuple[str, str]:
    username = os.environ.get("OPENREVIEW_USERNAME") or input("OpenReview email: ").strip()
    password = os.environ.get("OPENREVIEW_PASSWORD") or getpass.getpass("OpenReview password: ")

    if not username or not password:
        raise RuntimeError("OpenReview username and password are required")

    return username, password


def api_request(path: str, token: str | None = None, *, data: dict | None = None) -> bytes:
    body = json.dumps(data).encode() if data is not None else None
    headers = {
        "Accept": "application/json",
        "User-Agent": "tpm2026-paper-sync/1.0",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        token_value = token[len("Bearer ") :] if token.startswith("Bearer ") else token
        headers["Authorization"] = f"Bearer {token_value}"

    request = Request(f"{OPENREVIEW_BASE_URL}{path}", data=body, headers=headers)
    try:
        with urlopen(request, timeout=60) as response:
            return response.read()
    except HTTPError as error:
        detail = error.read().decode(errors="replace")
        raise RuntimeError(f"OpenReview API returned {error.code}: {detail}") from error


def authenticate() -> str:
    existing_token = os.environ.get("OPENREVIEW_TOKEN")
    if existing_token:
        return existing_token

    username, password = credentials()
    login = json.loads(api_request("/login", data={"id": username, "password": password}))
    if login.get("mfaPending"):
        raise RuntimeError(
            "This account requires MFA. Set OPENREVIEW_TOKEN to a current API token and retry."
        )
    if not login.get("token"):
        raise RuntimeError("OpenReview login did not return an API token")
    return login["token"]


def normalized_pdf_text(value: str) -> str:
    def join_wrapped_word(match: re.Match[str]) -> str:
        prefix, continuation = match.groups()
        separator = "-" if "-" in prefix else ""
        return f"{prefix}{separator}{continuation}"

    value = re.sub(
        r"\b([A-Za-z]+(?:-[A-Za-z]+)*)-\s+([a-z][A-Za-z]*)",
        join_wrapped_word,
        value,
    )
    value = re.sub(r"\b([A-Z]{2,})-\s+([A-Z]{2,})\b", r"\1\2", value)
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"\s+([,.;:!?%])", r"\1", value)
    value = re.sub(r"\b(Code):(?=https?://)", r"\1: ", value, flags=re.IGNORECASE)
    return re.sub(r"(?<=github\.)\s+(?=com/)", "", value).strip()


def abstract_from_pdf(pdf_path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise RuntimeError(
            "PDF backfill requires pypdf. Install it with `python3 -m pip install pypdf`."
        ) from error

    text = "\n".join((page.extract_text() or "") for page in PdfReader(pdf_path).pages[:2])
    match = re.search(
        r"(?:^|\n)\s*abstract(?:\s*[—–-]\s*|\s*\n)(?P<abstract>.*?)"
        r"(?=\n\s*(?:index\s+terms|(?:1|I)\.?\s+(?:introduction|I\s*N\s*T\s*R\s*O\s*D\s*U\s*C\s*T\s*I\s*O\s*N)\b))",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        raise RuntimeError(f"Could not identify an abstract in {pdf_path}")
    return normalized_pdf_text(match.group("abstract"))


def backfill_abstracts() -> int:
    papers = json.loads(PAPERS_INDEX.read_text())
    for position, paper in enumerate(papers, start=1):
        pdf_url = paper.get("pdfUrl")
        if not pdf_url:
            raise RuntimeError(f"Paper {paper['id']} has no local PDF")
        paper["abstract"] = abstract_from_pdf(ROOT / "public" / pdf_url)
        print(f"[{position:02d}/{len(papers):02d}] {paper['title']}")

    PAPERS_INDEX.write_text(json.dumps(papers, ensure_ascii=False, indent=2) + "\n")
    print(f"\nBackfilled {len(papers)} abstracts in {PAPERS_INDEX}")
    return 0


def main() -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument(
        "--abstracts-from-pdfs",
        action="store_true",
        help="Backfill abstracts from the PDFs already stored in public/papers without OpenReview access.",
    )
    args = parser.parse_args()
    if args.abstracts_from_pdfs:
        return backfill_abstracts()

    token = authenticate()
    query = urlencode(
        {
            "invitation": SUBMISSION_INVITATION,
            "content.venue": ACCEPTED_VENUE,
            "limit": 1000,
        }
    )
    notes = json.loads(api_request(f"/notes?{query}", token))["notes"]
    notes.sort(key=lambda note: content_value(note, "title", "").casefold())

    if not notes:
        raise RuntimeError("OpenReview returned no accepted TPM 2026 submissions")

    PAPERS_DIRECTORY.mkdir(parents=True, exist_ok=True)
    papers = []

    for position, note in enumerate(notes, start=1):
        title = content_value(note, "title", "").strip()
        authors = content_value(note, "authors", [])
        abstract = content_value(note, "abstract", "").strip()
        note_id = note["id"]
        attachment_query = urlencode({"id": note_id, "name": "pdf"})
        pdf = api_request(f"/attachment?{attachment_query}", token)

        if not title or not authors or not abstract:
            raise RuntimeError(f"Submission {note_id} is missing title, author, or abstract metadata")
        if not pdf.startswith(b"%PDF"):
            raise RuntimeError(f"Submission {note_id} did not return a valid PDF")

        pdf_name = f"{note_id}.pdf"
        (PAPERS_DIRECTORY / pdf_name).write_bytes(pdf)
        papers.append(
            {
                "id": note_id,
                "title": title,
                "authors": ", ".join(authors),
                "abstract": abstract,
                "status": "Accepted",
                "pdfUrl": f"papers/{pdf_name}",
                "forumUrl": f"https://openreview.net/forum?id={note_id}",
                "videoUrl": None,
                "session": None,
                "placeholder": False,
            }
        )
        print(f"[{position:02d}/{len(notes):02d}] {title}")

    PAPERS_INDEX.write_text(json.dumps(papers, ensure_ascii=False, indent=2) + "\n")
    print(f"\nDownloaded {len(papers)} papers to {PAPERS_DIRECTORY}")
    print(f"Updated {PAPERS_INDEX}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1)
