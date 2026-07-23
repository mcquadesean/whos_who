"""Segment HathiTrust OCR pages of a Marquis Who's Who volume into per-person entry
blocks. Mirrors corporate_kinship/parse_register.py but tuned for Who's Who typography.

Who's Who entries begin with a boldface surname in caps, followed by a comma and the
given name(s): e.g.  SMITH, John Bradford, banker; b. Boston, Mass., May 3, 1901; ...
This script only SEGMENTS (one raw_entry per person); structured fields are pulled by
extract_whoswho_llm.py. Calibrate RUNNING_HEADER_RE / NAME_HEADER_RE on a real page
before a full run.

Usage (inside capsule):
    python parse_whoswho.py <volume_dir> --htid <htid> --year <yyyy> \
        --series <WWA|WWFI|...> --out /media/secure_volume/out/<enc>.csv
"""
import argparse
import csv
import re
from pathlib import Path

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(x, **k):
        return x

RUNNING_HEADER_RE = re.compile(
    r"^(WHO'?S\s+WHO\b|MARQUIS|A\.?\s*N\.?\s+MARQUIS)", re.IGNORECASE)
PAGE_NUMBER_RE = re.compile(r"^\d{1,5}$")
# surname portion (before comma) is all-caps; given portion starts uppercase
NAME_HEADER_RE = re.compile(r"^([A-Z][A-Z .,'’&-]{1,60}?),\s+([A-Z][A-Za-z].*)$")
BIRTH_RE = re.compile(r"\bb\.\s*([^;]+)", re.IGNORECASE)
SUFFIX_RE = re.compile(r"\b(Jr|Sr|II|III|IV)\b\.?", re.IGNORECASE)
# real entries are semicolon-delimited or cross-references ("see X"); index lines
# ("Smith, John, 234"), abbreviation keys, and staff lists have neither.
ENTRY_SIGNAL_RE = re.compile(r";|\bsee\b", re.IGNORECASE)


def is_entry_like(text):
    return bool(ENTRY_SIGNAL_RE.search(text)) and any(c.isalpha() for c in text)


def is_page_header(line):
    return bool(PAGE_NUMBER_RE.match(line) or RUNNING_HEADER_RE.match(line))


def looks_like_name_header(line):
    m = NAME_HEADER_RE.match(line)
    if not m:
        return False
    surname = m.group(1)
    if not any(c.isalpha() for c in surname):
        return False
    # reject if the surname portion has lowercase (i.e. not a caps headword)
    letters = [c for c in surname if c.isalpha()]
    return letters and not any(c.islower() for c in letters)


def iter_record_blocks(lines):
    current = None
    for raw in lines:
        line = raw.strip()
        if not line or is_page_header(line):
            continue
        if looks_like_name_header(line):
            if current is not None:
                yield current
            current = [line]
        elif current is not None:
            current.append(line)
    if current is not None:
        yield current


def join_block(block):
    text = ""
    for line in block:
        line = line.strip()
        if not line:
            continue
        if text.endswith("-") and line[:1].islower():
            text = text[:-1] + line
        elif text:
            text = text + " " + line
        else:
            text = line
    return text


def split_name(header_text):
    surname, _, rest = header_text.partition(",")
    surname = surname.strip()
    given = re.split(r"[;(]", rest, maxsplit=1)[0].strip()
    suffix = ""
    sm = SUFFIX_RE.search(given)
    if sm:
        suffix = sm.group(1)
        given = SUFFIX_RE.sub("", given).strip(" ,")
    parts = given.split()
    given_first = parts[0] if parts else ""
    middle = " ".join(parts[1:]) if len(parts) > 1 else ""
    return surname, given_first, middle, suffix


def page_files(volume_dir):
    paths = sorted(Path(volume_dir).rglob("*.txt"))
    return [p for p in paths if p.name[0].isdigit()]


def select_pages(paths, page_range):
    if not page_range:
        return paths
    start, _, end = page_range.partition("-")
    start = int(start)
    end = int(end) if end else start
    return paths[start - 1:end]


FIELDS = ["ht_volume_id", "series_id", "source_volume_year",
          "surname", "given_name", "middle_name", "suffix", "raw_entry"]


def parse_volume(volume_dir, htid, series, year, page_range=None, max_entry_chars=20000):
    paths = select_pages(page_files(volume_dir), page_range)
    lines = []
    for p in paths:
        lines.extend(p.read_text(errors="replace").splitlines())
    records, big, noise = [], 0, 0
    for block in tqdm(list(iter_record_blocks(lines)), desc="entries"):
        text = join_block(block)
        if max_entry_chars and len(text) > max_entry_chars:
            big += 1
            continue
        if not is_entry_like(text):
            noise += 1                      # index line / abbrev key / staff list / stray caps
            continue
        surname, given, middle, suffix = split_name(block[0])
        records.append({
            "ht_volume_id": htid, "series_id": series, "source_volume_year": year,
            "surname": surname, "given_name": given, "middle_name": middle,
            "suffix": suffix, "raw_entry": text,
        })
    print(f"  kept {len(records)} entries | dropped {noise} non-entry blocks "
          f"(index/front-matter), {big} oversized")
    return records


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("volume_dir")
    ap.add_argument("--htid", required=True)
    ap.add_argument("--series", required=True)
    ap.add_argument("--year", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pages", default=None)
    ap.add_argument("--max-entry-chars", type=int, default=20000)
    a = ap.parse_args()
    recs = parse_volume(a.volume_dir, a.htid, a.series, a.year, a.pages, a.max_entry_chars)
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(recs)
    print(f"parsed {len(recs)} person entries -> {a.out}")


if __name__ == "__main__":
    main()
