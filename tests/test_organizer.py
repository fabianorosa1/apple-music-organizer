import json, tempfile, unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import organizer

CFG = organizer.load_config()

class OrganizerTests(unittest.TestCase):
    def test_local_classification_uses_multiple_signals(self):
        p = {"name": "Deep Focus Español", "genre": "Electronic", "artist": "", "tracks": ["Ambient Study"]}
        got = organizer.classify_local(p, CFG)
        self.assertEqual(got["genre"], "Electronic")
        self.assertEqual(got["mood"], "Focus")
        self.assertEqual(got["language"], "Spanish")

    def test_plan_is_deterministic_and_nested(self):
        items = [{"name": "Workout Rock", "persistent_id": "A", "full_path": "", "track_count": 1, "genre": "", "artist": "", "tracks": []}]
        plan = organizer.make_plan(items, CFG, "local")
        self.assertEqual(plan["moves"][0]["destination"], "AI Organized/Rock/Workout")
        self.assertEqual(plan["inventory_sha256"], organizer.digest(items))

    def test_exclusions_are_not_moved(self):
        items = [{"name": "Library", "persistent_id": "A", "full_path": "", "track_count": 1, "genre": "", "artist": "", "tracks": []}]
        self.assertEqual(organizer.make_plan(items, CFG, "local")["moves"], [])

    def test_other_labels_do_not_nest(self):
        self.assertEqual(organizer.destination_for({"genre": "Other", "mood": "Other"}, CFG), "AI Organized/Unsorted")
        self.assertEqual(organizer.destination_for({"genre": "Jazz", "mood": "Other"}, CFG), "AI Organized/Jazz")

    def test_extract_json_strips_think_block(self):
        self.assertEqual(organizer.extract_json('<think>x {a}</think>{"genre": "Pop"}'), {"genre": "Pop"})

    def test_plan_files_are_written(self):
        old = organizer.OUT
        with tempfile.TemporaryDirectory() as d:
            organizer.OUT = Path(d)
            organizer.write_plan(organizer.make_plan([], CFG, "local"))
            self.assertTrue((Path(d) / "plan.json").exists())
            self.assertIn("organization plan", (Path(d) / "plan.md").read_text())
        organizer.OUT = old

if __name__ == "__main__": unittest.main()
