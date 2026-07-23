import argparse
import csv
import re
import sys
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(x, **k):
        return x

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124 Safari/537.36")
BASE = "https://libgen.li/index.php"
MD5_RE = re.compile(r"md5=([a-f0-9]{32})", re.I)
HEX32_RE = re.compile(r"([a-f0-9]{32})", re.I)
TR_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
TD_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S | re.I)
EDITION_RE = re.compile(r"edition\.php\?id=(\d+)", re.I)
EDITION_ANCHOR_RE = re.compile(r"(<a\b(?:(?!</a>).)*?edition\.php.*?</a>)", re.S | re.I)
WHOSWHO_RE = re.compile(r"who[’'ʼ`]?s\s+who", re.I)


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, d):
        self.parts.append(d)


def clean(cell):
    p = _Text()
    p.feed(cell)
    return re.sub(r"\s+", " ", "".join(p.parts)).strip()


def title_of(cell):
    m = EDITION_ANCHOR_RE.search(cell)
    return clean(m.group(1)) if m else clean(cell)


def fetch(query, page, res=100):
    params = {
        "req": query, "columns[]": "t", "objects[]": "f", "topics[]": "l",
        "res": str(res), "gmode": "on", "filesuns": "all", "page": str(page),
    }
    qs = urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(BASE + "?" + qs, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def parse_rows(html):
    body = html.split("<tbody>", 1)[-1].split("</tbody>", 1)[0] if "<tbody>" in html else html
    out = []
    for row in TR_RE.findall(body):
        cells = TD_RE.findall(row)
        if len(cells) < 9:
            continue
        m = MD5_RE.search(row)
        if not m:
            hexes = HEX32_RE.findall(row)
            if not hexes:
                continue
            md5 = hexes[0].lower()
        else:
            md5 = m.group(1).lower()
        ed = EDITION_RE.search(row)
        title_cell = cells[1] if len(cells) >= 10 else cells[0]
        base = len(cells) - 9
        def g(i):
            j = base + i
            return clean(cells[j]) if 0 <= j < len(cells) else ""
        out.append({
            "md5": md5,
            "title": title_of(title_cell)[:300],
            "author": g(1),
            "publisher": g(2),
            "year": g(3),
            "language": g(4),
            "pages": g(5),
            "size": g(6),
            "extension": g(7),
            "edition_id": ed.group(1) if ed else "",
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", default="who's who")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-pages", type=int, default=30)
    ap.add_argument("--sleep", type=float, default=1.0)
    ap.add_argument("--no-phrase", action="store_true",
                    help="do not wrap the query in quotes for phrase matching")
    ap.add_argument("--no-title-filter", action="store_true",
                    help="keep all rows, even titles not matching the phrase")
    args = ap.parse_args()

    query = args.query if args.no_phrase else '"%s"' % args.query

    seen = {}
    dropped = 0
    empty_streak = 0
    for page in tqdm(range(1, args.max_pages + 1), desc="pages"):
        try:
            html = fetch(query, page)
        except Exception as e:
            print(f"page {page}: fetch error {e}", file=sys.stderr)
            time.sleep(args.sleep * 3)
            continue
        rows = parse_rows(html)
        new = 0
        for r in rows:
            if not args.no_title_filter and not WHOSWHO_RE.search(r["title"]):
                dropped += 1
                continue
            if r["md5"] not in seen:
                seen[r["md5"]] = r
                new += 1
        print(f"page {page}: {len(rows)} rows, {new} new (total {len(seen)}, dropped {dropped})")
        if not rows:
            empty_streak += 1
            if empty_streak >= 2:
                break
        else:
            empty_streak = 0
        time.sleep(args.sleep)

    fields = ["md5", "title", "author", "publisher", "year", "language",
              "pages", "size", "extension", "edition_id"]
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(seen.values())
    print(f"\nwrote {len(seen)} unique editions -> {args.out}")


if __name__ == "__main__":
    main()
