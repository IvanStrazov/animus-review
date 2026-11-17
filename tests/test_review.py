"""End-to-end tests for scripts/review.py (stdlib unittest, no dependencies)."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "review.py"


class ReviewTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.proj = self.tmp / "proj"
        (self.proj / ".journal" / "log").mkdir(parents=True)
        self.env = dict(os.environ, JOURNAL_GLOBAL_DIR=str(self.tmp / "journal"),
                        CLAUDE_ECOSYSTEM_FILE=str(self.tmp / "eco.json"), PYTHONIOENCODING="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_v(self, *args, stdin="", ok=True):
        r = subprocess.run([sys.executable, str(SCRIPT), *args], input=stdin, cwd=str(self.proj),
                           env=self.env, capture_output=True, text=True, encoding="utf-8")
        if ok:
            self.assertEqual(r.returncode, 0, r.stderr)
        return r

    def test_full_cycle(self):
        out = self.run_v("save", "--title", "ML methodology",
                         stdin="Questions:\n1. Is the IC real?\nAnswer format: markdown").stdout
        rid = out.split("request ")[1].split(":")[0]
        d = self.proj / ".journal" / "review"
        self.assertTrue((d / f"{rid}.request.md").read_text(encoding="utf-8").startswith("# ML methodology"))
        self.assertIn(f"{rid} | open | ML methodology", (d / "INDEX.md").read_text(encoding="utf-8"))
        ans = self.tmp / "answer.md"
        ans.write_text("Verdict: mostly fine\nF1 high: leakage in features", encoding="utf-8")
        shown = self.run_v("in", str(ans)).stdout
        self.assertIn("Is the IC real?", shown)
        self.assertIn("F1 high: leakage", shown)
        self.assertTrue((d / f"{rid}.response.md").is_file())
        self.assertIn("answered", self.run_v("list").stdout)
        self.run_v("close", rid, "--note", "2 accepted, 1 rejected")
        self.assertIn("closed", self.run_v("list").stdout)
        self.assertIn("2 accepted", (d / f"{rid}.request.md").read_text(encoding="utf-8"))
        self.assertIn("no open request", self.run_v("in", str(ans), ok=False).stderr)

    def test_gather_topic_and_sizes(self):
        (self.proj / ".journal" / "log" / "2026-11.md").write_text(
            "## 2026-11-10 10:00 #ml — Ridge grid\nDone: 12 trials\n\n"
            "## 2026-11-11 10:00 #ui — Buttons\nDone: x\n", encoding="utf-8")
        out = self.run_v("gather", "--topic", "ml").stdout
        self.assertIn("Ridge grid", out)
        self.assertNotIn("Buttons", out)
        f = self.proj / "a.py"
        f.write_text("x = 1\n" * 40, encoding="utf-8")
        s = self.run_v("sizes", str(f), str(self.proj / "missing.py")).stdout
        self.assertIn("40 lines", s)
        self.assertIn("missing", s)
        self.assertIn("total ~60 tokens", s)

    def test_pasted_answer_rounds_and_prefix_close(self):
        out = self.run_v("save", "--title", "A very long title about the save system architecture for a roguelite",
                         stdin="Questions:\n1. ok?\nAnswer format: md").stdout
        rid = out.split()[2].rstrip(":")
        cut = self.run_v("save", "--title", "Cut", stdin="Questions:\n1. half a sente", ok=False)
        self.assertIn("looks cut off", cut.stderr)                # an unterminated heredoc is refused
        self.run_v("save", "--title", "Mistake", "--force", stdin="oops")
        self.assertIn("dropped", self.run_v("drop", self.run_v("list").stdout.split()[-3]).stdout)
        self.assertNotIn("Mistake", self.run_v("list").stdout)
        self.assertFalse(rid.endswith("-roguel"), rid)       # cut at a word boundary
        self.assertIn("F1 pasted", self.run_v("in", "-", stdin="F1 pasted finding").stdout)
        self.assertIn("F2 second round", self.run_v("in", "-", stdin="F2 second round").stdout)  # answered -> again
        d = self.proj / ".journal" / "review"
        self.assertEqual(len(list(d.glob(f"{rid}.response*.md"))), 2)  # the first round is kept
        self.assertIn("not a file", self.run_v("in", "nope.md", ok=False).stderr)
        self.run_v("close", rid[:15], "--note", "done")      # unique prefix (date-time) is enough
        self.assertIn("closed", self.run_v("list").stdout)

    def test_limits(self):
        self.assertNotEqual(self.run_v("save", "--title", "x", stdin="\n".join(["l"] * 300), ok=False).returncode, 0)
        self.assertNotEqual(self.run_v("close", "nope", ok=False).returncode, 0)
        self.assertIn("no reviews", self.run_v("list").stdout)


if __name__ == "__main__":
    unittest.main()
