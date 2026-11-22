# HARSHx17 animated SVG README

## What this contains

- `README.md`: the ready-to-use image stack. Tiles are individually clickable at exactly 32.5% width.
- `scripts/render_readme_cards.py`: the single Python renderer and optional GitHub GraphQL fetcher.
- `data/contributions.json`: initially empty on purpose, not fabricated data. The Action replaces it with true daily contributions.
- `cards/*.svg`: generated SVGs with embedded, subsetted WOFF fonts, CSS keyframes, SMIL decorative animation and reduced-motion fallbacks.
- `.github/workflows/refresh-cards.yml`: daily refresh at 03:17 UTC, manual dispatch, and commit.

## Install

Copy files into the `HARSHx17/HARSHx17` repository, preserving paths. Existing `README.md` will be replaced, so back it up first. Add the workflow alongside your existing workflows; do not delete any contribution-snake workflow you wish to keep.

In GitHub repository Settings > Actions > General, allow **Read and write permissions** for the workflow token if organization policy requires it. The workflow also sets `contents: write` explicitly.

Run the `Refresh profile cards` workflow manually once. The default `GITHUB_TOKEN` is used to query your GitHub contributions. The JSON and SVGs will be committed. Scheduled Actions are best-effort and can run late.

## Local development

```bash
sudo apt-get install fonts-inter fonts-dejavu-core
python -m pip install 'fonttools[woff]>=4.55,<5'
python scripts/render_readme_cards.py
STATIC=1 python scripts/render_readme_cards.py
GITHUB_TOKEN=ghp_YOUR_TOKEN python scripts/render_readme_cards.py --refresh
```

Never commit a GitHub token. For macOS, adjust `FONT_CANDIDATES` in the script to point to your licensed local font files. Font files are only embedded into the generated cards, never redistributed separately.

**Important:** SVG image formats are supported in GitHub READMEs, but animation behavior can vary by GitHub image proxy, browser, platform and reduced-motion settings. Use GitHub-rendered README to test. `STATIC=1` renders final-state cards, but will overwrite the animation SVGs until you rerun normally.

## Customization

- Theme colours `BG`, `PANEL`, `STROKE`, `INK`, `MUTED`, `ACCENT`, `CYAN`, `BLUE` are at the top of the Python script.
- Headline and biography are in `hero()`.
- Featured projects are in `FEATURES`. They are projects mentioned in your current README, **not verified public repository URLs**. All currently point to the portfolio. Replace these with actual project GitHub URLs after confirming the repositories are public.
- Optional portrait: `PORTRAIT_PATH=/path/to/portrait.png python scripts/render_readme_cards.py`. This embeds the portrait in the SVG. Avoid putting personal photos in public repos without consent.
- The existing portfolio page was not machine-readable during creation, so the theme is based on the current README's green/cyan palette, not a verified exact site CSS extraction.
- If an existing daily contribution JSON refresh workflow already exists, merge the `Install fonts and font subsetter`, `Render` and `git add cards/` steps into it instead of scheduling a second workflow.

## Data semantics

GitHub GraphQL `contributionCalendar` supplies daily contribution counts for the queried user. `CURRENT STREAK` is defined as the number of consecutive positive-count days ending today, or yesterday if today has zero (to avoid penalizing a day that has not finished). `ACTIVE DAYS` counts nonzero days in the one-year fetch. `BUSIEST DAY` is the date with maximum contributions in that period. Monthly chart covers the last 12 calendar months, with partial end month.
