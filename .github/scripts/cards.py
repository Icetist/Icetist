#!/usr/bin/env python3
"""Refreshes the Profile and Toolkit cards (dark + light) with the current GitHub avatar.

The committed SVGs in assets/<theme>/ are the templates. This swaps in the
current avatar and writes the results to <out_dir>.

Usage: GITHUB_TOKEN=... python3 cards.py <out_dir> [login]
"""
import base64, json, os, re, sys, urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = sys.argv[1] if len(sys.argv) > 1 else "dist"
LOGIN = next((a for a in sys.argv[2:] if not a.startswith("--")), os.environ.get("GITHUB_REPOSITORY_OWNER", "Icetist"))
THEMES = ("dark", "light")
CARDS = ("profile", "toolkit")
AVATAR_SIZE = 256
# avatar <image> elements are the ones clipped by these clipPath ids
AVATAR_RE = re.compile(r'(<image href=")data:image/[a-z]+;base64,[^"]*("[^>]*clip-path="url\(#(?:tav|av|fav)\)")')


def get(url, accept="application/vnd.github+json"):
    headers = {"Accept": accept, "User-Agent": f"{LOGIN}-profile-cards"}
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com"):
        headers["Authorization"] = f"bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
        return r.read(), r.headers.get_content_type()


def avatar_href():
    body, _ = get(f"https://api.github.com/users/{LOGIN}")
    url = json.loads(body)["avatar_url"]
    sep = "&" if "?" in url else "?"
    data, mime = get(f"{url}{sep}s={AVATAR_SIZE}", accept="image/*")
    if not mime.startswith("image/"):
        raise ValueError(f"avatar returned {mime}")
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def main():
    try:
        href = avatar_href()
    except Exception as e:  # keep the committed avatar rather than break the cards
        print(f"warning: could not fetch avatar, keeping template image: {e}", file=sys.stderr)
        href = None

    os.makedirs(OUT, exist_ok=True)
    for theme in THEMES:
        for card in CARDS:
            with open(os.path.join(ROOT, "assets", theme, f"{card}.svg"), encoding="utf-8") as f:
                svg = f.read()
            if href:
                svg, n = AVATAR_RE.subn(lambda m: m.group(1) + href + m.group(2), svg)
                if n == 0:
                    raise SystemExit(f"no avatar image found in {theme}/{card}.svg")
            with open(os.path.join(OUT, f"{card}-{theme}.svg"), "w", encoding="utf-8") as f:
                f.write(svg)
    print(f"{LOGIN}: avatar {'refreshed' if href else 'unchanged'}")


if __name__ == "__main__":
    main()
