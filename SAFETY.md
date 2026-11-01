# Safety, backup, and recovery

## Before applying

- Use dry-run first and review every proposed destination.
- Do not run simultaneously on the MacBook Air and Mac mini.
- If Sync Library is enabled, wait for the library to settle before and after applying.
- Keep Apple Music open during the apply step, with no playlist editing in progress.
- Keep the generated backup JSON and the reviewed plan together.

## What is backed up

The backup records playlist names, folder paths, and track metadata observed before the run. It does not copy audio files or playlist contents to another service. It is an audit and recovery reference, not a full media-library backup.

## Recovery

The organizer never deletes playlists or tracks. If the resulting folder layout is not what you want:

1. Stop using the organizer on all Macs.
2. Use the backup JSON and the plan to identify the affected playlists.
3. Move playlists back manually in Music, or create a reviewed inverse plan before using any automation.
4. If Sync Library is producing unexpected changes, pause further edits and wait for all devices to converge.

For a complete library rollback, use Apple's own backup strategy (for example a Time Machine snapshot or a copy of the Music Library database) before editing. Do not treat this project as a replacement for that backup.

## Apply guardrails

The script checks that:

- the plan has the expected schema;
- the plan was generated from an inventory;
- the current playlist names still match the planned source set;
- the explicit `--apply` flag is present;
- a backup is written before AppleScript is invoked.

Use `--allow-stale-plan` only when you have manually reviewed the differences and accept that the plan no longer matches the current inventory.
