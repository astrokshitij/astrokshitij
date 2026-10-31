"""Build one SVG card per public repo and refresh the projects table in README.md.

Run locally:   python scripts/gen_cards.py
Runs weekly and on every push via .github/workflows/refresh-projects.yml.
Standard library only.
"""
import json
import os
import subprocess
import textwrap
import urllib.request
from datetime import datetime
from html import escape
from pathlib import Path

USER = "astrokshitij"
MAX_REPOS = 6
ROOT = Path(__file__).resolve().parent.parent
CARDS = ROOT / "assets" / "cards"
README = ROOT / "README.md"

FONT = "'Segoe UI', -apple-system, 'Helvetica Neue', Arial, sans-serif"
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
    lines = textwrap.wrap(desc, 54)[:3]
    if len(textwrap.wrap(desc, 54)) > 3:
        lines[-1] = lines[-1].rstrip(".,") + "…"
    lang = repo.get("language") or "Other"
    color = LANG_COLORS.get(lang, "#8b95b0")
    pushed = datetime.strptime(repo["pushed_at"], "%Y-%m-%dT%H:%M:%SZ").strftime("%d %b %Y")
    desc_svg = "".join(
        f'<tspan x="28" dy="{0 if i == 0 else 21}">{escape(line)}</tspan>' for i, line in enumerate(lines)
    )
    name = escape(repo["name"])
    stars = repo.get("stargazers_count", 0)
    star_svg = (
        f'<text x="410" y="152" text-anchor="end" font-size="13" fill="#7f8aa6">★ {stars}</text>' if stars else ""
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="440" height="176" viewBox="0 0 440 176" role="img" aria-label="{name}: {escape(desc)}">
  <defs>
    <linearGradient id="card" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0c1224"/><stop offset="1" stop-color="#17101c"/></linearGradient>
    <linearGradient id="bar" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#ffd08a"/><stop offset="1" stop-color="#ff7a1a"/></linearGradient>
  </defs>
  <rect x="0.5" y="0.5" width="439" height="175" rx="16" fill="url(#card)" stroke="#232c46"/>
  <rect x="28" y="22" width="34" height="3" rx="1.5" fill="url(#bar)"/>
  <g font-family="{FONT}">
    <text x="28" y="56" font-size="20" font-weight="700" fill="#f4f6fc">{name}</text>
    <text x="28" y="84" font-size="14" fill="#9aa6c4">{desc_svg}</text>
    <circle cx="34" cy="148" r="5" fill="{color}"/>
    <text x="46" y="152" font-size="13" fill="#c9d3ea">{escape(lang)}</text>
    <text x="{58 + int(len(lang) * 7.2) + 22}" y="152" font-size="13" fill="#7f8aa6">updated {pushed}</text>
    {star_svg}
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
        (CARDS / f"{r['name']}.svg").write_text(card_svg(r), encoding="utf-8")

    cells = [
        f'<a href="{r["html_url"]}"><img src="assets/cards/{r["name"]}.svg" alt="{escape(r["name"])}" width="100%"></a>'
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
