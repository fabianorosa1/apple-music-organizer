# Installation and use

## Requirements

- macOS with Apple Music
- Python 3.9 or newer (the standard library is sufficient)
- Automation permission for the terminal or app that launches the script
- Optional: an OpenAI-compatible API key for AI classification

## Install

1. Copy this folder to both Macs if you want it available on both the MacBook Air and Mac mini.
2. Open Terminal and change into the project folder.
3. Run `python3 organizer.py --dry-run`.
4. If macOS asks whether Terminal may control Music, choose **Allow**. If you deny it, open System Settings → Privacy & Security → Automation and allow the terminal app to control Music.

No scheduled task is installed. Every run is started manually.

## Optional AI configuration

Copy `config.json` if you want to customize it. Set an API key in the shell before a run:

```bash
export OPENAI_API_KEY='your-key'
python3 organizer.py --dry-run --provider openai
```

The key is read from the environment and is never written to the plan or backup. Without the key, use `--provider local` for deterministic keyword classification.

## Recommended workflow

1. Close any other Apple Music organization tools and ensure the library is stable.
2. Run a dry run.
3. Read `output/plan.md` and inspect `output/plan.json`.
4. Make a copy of the plan if you want an audit record.
5. Apply only after reviewing the proposed moves: `python3 organizer.py --apply --plan output/plan.json`.
6. Verify folders in Music before using another Mac or allowing a Sync Library update to propagate.

## Useful commands

```bash
python3 organizer.py --dry-run --provider local
python3 organizer.py --dry-run --provider openai
python3 organizer.py --inventory-only
python3 organizer.py --apply --plan output/plan.json
python3 -m unittest discover -s tests -v
```

The tool creates `output/` on first use. It is safe to delete old generated plans and backups after you have confirmed that you no longer need them.
