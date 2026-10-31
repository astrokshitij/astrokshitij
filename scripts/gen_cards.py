"""Build one SVG card per public repo and refresh the projects table in README.md.

Run locally:   python scripts/gen_cards.py
Runs weekly and on every push via .github/workflows/refresh-projects.yml.
Standard library only.
"""
import json
import os
import subprocess
import textwrap
import urllib.error
import urllib.request
from datetime import datetime
from html import escape
from pathlib import Path

USER = "astrokshitij"
MAX_REPOS = 6
ROOT = Path(__file__).resolve().parent.parent
CARDS = ROOT / "assets" / "cards"
README = ROOT / "README.md"

FONT = "-apple-system, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
LANG_COLORS = {
    "TypeScript": "#3178c6",
    "JavaScript": "#f1e05a",
    "Python": "#3776ab",
    "Jupyter Notebook": "#da5b0b",
    "HTML": "#e34c26",
    "CSS": "#9b59d0",
    "C++": "#f34b7d",
    "Shell": "#89e051",
}


def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}", headers={"User-Agent": "profile-cards"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.URLError:
        # Local machines behind a TLS-intercepting proxy: fall back to the GitHub CLI.
        out = subprocess.run(["gh", "api", path], capture_output=True, text=True, check=True)
        return json.loads(out.stdout)


def card_svg(repo):
    desc = repo.get("description") or "No description yet."
    wrapped = textwrap.wrap(desc, 56)
    lines = wrapped[:3]
    if len(wrapped) > 3:
        lines[-1] = lines[-1].rstrip(".,") + "…"
    lang = repo.get("language") or "Other"
    color = LANG_COLORS.get(lang, "#8b95b0")
    pushed = datetime.strptime(repo["pushed_at"], "%Y-%m-%dT%H:%M:%SZ").strftime("%d %b %Y")
    desc_svg = "".join(
        f'<tspan x="24" dy="{0 if i == 0 else 21}">{escape(line)}</tspan>' for i, line in enumerate(lines)
    )
    name = escape(repo["name"])
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="440" height="160" viewBox="0 0 440 160" role="img" aria-label="{name}: {escape(desc)}">
  <style>
    .bg {{ fill: #ffffff; stroke: #d0d7de; }}
    .title {{ fill: #0969da; }}
    .desc {{ fill: #59636e; }}
    .meta {{ fill: #59636e; }}
    @media (prefers-color-scheme: dark) {{
      .bg {{ fill: #0d1117; stroke: #30363d; }}
      .title {{ fill: #4493f8; }}
      .desc {{ fill: #9198a1; }}
      .meta {{ fill: #9198a1; }}
    }}
  </style>
  <rect class="bg" x="0.5" y="0.5" width="439" height="159" rx="8" stroke-width="1"/>
  <g font-family="{FONT}">
    <text class="title" x="24" y="40" font-size="17" font-weight="600">{name}</text>
    <text class="desc" x="24" y="68" font-size="14">{desc_svg}</text>
    <circle cx="30" cy="132" r="5.5" fill="{color}"/>
    <text class="meta" x="42" y="136" font-size="13">{escape(lang)}</text>
    <text class="meta" x="{54 + int(len(lang) * 7.2) + 20}" y="136" font-size="13">Updated {pushed}</text>
  </g>
</svg>
"""


def main():
    repos = [
        r
        for r in api(f"/users/{USER}/repos?per_page=100&type=owner")
        if not r["fork"] and not r["archived"] and r["name"].lower() != USER.lower()
    ]
    repos.sort(key=lambda r: r["pushed_at"], reverse=True)
    repos = repos[:MAX_REPOS]

    CARDS.mkdir(parents=True, exist_ok=True)
    for old in CARDS.glob("*.svg"):
        old.unlink()
    for r in repos:
        (CARDS / f"{r['name']}-card.svg").write_text(card_svg(r), encoding="utf-8")

    cells = [
        f'<a href="{r["html_url"]}"><img src="assets/cards/{r["name"]}-card.svg" alt="{escape(r["name"])}" width="100%"></a>'
        for r in repos
    ]
    rows = []
    for i in range(0, len(cells), 2):
        pair = cells[i : i + 2]
        tds = "".join(f'\n    <td width="50%">{c}</td>' for c in pair)
        rows.append(f"  <tr>{tds}\n  </tr>")
    table = "<table>\n" + "\n".join(rows) + "\n</table>"

    text = README.read_text(encoding="utf-8")
    start, end = "<!-- PROJECTS:START -->", "<!-- PROJECTS:END -->"
    head, rest = text.split(start, 1)
    _, tail = rest.split(end, 1)
    README.write_text(f"{head}{start}\n{table}\n{end}{tail}", encoding="utf-8")
    print("cards:", [r["name"] for r in repos])


if __name__ == "__main__":
    main()
