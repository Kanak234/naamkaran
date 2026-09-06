# नामकरण (NAAMKARAN)

A safe rename tool for large Rust workspaces, built for the KLIONS language
project. It renames a crate/module across an entire workspace without breaking
references.

> Detailed notes are in [`PADHO.txt`](PADHO.txt) (Hindi).

## Tools

- `tools/naamkaran.py` — the renamer
- `tools/sab_jaancho.py` — checks the workspace before/after
- `tools/nakli_workspace.py` — builds a throwaway test workspace
- `mandala/mandala_bhandar.py` — supporting module

## Run

```bash
python3 tools/naamkaran.py     # see PADHO.txt for arguments
```

## Requires

- Python 3 (standard library).

## Status

Working utility. Note (from `PADHO.txt`): the name "SŪTRA" was dropped after it
was found to already belong to another functional language, so this tool and the
language it supports were renamed.
