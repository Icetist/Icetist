#!/usr/bin/env python3
"""Builds the Activity card (dark + light) from the GitHub GraphQL API.

Usage: GITHUB_TOKEN=... python3 stats.py <out_dir> [login]
       python3 stats.py <out_dir> --demo     (renders sample numbers, no network)
"""
import base64, datetime as dt, json, os, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else "dist"
DEMO = "--demo" in sys.argv
LOGIN = next((a for a in sys.argv[2:] if not a.startswith("--")), os.environ.get("GITHUB_REPOSITORY_OWNER", "Icetist"))

THEMES = {
    "dark": dict(base="#202020", card="#2B2B2B", stroke="#3A3A3A", divider="#3A3A3A",
                 text="#FFFFFF", text2="#C5C5C5", text3="#9A9A9A", accent="#60CDFF"),
    "light": dict(base="#F3F3F3", card="#FBFBFB", stroke="#E5E5E5", divider="#E5E5E5",
                  text="#1A1A1A", text2="#5D5D5D", text3="#8A8A8A", accent="#005FB8"),
}

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    createdAt
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      totalCount
      nodes { stargazerCount }
    }
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar { weeks { contributionDays { date contributionCount } } }
    }
  }
}"""

def gql(variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if "errors" in body:
        raise SystemExit(f"GraphQL error: {body['errors']}")
    return body["data"]["user"]

def fetch():
    today = dt.datetime.now(dt.timezone.utc)
    iso = lambda d: d.strftime("%Y-%m-%dT%H:%M:%SZ")
    first = gql({"login": LOGIN, "from": iso(today - dt.timedelta(days=364)), "to": iso(today)})
    days = {}
    # walk back one year at a time to the account's creation for the all-time numbers
    start_year = int(first["createdAt"][:4])
    for year in range(start_year, today.year + 1):
        frm = dt.datetime(year, 1, 1, tzinfo=dt.timezone.utc)
        to = min(dt.datetime(year, 12, 31, 23, 59, 59, tzinfo=dt.timezone.utc), today)
        u = gql({"login": LOGIN, "from": iso(frm), "to": iso(to)})
        for w in u["contributionsCollection"]["contributionCalendar"]["weeks"]:
            for d in w["contributionDays"]:
                days[d["date"]] = d["contributionCount"]
    repos = first["repositories"]
    return days, sum(n["stargazerCount"] for n in repos["nodes"]), repos["totalCount"], today.date()

def demo():
    import random
    random.seed(7)
    today = dt.date(2026, 10, 29)
    days = {(today - dt.timedelta(days=i)).isoformat(): (random.random() < .55) * random.randint(1, 9) for i in range(900)}
    for i in range(9):
        days[(today - dt.timedelta(days=i)).isoformat()] = 3
    return days, 7, 4, today

def summarise(days, today):
    ordered = sorted(days.items())
    year_ago = (today - dt.timedelta(days=364)).isoformat()
    past_year = sum(c for d, c in ordered if d >= year_ago)
    total = sum(c for _, c in ordered)
    longest = run = 0
    for _, c in ordered:
        run = run + 1 if c else 0
        longest = max(longest, run)
    # current streak: today may still be empty, so start from yesterday in that case
    cur, d = 0, today
    if not days.get(d.isoformat()):
        d -= dt.timedelta(days=1)
    while days.get(d.isoformat()):
        cur += 1
        d -= dt.timedelta(days=1)
    return past_year, total, cur, longest

def font_css():
    css = ""
    for w in (400, 600):
        with open(os.path.join(HERE, "fonts", f"NotoSans-{w}.woff2"), "rb") as f:
            data = base64.b64encode(f.read()).decode()
        css += f"@font-face{{font-family:'NotoFallback';font-weight:{w};src:url(data:font/woff2;base64,{data}) format('woff2');}}"
    return css

FF = "'Segoe UI Variable Text','Segoe UI Variable','Segoe UI',NotoFallback,sans-serif"
FD = "'Segoe UI Variable Display','Segoe UI Variable','Segoe UI',NotoFallback,sans-serif"

def render(theme, tiles, updated, css):
    c = THEMES[theme]
    W, H, M = 1200, 214, 14
    cw, ch = W - 2 * M, H - 2 * M - 8
    col = cw / len(tiles)
    body = ""
    for i, (value, label, note) in enumerate(tiles):
        x = M + col * i + 36
        if i:
            body += f'<line x1="{M + col*i}" x2="{M + col*i}" y1="{M+32}" y2="{M+ch-32}" stroke="{c["divider"]}"/>'
        body += (f'<text x="{x}" y="{M+84}" font-family="{FD}" font-weight="600" font-size="46" fill="{c["text"]}">{value}</text>'
                 f'<text x="{x}" y="{M+118}" font-family="{FF}" font-size="18" fill="{c["text2"]}">{label}</text>'
                 f'<text x="{x}" y="{M+146}" font-family="{FF}" font-size="15" fill="{c["text3"]}">{note}</text>')
    op = ".28" if theme == "light" else ".55"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="GitHub activity">'
            f'<style>{css}</style><defs><filter id="sh" x="-10%" y="-10%" width="120%" height="130%">'
            f'<feDropShadow dx="0" dy="5" stdDeviation="9" flood-color="#000" flood-opacity="{op}"/></filter></defs>'
            f'<rect x="{M}" y="{M}" width="{cw}" height="{ch}" rx="10" fill="{c["card"]}" filter="url(#sh)"/>'
            f'<rect x="{M+.5}" y="{M+.5}" width="{cw-1}" height="{ch-1}" rx="9.5" fill="none" stroke="{c["stroke"]}"/>'
            f'{body}'
            f'<text x="{W-M-24}" y="{M+34}" text-anchor="end" font-family="{FF}" font-size="13" fill="{c["text3"]}">Updated {updated}</text>'
            '</svg>')

def main():
    days, stars, repos, today = demo() if DEMO else fetch()
    past_year, total, cur, longest = summarise(days, today)
    plural = lambda n, w: f"{n:,} {w}{'' if n == 1 else 's'}"
    tiles = [
        (f"{past_year:,}", "Contributions", "in the past year"),
        (plural(cur, "day"), "Current streak", "and counting" if cur else "starts today"),
        (plural(longest, "day"), "Longest streak", f"{total:,} contributions all time"),
        (f"{stars:,}", "Stars earned", f"across {plural(repos, 'public repo')}"),
    ]
    updated = f"{today.day} {today.strftime('%b %Y')}"
    css = font_css()
    os.makedirs(OUT, exist_ok=True)
    for theme in THEMES:
        with open(os.path.join(OUT, f"stats-{theme}.svg"), "w") as f:
            f.write(render(theme, tiles, updated, css))
    print(f"{LOGIN}: {past_year} past year, streak {cur}/{longest}, {stars} stars, {repos} repos")

if __name__ == "__main__":
    main()
