#!/usr/bin/env python3
"""Apple Music organizer v2. Dry-run is the default; apply is fail-closed."""
import argparse, hashlib, json, os, re, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
SCRIPT = ROOT / "AppleMusicOrganizer.applescript"

def cfg(): return load_config()
def load_config(): return json.loads((ROOT / "config.json").read_text(encoding="utf-8"))

def run_script(mode, path=None):
    args = ["osascript", str(SCRIPT), mode] + ([str(path)] if path else [])
    try:
        p = subprocess.run(args, text=True, capture_output=True, check=True)
    except FileNotFoundError: raise RuntimeError("osascript is unavailable; run on macOS.")
    except subprocess.CalledProcessError as e: raise RuntimeError((e.stderr or e.stdout or "AppleScript failed").strip())
    return p.stdout

def inventory():
    result = []
    for raw in run_script("inventory").splitlines():
        if not raw.strip(): continue
        fields = raw.split("\t")
        if len(fields) != 8:
            raise RuntimeError("Unsafe AppleScript protocol: expected 8 inventory fields including persistent_id, full_path, and track_count.")
        name, pid, full_path, media_kind, track_count, genre, artist, tracks = fields
        if not pid: raise RuntimeError(f"Playlist {name!r} has no persistent identity.")
        result.append({"name": name, "persistent_id": pid, "full_path": full_path, "media_kind": media_kind, "track_count": int(track_count or 0), "genre": genre, "artist": artist, "tracks": [x for x in tracks.split(" | ") if x]})
    ids = [p["persistent_id"] for p in result]
    if len(ids) != len(set(ids)): raise RuntimeError("AppleScript returned duplicate persistent identities.")
    return result

def digest(items): return hashlib.sha256(json.dumps(items, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
def corpus(p): return " ".join([p.get("name", ""), p.get("full_path", ""), p.get("genre", ""), p.get("artist", "")] + p.get("tracks", [])).lower()

def first_match(text, mapping):
    words = sorted(((w.lower(), label) for label, values in mapping.items() for w in values), key=lambda x: len(x[0]), reverse=True)
    return next((label for word, label in words if re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", text)), "Other")

def classify_local(p, c):
    print(f"Classifying playlist locally: {p['name']}")
    text = corpus(p); name = p.get("name", "").lower(); h = c["hints"]
    # Track titles are too noisy for mood/genre keywords ("love", "film"), so those use the playlist name and genre tags only.
    tags = " ".join([name, p.get("genre", "").lower()])
    return {"genre": first_match(tags, h["genre_keywords"]), "mood": first_match(name, h["mood_keywords"]), "language": first_match(text, h["language_keywords"])}

def extract_json(text):
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start: raise ValueError("no JSON object in model reply")
    return json.loads(text[start:end + 1])

def classify_ai(p, c):
    print(f"Classifying playlist with AI: {p['name']}")
    ai = c["ai"]; key = os.environ.get(ai.get("api_key_env") or "", "")
    sample = {"name": p["name"], "track_count": p.get("track_count", 0), "genres": sorted(set(filter(None, (g.strip() for g in p.get("genre", "").split(","))))), "artists": sorted(set(filter(None, (a.strip() for a in p.get("artist", "").split(","))))), "tracks": p.get("tracks", [])[:12]}
    system = "You classify music playlists. Reply with one JSON object with string keys genre, mood, language. Each value MUST be copied exactly from the matching taxonomy list; use Other when unsure. No explanations."
    payload = {"model": ai["model"], "temperature": 0, "chat_template_kwargs": {"enable_thinking": False}, "messages": [{"role": "system", "content": system}, {"role": "user", "content": json.dumps({"playlist": sample, "taxonomy": {"genre": c["taxonomy"]["Genres"], "mood": c["taxonomy"]["Moods"], "language": c["taxonomy"]["Languages"]}}, ensure_ascii=False)}]}
    #print(f"Payload for AI classification: {json.dumps(payload, ensure_ascii=False)}")

    headers = {"Content-Type": "application/json"}
    if key: headers["Authorization"] = "Bearer " + key
    req = urllib.request.Request(ai["endpoint"], data=json.dumps(payload).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=ai.get("timeout_seconds", 45)) as response: result = extract_json(json.load(response)["choices"][0]["message"]["content"])
    allowed = {"genre": set(c["taxonomy"]["Genres"]), "mood": set(c["taxonomy"]["Moods"]), "language": set(c["taxonomy"]["Languages"])}
    return {k: (result.get(k) if result.get(k) in allowed[k] else "Other") for k in allowed}

def classify(p, c, provider):
    if provider in ("ai", "openai"):
        try: return classify_ai(p, c)
        except Exception as e:
            print(f"WARNING: AI failed for {p['name']!r} ({e}); using keyword fallback.", file=sys.stderr)
    return classify_local(p, c)

def safe_segment(text): return text.replace("/", "-").strip() or "Other"

def destination_for(labels, c):
    # One folder level per configured hierarchy level; "Other" ends the descent instead of nesting Other/Other/Other.
    parts = [safe_segment(c["root_folder"])]
    for level in c.get("hierarchy", ["genre", "mood"]):
        label = labels.get(level, "Other")
        if label == "Other": break
        parts.append(safe_segment(label))
    if len(parts) == 1: parts.append("Unsorted")
    return "/".join(parts)

def in_scope(p, c):
    path = p["full_path"].strip("/"); source = c.get("source_folder", "Playlists").strip("/"); root = c["root_folder"].strip("/")
    if path == "": return c.get("include_root_playlists", True)
    if path == source or path.startswith(source + "/"): return True
    return c.get("reorganize_existing", True) and (path == root or path.startswith(root + "/"))

def make_plan(items, c, provider):
    protected = set(c.get("protected_playlists", [])); moves = []
    for p in items:
        if not in_scope(p, c) or p["name"] in protected or (c.get("skip_empty_playlists", True) and p.get("track_count", 0) == 0): continue
        labels = classify(p, c, provider)
        destination = destination_for(labels, c)
        if p["full_path"] == destination: continue
        moves.append({"playlist_id": p["persistent_id"], "playlist": p["name"], "current_path": p["full_path"], "destination": destination, "classification": labels})
    return {"schema": 2, "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "provider": provider, "inventory_sha256": digest(items), "source_playlists": sorted(m["playlist_id"] for m in moves), "moves": moves}

def write_plan(plan):
    OUT.mkdir(exist_ok=True); (OUT / "plan.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = ["# Apple Music playlist organization plan", "", f"Generated: `{plan['created_at']}`", f"Inventory hash: `{plan['inventory_sha256']}`", "", "| Playlist | Current path | Proposed folder |", "|---|---|---|"]
    for m in plan["moves"]:
        playlist = m["playlist"].replace("|", "\\|")
        current_path = m["current_path"].replace("|", "\\|")
        lines.append(f"| {playlist} | {current_path} | {m['destination']} |")
    (OUT / "plan.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

def apply_plan(path, confirm, batch_size=10, resume_partial=False):
    if not confirm: raise RuntimeError("Live changes require --apply --confirm-apply after reviewing output/plan.md.")
    if batch_size < 1 or batch_size > 50: raise RuntimeError("--batch-size must be between 1 and 50.")
    plan = json.loads(Path(path).read_text(encoding="utf-8"))
    if plan.get("schema") != 2 or not isinstance(plan.get("moves"), list): raise RuntimeError("Only schema-2 plans may be applied.")
    current = inventory()
    if not resume_partial and digest(current) != plan.get("inventory_sha256"): raise RuntimeError("Library changed since review; use --resume-partial only after inspecting the current inventory.")
    current_by_id = {p["persistent_id"]: p for p in current}
    if resume_partial:
        pending = []
        for move in plan["moves"]:
            current_item = current_by_id.get(move.get("playlist_id"))
            if current_item is None: raise RuntimeError(f"Playlist identity is missing: {move.get('playlist_id')}")
            current_path = current_item.get("full_path", "")
            if current_path == move["destination"]: continue
            if current_path != move.get("current_path", ""): raise RuntimeError(f"Unexpected state for {move['playlist']!r}: {current_path!r}")
            pending.append(move)
    else:
        pending = list(plan["moves"])
    OUT.mkdir(exist_ok=True); backup = OUT / ("backup-" + time.strftime("%Y%m%d-%H%M%S") + ".json"); backup.write_text(json.dumps({"plan": plan, "pending_moves": pending, "inventory": current}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"); print("Backup written:", backup)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    moves = pending
    total_batches = (len(moves) + batch_size - 1) // batch_size
    for batch_number, start in enumerate(range(0, len(moves), batch_size), start=1):
        batch = moves[start:start + batch_size]
        apply_file = OUT / f"apply-{stamp}-part{batch_number:03d}.tsv"
        apply_file.write_text("".join(f"MOVE\t{m['playlist_id']}\t{m['destination']}\n" for m in batch), encoding="utf-8")
        print(f"Applying batch {batch_number}/{total_batches} ({len(batch)} playlists)...")
        try:
            run_script("apply", apply_file)
        except Exception as exc:
            raise RuntimeError(f"Batch {batch_number}/{total_batches} failed after earlier batches may have completed: {exc}") from exc
    print("Apply completed.")

def main():
    ap = argparse.ArgumentParser(); mode = ap.add_mutually_exclusive_group(); mode.add_argument("--dry-run", action="store_true"); mode.add_argument("--inventory-only", action="store_true"); mode.add_argument("--apply", action="store_true"); ap.add_argument("--provider", choices=["local", "ai", "openai"]); ap.add_argument("--plan", default=str(OUT / "plan.json")); ap.add_argument("--confirm-apply", action="store_true"); ap.add_argument("--batch-size", type=int, default=10); ap.add_argument("--resume-partial", action="store_true"); a = ap.parse_args(); c = cfg()
    try:
        if a.apply: apply_plan(a.plan, a.confirm_apply, a.batch_size, a.resume_partial); return 0
        items = inventory()
        if a.inventory_only: OUT.mkdir(exist_ok=True); (OUT / "inventory.json").write_text(json.dumps(items, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"); print(f"Wrote {len(items)} playlists"); return 0
        plan = make_plan(items, c, a.provider or c.get("provider", "local")); write_plan(plan); print(f"Dry-run only: proposed {len(plan['moves'])} placements. Review {OUT / 'plan.md'}"); return 0
    except Exception as e: print("ERROR:", e, file=sys.stderr); return 1

if __name__ == "__main__": raise SystemExit(main())
