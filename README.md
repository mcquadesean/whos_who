# Who's Who

Extract structured data from Who's Who directories — biographical reference volumes
sourced from Anna's Archive — into clean tabular datasets of individuals and their
biographical fields.

**Supervisor:** McQuade · **Researcher:** Sean McQuade

## Directory Structure

**Code** (`/gpfs/home/hfa9391/mcquade_projects/whos_who/`):
```
whos_who/
├── scripts/
├── notebooks/
├── jobs/
├── logs/
│   └── claude_progress.md
├── CLAUDE.md
├── README.md
├── environment.yml
├── .gitignore
└── .env.example
```

**External storage** (`/gpfs/kellogg/proj/mke060/shared_sm/whos_who/`):
```
whos_who/
├── data/
│   ├── raw/          # source PDF / EPUB volumes from Anna's Archive
│   ├── processed/
│   └── _archive/
└── results/
    └── _archive/
```

## Pipeline

| Step | Script | Status |
|------|--------|--------|
| _(none yet)_ | | |

## Notes

- Source volumes arrive in mixed formats (scanned PDF, digital-text PDF, EPUB) and need
  format-specific extraction; scanned volumes require OCR.
- Never delete files — move to a dated `archived/` subfolder.
- All outputs go to the shared data drive, not local directories.
