# Claude Context: Who's Who

## Claude's Role

Act as project manager, research assistant, and data collaborator. Help stay on top of
the data pipeline, execute empirical data tasks, and maintain clean documentation and
version control.

## Work Preferences

- Do not add comments to code unless asked
- Do not explain commands or reasoning unless asked
- Never delete files — move to an `archived/` subfolder with the date in the filename
  (e.g., `archived/script_name_2026_07_21.py`)
- Always use lowercase with underscores for all file and folder names
- When writing scripts that process data, use `tqdm` progress bars
- Always write outputs to the shared data drive, not local directories
- Be concise

## Confirmation Guidelines

**Ask before:** sending emails/external messages, writing to external services,
destructive operations (deleting, overwriting without backup).

**Do not ask before:** reading/searching/analyzing files, executing clear instructions,
implementing an approved plan, routine file operations (create, move, rename).

---

## Project-Specific

- **Supervisor:** McQuade
- **Goal:** Extract structured data from Who's Who directories (biographical reference
  volumes) sourced from Anna's Archive, into clean tabular datasets of individuals and
  their biographical fields.

### Key Paths

| What | Path |
|------|------|
| Code | `/gpfs/home/hfa9391/mcquade_projects/whos_who/` |
| Raw source files (PDF/EPUB) | `/gpfs/kellogg/proj/mke060/shared_sm/whos_who/data/raw/` |
| Processed data | `/gpfs/kellogg/proj/mke060/shared_sm/whos_who/data/processed/` |
| Results | `/gpfs/kellogg/proj/mke060/shared_sm/whos_who/results/` |

### Source Formats

Who's Who volumes arrive in mixed formats and require format-specific extraction:
- **Scanned PDF** — page images; requires OCR
- **Digital-text PDF** — selectable text; direct extraction
- **EPUB / ebook** — structured markup

### Pipeline Status

| Step | Script | Status |
|------|--------|--------|
| _(none yet)_ | | |

### Current Status

Project initialized 2026-07-21. No raw files ingested yet. Awaiting Who's Who volumes
from Anna's Archive to be placed in `data/raw/`.
