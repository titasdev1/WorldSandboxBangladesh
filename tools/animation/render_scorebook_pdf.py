#!/usr/bin/env python3
"""Render the A-Square Markdown scorebook to a paginated review PDF."""
from __future__ import annotations

import argparse
import html
from pathlib import Path

import markdown
from weasyprint import HTML


CSS = r"""
@page {
  size: A4;
  margin: 19mm 18mm 21mm;
  @top-left {
    content: "A-SQUARE  /  FILM ART DIRECTION";
    color: #66717d;
    font: 700 8pt "DejaVu Sans";
    letter-spacing: 1.2pt;
  }
  @top-right {
    content: "27 NOVEMBER 2026";
    color: #8a929b;
    font: 8pt "DejaVu Sans";
  }
  @bottom-left {
    content: "PROJECT A-SQUARE  •  INTERNAL ART-DIRECTION SCOREBOOK";
    color: #8a929b;
    font: 7pt "DejaVu Sans";
  }
  @bottom-right {
    content: counter(page);
    color: #344253;
    font: 700 9pt "DejaVu Sans";
  }
}
@page:first {
  margin: 0;
  @top-left { content: ""; }
  @top-right { content: ""; }
  @bottom-left { content: ""; }
  @bottom-right { content: ""; }
}
* { box-sizing: border-box; }
html { color: #1e2834; background: #fff; }
body {
  margin: 0;
  font-family: "DejaVu Sans", sans-serif;
  font-size: 9.35pt;
  line-height: 1.52;
  color: #26313d;
}
.cover {
  height: 297mm;
  padding: 37mm 23mm 26mm;
  color: #f4f5f4;
  background: #101e2a;
  page-break-after: always;
  position: relative;
}
.cover .eyebrow {
  color: #9ec9c2;
  font-size: 9pt;
  letter-spacing: 3pt;
  font-weight: 700;
  text-transform: uppercase;
  margin: 0 0 28mm;
}
.cover h1 {
  color: #f7f3e9;
  font-size: 34pt;
  line-height: 1.08;
  max-width: 150mm;
  margin: 0 0 8mm;
  letter-spacing: -1.1pt;
}
.cover .subtitle {
  color: #a8c7c6;
  font-size: 14pt;
  line-height: 1.4;
  max-width: 140mm;
  margin-bottom: 30mm;
}
.cover .rule {
  width: 60mm;
  height: 1.2mm;
  background: #c99b5c;
  margin: 0 0 14mm;
}
.cover .meta {
  color: #c5d0d4;
  font-size: 9pt;
  line-height: 1.9;
}
.cover .footer {
  position: absolute;
  left: 23mm;
  bottom: 24mm;
  color: #91a2ad;
  font-size: 8pt;
  letter-spacing: 1pt;
}
.contents {
  page-break-after: always;
}
.contents h1 {
  color: #183445;
  font-size: 24pt;
  border-bottom: 2px solid #c99b5c;
  padding-bottom: 5mm;
  margin: 0 0 8mm;
}
.contents ul {
  list-style: none;
  margin: 0;
  padding-left: 5mm;
}
.contents > ul { padding-left: 0; }
.contents li { margin: 0 0 2.3mm; }
.contents a {
  color: #2a5262;
  text-decoration: none;
}
.contents ul ul {
  border-left: 1px solid #d8e0e2;
  margin: 2mm 0 3mm 2mm;
  padding-left: 5mm;
  font-size: 8.3pt;
}
.markdown h1 {
  color: #16384a;
  font-size: 22pt;
  line-height: 1.16;
  margin: 0 0 8mm;
  padding-bottom: 3mm;
  border-bottom: 1.4px solid #c99b5c;
  page-break-after: avoid;
}
.markdown h1:not(:first-of-type) {
  page-break-before: always;
  padding-top: 3mm;
}
.markdown h2 {
  color: #1b5662;
  font-size: 14pt;
  margin: 9mm 0 3mm;
  page-break-after: avoid;
}
.markdown h3 {
  color: #8b6336;
  font-size: 10.5pt;
  margin: 6mm 0 2mm;
  page-break-after: avoid;
}
.markdown p { margin: 0 0 3.3mm; orphans: 3; widows: 3; }
.markdown strong { color: #1b3342; }
.markdown em { color: #4a5b66; }
.markdown ul, .markdown ol {
  margin: 1mm 0 4mm;
  padding-left: 7mm;
}
.markdown li { margin: 0 0 1.8mm; }
.markdown blockquote {
  margin: 4mm 0;
  padding: 3mm 5mm;
  border-left: 3px solid #c99b5c;
  background: #f4f6f4;
  color: #4d5b65;
}
.markdown code {
  font-family: "DejaVu Sans Mono", monospace;
  font-size: 8pt;
  background: #edf1f1;
  padding: 0.3mm 0.8mm;
  border-radius: 1mm;
}
.markdown pre {
  white-space: pre-wrap;
  background: #162633;
  color: #e7eeee;
  padding: 4mm;
  border-radius: 2mm;
  font: 7.4pt/1.45 "DejaVu Sans Mono", monospace;
  page-break-inside: avoid;
}
.markdown pre code { background: transparent; color: inherit; padding: 0; }
.markdown hr {
  border: 0;
  border-top: 1px solid #d7dfe0;
  margin: 7mm 0;
}
.markdown a { color: #276b76; }
.markdown table {
  width: 100%;
  border-collapse: collapse;
  margin: 4mm 0 6mm;
  font-size: 8.2pt;
}
.markdown th {
  text-align: left;
  background: #1a4353;
  color: white;
  padding: 2.2mm;
}
.markdown td {
  border: 1px solid #dce2e3;
  padding: 2mm;
  vertical-align: top;
}
.markdown tr { page-break-inside: avoid; }
"""
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    source = args.input.read_text(encoding="utf-8")
    md = markdown.Markdown(extensions=["extra", "toc", "sane_lists", "tables"])
    body = md.convert(source)
    toc = md.toc or "<p>Contents will be built from the document headings.</p>"

    title = "A-Square Film Art Direction Scorebook"
    subtitle = "Shariatpur riverfront • Delta Command • original title reveal • operator performance"
    cover = f"""
    <section class="cover">
      <div class="eyebrow">PROJECT A-SQUARE / CINEMATIC ART & ANIMATION</div>
      <h1>{html.escape(title)}</h1>
      <div class="subtitle">{html.escape(subtitle)}</div>
      <div class="rule"></div>
      <div class="meta">
        Revision: 27 November 2026<br>
        Offline authoring: Blender 5.2.5 LTS<br>
        Runtime target: Godot 4.4.1 Android<br>
        Scope: shot direction, performance, environment art, camera, materials, lighting and production prompts<br>
        Status: production direction; visual approval remains a separate gate
      </div>
      <div class="footer">ORIGINAL BANGLADESH-ROOTED GAME CINEMATICS</div>
    </section>
    """
    document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>{CSS}</style>
</head>
<body>
{cover}
<nav class="contents"><h1>Contents</h1>{toc}</nav>
<main class="markdown">{body}</main>
</body>
</html>"""
    args.output.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=document, base_url=str(args.input.parent.resolve())).write_pdf(args.output)
    if not args.output.is_file() or args.output.stat().st_size < 20_000:
        raise SystemExit("PDF_EXPORT_GATE: PDF missing or unexpectedly small.")
    print(f"PDF_EXPORT_PASS: {args.output} ({args.output.stat().st_size} bytes)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
