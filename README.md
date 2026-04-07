# TPM 2026 Website

Static Astro website for the 9th Workshop on Tractable Probabilistic Modeling at UAI 2026.

The site is configured for GitHub Pages deployment at:

- `https://tractable-probabilistic-modeling.github.io/tpm2026/`

## Stack

- Astro
- `@astrojs/react`
- HeroUI v3
- Astro content collections

The site is prerendered as static HTML and keeps JavaScript to a minimum.

## Local development

Install dependencies:

```bash
npm install
```

Start the dev server:

```bash
npm run dev -- --host
```

Build the site:

```bash
npm run build
```

Preview the production build:

```bash
npm run preview
```

## Content structure

Editable content lives in `src/content/`.

- `src/content/site.json`: workshop-wide metadata, deadlines, feature flags
- `src/content/menu.json`: main navigation items
- `src/content/pages/*.md`: page copy for home, CFP, program, and papers
- `src/content/speakers.json`: invited speaker data
- `src/content/organizers.json`: organizer data
- `src/content/papers.json`: accepted paper entries or placeholders
- `src/content/workshop.json`: tentative workshop schedule

## Assets

- `src/assets/images/`: site imagery
- `src/assets/organizers/`: organizer photos
- `public/`: favicons, manifest, and future downloadable files

## Toggling accepted papers

The accepted papers section is controlled by `showAcceptedPapers` in `src/content/site.json`.

- `false`: hide the navigation item and show a coming-soon page
- `true`: show the navigation item and render the paper entries from the collection

## Deployment

GitHub Pages deployment is configured in `.github/workflows/deploy.yml` using Astro's official GitHub Action.

Repository settings should use:

- Pages source: `GitHub Actions`

## Notes

- OpenReview URL is currently `TBD`
- Speaker personal websites are currently `TBD`
- Submission template URL is currently `TBD`
