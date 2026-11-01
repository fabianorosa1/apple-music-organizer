# Validation record

Validated on 2026-10-31:

- `python3 -m unittest discover -s tests -v`: 4 tests passed.
- `python3 -m py_compile organizer.py`: passed.
- AppleScript source was inspected and retained for macOS execution. Full `osacompile` validation was not possible in the packaging environment because the Music scripting dictionary service returned a connection error; validate once on the target Mac with:

```bash
osacompile -o /tmp/AppleMusicOrganizer.scpt AppleMusicOrganizer.applescript
```

The package does not contain a live-library inventory, plan, backup, API key, or scheduled task.
