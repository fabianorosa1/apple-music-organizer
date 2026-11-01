# Apple Music organizer review

## Findings

1. **Critical: duplicate names are unsafe.** `make_plan()` stores only `p["name"]`, and the AppleScript apply path uses `some user playlist whose name is pName`. The two `Hits of 2013` playlists (and the other duplicate names) can cause the wrong playlist to move.
2. **Critical: the apply command is not approval-gated.** `--apply` immediately writes a backup, creates the apply file, and invokes Apple Music. `--allow-stale-plan` weakens the only existing freshness check.
3. **Critical: the API key is plaintext.** The value in `config.json` must be treated as exposed and rotated if valid. It must not remain in source, plan files, backups, or logs.
4. **High: protection is name-only and incomplete.** `Music Videos` is excluded, but `TV & Movies` is not. Empty playlists and other non-music playlists are not reliably identifiable from the five-field inventory protocol.
5. **High: the plan can be stale without detection.** It checks only missing names; it does not compare the current inventory with the inventory used to generate the plan.
6. **Medium: the Python/AppleScript protocol is positional and lossy.** Tab/newline characters in names are normalized only during apply-file creation, and the Python side silently skips malformed inventory rows.
7. **Medium: classification is optimistic.** A maximum of 12 sampled tracks and substring keyword matching can misclassify multilingual or mixed-content playlists. This should remain a reviewable proposal, never an automatic decision.

## Required AppleScript interface change

The attached AppleScript was not available for verification. The following is therefore an interface requirement, not a verified Apple Music dictionary fact.

Change inventory output from five fields:

```text
name<TAB>folder<TAB>genre<TAB>artist<TAB>track names
```

to six fields:

```text
name<TAB>folder<TAB>persistent_id<TAB>genre<TAB>artist<TAB>track names
```

The `persistent_id` must be a stable identity returned by Music for that playlist. The apply handler must parse `MOVE<TAB>persistent_id<TAB>destination` and resolve the playlist by that identity—not by name. The exact AppleScript property/class spelling must be confirmed against Music’s scripting dictionary on the target Mac; it cannot be validated from the missing file.

The apply handler should also fail if the identity resolves to zero or more than one playlist, rather than swallowing errors with a broad `try` block.

## Precise Python changes

### 1. Reject the legacy inventory protocol

Replace the five-field parsing in `inventory()` with:

```python
if len(fields) != 6:
    raise RuntimeError(
        "AppleScript inventory interface is legacy/unsafe: "
        "expected 6 tab-separated fields including persistent_id."
    )
name, folder, persistent_id, genre, artist, tracks = fields
if not persistent_id:
    raise RuntimeError(f"Playlist {name!r} has no stable identity.")
result.append({
    "name": name,
    "folder": folder,
    "persistent_id": persistent_id,
    "genre": genre,
    "artist": artist,
    "tracks": [x for x in tracks.split(" | ") if x],
})
```

After the loop, reject duplicate IDs:

```python
ids = [p["persistent_id"] for p in result]
if len(ids) != len(set(ids)):
    raise RuntimeError("Duplicate playlist identities returned by AppleScript.")
```

### 2. Remove the secret from config

Delete `ai.apikey` and use:

```json
"api_key_env": "OPENAI_API_KEY"
```

Then change `classify_ai()` to:

```python
env_name = cfg["ai"].get("api_key_env", "OPENAI_API_KEY")
key = os.environ.get(env_name)
if not key:
    raise RuntimeError(f"{env_name} is not set; use --provider local or set it in the environment.")
```

Rotate the exposed key before using the OpenAI provider.

### 3. Protect non-music and empty playlists

Use explicit configuration:

```json
"protected_playlists": ["Library", "Music Videos", "TV & Movies"],
"skip_empty_playlists": true
```

In `make_plan()`:

```python
protected = set(cfg.get("exclude_playlists", []))
protected.update(cfg.get("protected_playlists", []))
for p in items:
    if p["name"] in protected:
        continue
    if cfg.get("skip_empty_playlists", True) and not p.get("tracks"):
        continue
```

For stronger protection, add a media-kind/content-kind field to the AppleScript inventory and skip anything not identified as an ordinary music playlist. Names alone are not sufficient.

### 4. Put stable IDs in plans and apply files

Each move must contain `playlist_id: p["persistent_id"]`. `source_playlists` should be a sorted list of persistent IDs, not names. The apply TSV must be:

```python
"MOVE\t" + m["playlist_id"] + "\t" + m["destination"] + "\n"
```

Reject schema 1 plans so legacy name-based plans cannot be applied.

### 5. Require an explicit approval flag and an exact inventory match

Add `--confirm-apply`. `apply_plan()` must reject unless it is set, then require:

```python
current = inventory()
if digest(current) != plan.get("inventory_sha256"):
    raise RuntimeError(
        "The library changed since this plan was generated; "
        "run a new dry-run and review it again."
    )
```

Remove or disable `--allow-stale-plan`; it defeats this safety property. Keep dry-run as the default. The only live path should be `--apply --confirm-apply`, after the user has reviewed `output/plan.md`.

Include the complete plan and the current inventory in the backup before invoking AppleScript.

## Dry-run/apply conclusion

The current default is dry-run, but apply is not sufficiently guarded. After the changes above, a legacy AppleScript or legacy plan fails closed; duplicate names cannot select a target; empty and named non-music playlists are excluded; credentials are externalized; and any library change since review forces a new dry-run.
