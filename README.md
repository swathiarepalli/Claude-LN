# Job-tailored resume tool

1. Extract a job posting (uses headless Chromium; falls back to `--text-file` for pasted text):
   `python -m jobresume.fetch_job <url> -o jobs/<name>.json`
2. Write a tailored resume JSON in `resumes/` (copy `resumes/base.json`, reorder and reword only what is true).
3. Render to a one-page PDF:
   `python -m jobresume.render_pdf resumes/<name>.json -o out/<name>.pdf`

Setup: `pip install -r requirements.txt` (Chromium must be installed for Playwright).
