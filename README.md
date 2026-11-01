# Apple Music Organizer v2

This version is designed for a reviewed, two-phase workflow:

1. Inventory and dry-run only.
2. Review `output/plan.md`.
3. Apply only with `--apply --confirm-apply` and an unchanged inventory.

It includes root playlists and playlists recursively below the configured `source_folder` (`Playlists`). Playlists are identified by Music's persistent ID, not by name.

The AppleScript must be compiled on the target Mac with Music open and Automation permission granted. The script was not executed against the live library by this bundle generation.

## Commands

```bash
python3 organizer.py --inventory-only
python3 organizer.py --dry-run
```

After reviewing `output/plan.md`:

```bash
python3 organizer.py --apply --plan output/plan.json --confirm-apply
```

Do not use an old schema-1 plan. Rotate any API key previously stored in `config.json` and keep the replacement in `OPENAI_API_KEY`.

## Updated workflow (v2.1)

1. `export OMLX_API_KEY=...` (the key is no longer stored in `config.json`; rotate the one that was).
2. Clean up duplicate folders from earlier runs: `osascript MergeAppleMusicFolders.applescript preview "AI Organized"`, then `apply`.
3. `python3 organizer.py --dry-run --provider ai`, then review `output/plan.md`.
4. `python3 organizer.py --apply --confirm-apply`.

Folder depth is set by `hierarchy` in `config.json` (default `["genre", "mood"]` → `AI Organized/Rock/Party`). `Other` labels stop the descent instead of creating `Other/Other/Other`.
