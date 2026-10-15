"""Fetch a job posting and extract its description.

Usage:
    python -m jobresume.fetch_job <url> [-o out.json]
    python -m jobresume.fetch_job --text-file pasted_jd.txt [-o out.json]

Strategy: real headless Chromium (plain HTTP gets Cloudflare-blocked on many
career sites) -> schema.org JobPosting JSON-LD if present -> cleaned page text.
If the site blocks us, paste the description into a text file and use --text-file.
"""
import argparse
import glob
import html
import json
import re
import sys

from bs4 import BeautifulSoup

CHROMIUM_GLOBS = ["/opt/pw-browsers/chromium-*/chrome-linux/chrome"]
BLOCK_MARKERS = ("just a moment", "access denied", "verify you are human")


def _chromium_path():
    for pattern in CHROMIUM_GLOBS:
        hits = sorted(glob.glob(pattern))
        if hits:
            return hits[-1]
    return None  # let Playwright find its own browser


def fetch_html(url, timeout_ms=45000):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=_chromium_path(), headless=True)
        page = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ).new_page()
        page.goto(url, wait_until="networkidle", timeout=timeout_ms)
        content = page.content()
        browser.close()
    return content


def _html_to_text(fragment):
    soup = BeautifulSoup(html.unescape(fragment), "html.parser")
    for li in soup.find_all("li"):
        li.insert_before("\n- ")
    for br in soup.find_all(["br", "p", "div", "h1", "h2", "h3", "h4"]):
        br.insert_after("\n")
    return re.sub(r"\n{3,}", "\n\n", soup.get_text()).strip()


def _jobposting_jsonld(soup):
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else data.get("@graph", [data])
        for item in items:
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                return item
    return None


def parse_job(page_html, url=None):
    soup = BeautifulSoup(page_html, "html.parser")
    title = (soup.title.string or "").strip().lower() if soup.title else ""
    if any(m in title for m in BLOCK_MARKERS):
        raise RuntimeError(
            "Blocked by the site's bot protection. Paste the description into a "
            "text file and re-run with --text-file."
        )

    ld = _jobposting_jsonld(soup)
    if ld:
        org = ld.get("hiringOrganization") or {}
        loc = ld.get("jobLocation") or {}
        if isinstance(loc, list):
            loc = loc[0] if loc else {}
        addr = loc.get("address", {}) if isinstance(loc, dict) else {}
        return {
            "source": "json-ld",
            "url": url,
            "title": ld.get("title"),
            "company": org.get("name") if isinstance(org, dict) else org,
            "location": ", ".join(
                filter(None, [addr.get("addressLocality"), addr.get("addressCountry")])
            ),
            "description": _html_to_text(ld.get("description", "")),
        }

    for tag in soup(["script", "style", "nav", "header", "footer", "noscript"]):
        tag.decompose()
    node = soup.find("main") or soup.body or soup
    text = re.sub(r"\n{3,}", "\n\n", node.get_text("\n")).strip()
    h1 = soup.find("h1")
    return {
        "source": "page-text",
        "url": url,
        "title": h1.get_text(strip=True) if h1 else None,
        "company": None,
        "location": None,
        "description": text,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("url", nargs="?")
    ap.add_argument("--text-file", help="pasted job description instead of a URL")
    ap.add_argument("-o", "--out", default="-")
    args = ap.parse_args(argv)

    if args.text_file:
        with open(args.text_file, encoding="utf-8") as f:
            job = {"source": "pasted", "url": None, "title": None,
                   "company": None, "location": None, "description": f.read().strip()}
    elif args.url:
        job = parse_job(fetch_html(args.url), args.url)
    else:
        ap.error("give a URL or --text-file")

    out = json.dumps(job, indent=2, ensure_ascii=False)
    if args.out == "-":
        print(out)
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
