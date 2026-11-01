#!/usr/bin/env python3
"""Refreshes the Profile and Toolkit cards (dark + light) with live GitHub data.

The committed SVGs in assets/<theme>/ are the templates. This swaps in the
current GitHub avatar and fills the "Latest" row with the most recently
pushed public repo, then writes the results to <out_dir>.

Usage: GITHUB_TOKEN=... python3 cards.py <out_dir> [login]
"""
import base64, datetime as dt, html, json, os, re, sys, urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = sys.argv[1] if len(sys.argv) > 1 else "dist"
LOGIN = next((a for a in sys.argv[2:] if not a.startswith("--")), os.environ.get("GITHUB_REPOSITORY_OWNER", "Icetist"))
THEMES = ("dark", "light")
CARDS = ("profile", "toolkit")
AVATAR_SIZE = 256
DESC_MAX = 72
# avatar <image> elements are the ones clipped by these clipPath ids
AVATAR_RE = re.compile(r'(<image href=")data:image/[a-z]+;base64,[^"]*("[^>]*clip-path="url\(#(?:tav|av|fav)\)")')


def get(url, accept="application/vnd.github+json"):
    headers = {"Accept": accept, "User-Agent": f"{LOGIN}-profile-cards"}
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com"):
        headers["Authorization"] = f"bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
        return r.read(), r.headers.get_content_type()


def api(path):
    body, _ = get(f"https://api.github.com{path}")
    return json.loads(body)


def avatar_href(user):
    sep = "&" if "?" in user["avatar_url"] else "?"
    data, mime = get(f"{user['avatar_url']}{sep}s={AVATAR_SIZE}", accept="image/*")
    if not mime.startswith("image/"):
        raise ValueError(f"avatar returned {mime}")
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def ago(iso, now):
    days = (now - dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))).days
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 30:
        return f"{days} days ago"
    months = days // 30
    return f"{months} month{'s' if months > 1 else ''} ago"


def latest_repo(now):
    repos = api(f"/users/{LOGIN}/repos?sort=pushed&per_page=20&type=owner")
    picks = [r for r in repos if not r["fork"] and not r["archived"] and r["name"].lower() != LOGIN.lower()]
    if not picks:
        return None
    r = picks[0]
    desc = (r.get("description") or "").strip() or "No description yet"
    if len(desc) > DESC_MAX:
        desc = desc[:DESC_MAX - 1].rsplit(" ", 1)[0].rstrip(",.;:") + "…"
    lang = r.get("language")
    when = f"Pushed {ago(r['pushed_at'], now)}"
    return {
        "latest-title": f"Latest: {r['name']}",
        "latest-desc": desc,
        "latest-when": f"{lang} · {when}" if lang else when,
    }


def set_text(svg, el_id, value):
    pattern = re.compile(rf'(<text[^>]*\bid="{el_id}"[^>]*>)[^<]*(</text>)')
    out, n = pattern.subn(lambda m: m.group(1) + html.escape(value, quote=False) + m.group(2), svg)
    if n != 1:
        raise SystemExit(f"template is missing <text id=\"{el_id}\">")
    return out


def main():
    now = dt.datetime.now(dt.timezone.utc)
    user = api(f"/users/{LOGIN}")
    try:
        href = avatar_href(user)
    except Exception as e:  # keep the committed avatar rather than break the whole card
        print(f"warning: could not fetch avatar, keeping template image: {e}", file=sys.stderr)
        href = None
    latest = latest_repo(now)
    if latest is None:
        print("warning: no public repos found, keeping template Latest row", file=sys.stderr)

    os.makedirs(OUT, exist_ok=True)
    for theme in THEMES:
        for card in CARDS:
            with open(os.path.join(ROOT, "assets", theme, f"{card}.svg"), encoding="utf-8") as f:
                svg = f.read()
            if href:
                svg, n = AVATAR_RE.subn(lambda m: m.group(1) + href + m.group(2), svg)
                if n == 0:
                    raise SystemExit(f"no avatar image found in {theme}/{card}.svg")
            if card == "profile" and latest:
                for el_id, value in latest.items():
                    svg = set_text(svg, el_id, value)
            with open(os.path.join(OUT, f"{card}-{theme}.svg"), "w", encoding="utf-8") as f:
                f.write(svg)
    print(f"{LOGIN}: avatar {'refreshed' if href else 'unchanged'}, latest = {latest and latest['latest-title']}")


if __name__ == "__main__":
    main()
