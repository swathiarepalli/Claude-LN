"""Render a resume JSON (see resumes/base.json) to a one-page A4 PDF.

Usage:
    python -m jobresume.render_pdf resumes/uber_302643.json -o out/Swathi_Arepalli_Uber.pdf
"""
import argparse
import html
import json
import os
import sys

from jobresume.fetch_job import _chromium_path

CSS = """
@page { size: A4; margin: 0; }
* { box-sizing: border-box; }
body { margin: 0; font-family: Lato, 'Carlito', 'Helvetica Neue', Arial, sans-serif;
       font-size: 9.6pt; line-height: 1.32; color: #222; }
.page { display: flex; width: 210mm; height: 297mm; overflow: hidden; }
.side { width: 60mm; background: #2c3e5c; color: #fff; padding: 14mm 6mm 0 7mm; }
.stripe { width: 2.4mm; background: #3d8ea0; }
.main { flex: 1; padding: 9mm 8mm 0 8mm; }
.side h2 { font-size: 10.5pt; letter-spacing: .5px; margin: 0 0 6px; }
.side section { margin-bottom: 15px; }
.chip { background: rgba(255,255,255,.13); padding: 1.5px 4px; margin: 0 0 4px;
        font-size: 8.6pt; display: block; }
.side .item { margin-bottom: 9px; }
.side .t { font-weight: 700; font-size: 9pt; }
.side .s { color: #c9d1de; font-size: 8.6pt; }
.side .lv { color: #c9d1de; font-style: italic; font-size: 8pt; }
h1 { font-size: 24pt; font-weight: 400; color: #2c3e5c; margin: 0 0 6px; }
.summary { text-align: justify; margin: 0 0 8px; }
.contact { background: #2c3e5c; color: #fff; padding: 5px 8px; margin: 0 0 10px; width: 92%;
           display: grid; grid-template-columns: 1fr 1fr; font-size: 8.8pt; }
h3 { color: #2c3e5c; font-size: 11.5pt; letter-spacing: .5px; margin: 0 0 5px; }
.job { margin-bottom: 6px; }
.jt { font-weight: 700; font-size: 10.2pt; }
.jc { color: #444; }
.jd { display: flex; justify-content: space-between; width: 92%; color: #3d8ea0;
      font-style: italic; font-size: 8.5pt; }
ul { margin: 2px 0 0; padding-left: 16px; }
li { margin-bottom: 1.5px; text-align: justify; }
li::marker { color: #3d8ea0; }
"""


def esc(s):
    return html.escape(s or "")


def build_html(r):
    c = r["contact"]
    skills = "".join(f'<span class="chip">{esc(s)}</span>' for s in r["skills"])
    edu = "".join(
        f'<div class="item"><div class="t">{esc(e["degree"])}</div>'
        f'<div class="s">{esc(e["school"])}<br>{esc(e["years"])}</div></div>'
        for e in r["education"]
    )
    langs = "".join(
        f'<div class="t">{esc(l["name"])}</div><div class="lv">{esc(l["level"])}</div>'
        for l in r["languages"]
    )
    certs = "".join(
        f'<div class="item"><div class="t">{esc(x["name"])}</div>'
        f'<div class="s">{esc(x["issuer"])}</div></div>'
        for x in r["certifications"]
    )
    jobs = "".join(
        f'<div class="job"><div class="jt">{esc(j["title"])}</div>'
        f'<div class="jc">{esc(j["company"])}</div>'
        f'<div class="jd"><span>{esc(j["dates"])}</span><span>{esc(j["location"])}</span></div>'
        f'<ul>{"".join(f"<li>{esc(b)}</li>" for b in j["bullets"])}</ul></div>'
        for j in r["experience"]
    )
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>{esc(r["name"])} – Resume</title><style>{CSS}</style></head><body>
<div class="page">
 <div class="side">
  <section><h2>SKILLS</h2>{skills}</section>
  <section><h2>EDUCATION</h2>{edu}</section>
  <section><h2>LANGUAGES</h2>{langs}</section>
  <section><h2>CERTIFICATIONS</h2>{certs}</section>
 </div><div class="stripe"></div>
 <div class="main">
  <h1>{esc(r["name"])}</h1>
  <p class="summary">{esc(r["summary"])}</p>
  <div class="contact"><span>{esc(c["email"])}</span><span>{esc(c["phone"])}</span>
   <span>{esc(c["location"])}</span><span>{esc(c["linkedin"])}</span></div>
  <h3>WORK EXPERIENCE</h3>{jobs}
 </div>
</div></body></html>"""


def render(resume_path, out_path):
    from playwright.sync_api import sync_playwright

    with open(resume_path, encoding="utf-8") as f:
        resume = json.load(f)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=_chromium_path(), headless=True)
        page = browser.new_page()
        page.set_content(build_html(resume))
        overflow = page.evaluate(
            "document.querySelector('.main').scrollHeight - document.querySelector('.page').clientHeight"
        )
        page.pdf(path=out_path, format="A4", print_background=True)
        browser.close()
    if overflow > 0:
        print(f"WARNING: content overflows one page by ~{overflow}px", file=sys.stderr)
    return out_path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("resume")
    ap.add_argument("-o", "--out", required=True)
    args = ap.parse_args(argv)
    print(render(args.resume, args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
