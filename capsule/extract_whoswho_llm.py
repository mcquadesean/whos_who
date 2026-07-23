"""Full-schema Who's Who extractor. Reads a per-person CSV (raw_entry column, one block
per row from parse_whoswho.py) and emits one JSONL record per entry. Talks to a local
OpenAI-compatible chat endpoint (vLLM/llama.cpp) running inside the capsule. Resumable:
existing person_ids in --out are skipped on restart.

Usage (inside capsule, after the model server is up):
    python extract_whoswho_llm.py --in <parsed.csv> --out <vol>.jsonl \
        --server http://localhost:8000 --model <model>
"""
import argparse
import csv
import json
import os
import sys
import urllib.request

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(x, **k):
        return x

csv.field_size_limit(10 ** 9)

SYSTEM = (
    "You are a meticulous data-extraction engine. You are given the text of ONE entry "
    "from a printed Marquis Who's Who biographical directory (it may contain OCR errors). "
    "Extract every fact present into a single JSON object matching the schema exactly. "
    "Never invent facts that are not present. HOWEVER, the text may contain OCR errors — "
    "when a value is clearly present but garbled, reconstruct its most likely intended "
    "form (this is OCR repair, not invention). Otherwise copy values verbatim, keeping "
    "the directory's abbreviations ('v.p.', 'A.B.', 'dir.', 'Rev.'). Absent scalar -> null; "
    "absent list -> []. Output ONLY the JSON object — no commentary, no code fences."
)

SCHEMA_AND_RULES = r"""
Return exactly one JSON object with this structure:

{
  "record_type": "full_entry | cross_reference",
  "cross_reference_to": <name this redirects to, e.g. "Wise, Daniel", or null>,
  "is_person_entry": <true|false>,
  "verification_flag": <true if entry ends with "*" (subject did not verify)>,
  "ocr_repaired": <true if you corrected any OCR errors, else false>,

  "name": {"surname": null, "given_name": null, "middle_names": null, "suffix": null,
           "known_as": null, "formal_expansion": null, "maiden_name": null,
           "married_name": null, "pen_names": [], "full_name_as_printed": null},
  "gender": null,
  "deceased": {"is_deceased": false, "death_date": null, "see_reference": null},

  "occupations": [],
  "birth": {"date": null, "city": null, "county": null, "state_province": null, "country": null},

  "father": {"name": null, "title": null, "degree": null, "occupation": null},
  "mother": {"name": null, "maiden_name": null, "title": null, "occupation": null},
  "ancestry_notes": null,

  "education": [ {"institution": null, "location": null, "degree": null, "field": null,
                  "year": null,
                  "type": "prep_school|school|college|graduate|professional|military|honorary",
                  "granting_institution": null, "honors": null} ],

  "marital_status": null,
  "marriages": [ {"order": null, "spouse_name": null, "spouse_maiden_name": null,
                  "spouse_origin": null, "spouse_father": null,
                  "spouse_father_occupation": null, "marriage_date": null,
                  "marriage_place": null, "divorced_year": null, "spouse_died_year": null} ],
  "children": [ {"name": null, "suffix": null, "by_former_marriage": false} ],
  "children_count": null,

  "positions": [ {"organization": null, "org_descriptor": null, "title": null,
                  "location": null, "start_year": null, "end_year": null,
                  "is_current": false,
                  "type": "employment|directorship|trusteeship|corporation_member|overseer|founder_organizer|named_chair|emeritus|visiting|consultant|elected_office|appointed_office|civic_office"} ],
  "candidacies": [ {"office": null, "party": null, "year": null, "won": null} ],
  "credentials": [ {"type": null, "jurisdiction": null, "year": null} ],
  "ordination": {"denomination": null, "office": null, "year": null},
  "military": [ {"branch": null, "unit": null, "rank": null, "conflict": null,
                 "start_year": null, "end_year": null, "battles": [], "wounded": false,
                 "decorations": []} ],

  "professional_societies": [ {"name": null, "role": null, "role_years": null} ],
  "honorary_societies": [],
  "fraternal_orders": [],
  "clubs": [ {"name": null, "city": null, "office": null} ],
  "civic_wartime_service": [],

  "religion": null,
  "political_party": null,

  "awards_honors": [ {"award": null, "grantor": null, "year": null} ],
  "publications": [ {"title": null, "year": null,
                     "role": "author|editor|compiler|contributor|featured"} ],
  "patents": null,
  "avocations": [],
  "notable_notes": null,

  "addresses": {"home": [], "office": [], "residence": [], "business": []},
  "relocations": [ {"place": null, "year": null} ],
  "contact": {"home_phone": null, "office_phone": null, "fax": null,
              "business_email": null, "personal_email": null},

  "extraction_notes": null
}

RULES
- Copy values verbatim; keep the directory's abbreviations; do not expand or normalize.
- Absent scalar -> null; absent list -> [].
- "s." = son of / "d." = daughter of -> fill father, mother, and gender.
- Mother's maiden name = surname in parentheses: "Katherine Wyman (Hastman) H." ->
  mother.name "Katherine Wyman", mother.maiden_name "Hastman".
- For a woman whose parents' surname differs from her entry surname, that surname is her
  name.maiden_name.
- "q.v." = the named person is also an entrant; keep the name as written.
- "dir."->directorship, "trustee"->trusteeship, "cons."->consultant, named chairs->
  named_chair, "emeritus"->emeritus, "Vis. prof."->visiting.
- Cross-reference only ("see X"): record_type="cross_reference", is_person_entry=false,
  cross_reference_to="X", everything else null/[].
- OCR REPAIR: fix obvious scan corruptions to the intended text, e.g.
    "Htarted"->"Started", "Willlam"->"William", "U. of Chica0"->"U. of Chicago",
    "B.A., Yale, 18S1"->"1881", "geologrist"->"geologist", "8. William"->"s. William".
  Reconstruct garbled names, places, institutions, and years to their most probable
  intended value. This ONLY cleans corrupted renderings of text that IS present — never
  add facts that are absent. If a token is too garbled to guess confidently, keep it as
  printed and note the uncertainty.
- When you repair OCR, set "ocr_repaired": true and list each fix in extraction_notes
  (e.g. "birth_place Chica0->Chicago; edu year 18S1->1881").
- Output ONLY the JSON object.
"""

PERSON_FIELDS = ["ht_volume_id", "series_id", "source_volume_year",
                 "surname", "given_name", "middle_name", "suffix"]


def build_user(entry):
    return ('ENTRY (verbatim, may contain OCR noise):\n"""\n'
            + entry + '\n"""\n' + SCHEMA_AND_RULES)


def call_model(server, model, entry, timeout=240):
    payload = {"model": model,
               "messages": [{"role": "system", "content": SYSTEM},
                            {"role": "user", "content": build_user(entry)}],
               "temperature": 0, "max_tokens": 1500,
               "response_format": {"type": "json_object"}}
    req = urllib.request.Request(server.rstrip("/") + "/v1/chat/completions",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())["choices"][0]["message"]["content"]


def extract_json(text):
    s, e = text.find("{"), text.rfind("}")
    if s == -1 or e == -1:
        return None
    try:
        return json.loads(text[s:e + 1])
    except json.JSONDecodeError:
        return None


def done_ids(path):
    ids = set()
    if os.path.exists(path):
        for line in open(path):
            try:
                ids.add(json.loads(line)["person_id"])
            except Exception:
                pass
    return ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_csv", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--server", default="http://localhost:8000")
    ap.add_argument("--model", default="local")
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()

    rows = list(csv.DictReader(open(a.in_csv, newline="")))
    if a.limit:
        rows = rows[:a.limit]
    already = done_ids(a.out)
    ok = fail = 0
    with open(a.out, "a") as out:
        for i, row in enumerate(tqdm(rows, desc="extract")):
            pid = f"{row.get('ht_volume_id','')}#{i}"
            if pid in already:
                continue
            entry = row.get("raw_entry", "")
            if not entry.strip():
                continue
            try:
                parsed = extract_json(call_model(a.server, a.model, entry))
            except Exception:
                parsed = None
            if not parsed:
                fail += 1
                continue
            rec = {"person_id": pid}
            rec.update({k: row.get(k, "") for k in PERSON_FIELDS})
            rec.update(parsed)
            rec["raw_entry"] = entry
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out.flush()
            ok += 1
    print(f"extracted {ok}, failed {fail} -> {a.out}")


if __name__ == "__main__":
    main()
