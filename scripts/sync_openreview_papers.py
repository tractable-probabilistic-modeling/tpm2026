#!/usr/bin/env python3
"""Download accepted TPM 2026 papers and refresh the website paper index."""

from __future__ import annotations

import getpass
import json
import os
import sys
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


def main() -> int:
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
        note_id = note["id"]
        attachment_query = urlencode({"id": note_id, "name": "pdf"})
        pdf = api_request(f"/attachment?{attachment_query}", token)

        if not title or not authors:
            raise RuntimeError(f"Submission {note_id} is missing title or author metadata")
        if not pdf.startswith(b"%PDF"):
            raise RuntimeError(f"Submission {note_id} did not return a valid PDF")

        pdf_name = f"{note_id}.pdf"
        (PAPERS_DIRECTORY / pdf_name).write_bytes(pdf)
        papers.append(
            {
                "id": note_id,
                "title": title,
                "authors": ", ".join(authors),
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
