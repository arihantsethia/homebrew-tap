from pathlib import Path
import unittest

from update_clipport import current_tag, digest, prepare, render, version

FORMULA = '''class Clipport < Formula
  url "https://github.com/arihantsethia/clipport/archive/refs/tags/v0.1.1.tar.gz"
  sha256 "'''+"0"*64+'''"
  head "https://github.com/arihantsethia/clipport.git", branch: "main"
end
'''
COMMIT = "a" * 40


class UpdateTest(unittest.TestCase):
    def setUp(self):
        self.release = {"tag_name": "v0.1.2", "draft": False, "prerelease": False,
                        "published_at": "2026-10-12T00:00:00Z", "id": 42}
        self.status = "ahead"
        self.commits = [COMMIT, COMMIT]

    def fetch(self, path):
        if path == "/releases/latest":
            return self.release
        if path.startswith("/commits/"):
            return {"sha": self.commits.pop(0)}
        if path == f"/compare/{COMMIT}...main":
            return {"status": self.status}
        self.fail(path)

    def proposal(self):
        return prepare(FORMULA, self.fetch, lambda _: b"release archive")

    def test_updates_only_url_and_checksum(self):
        proposal = self.proposal()
        expected = FORMULA.replace("v0.1.1.tar.gz", "v0.1.2.tar.gz").replace("0" * 64, digest(b"release archive"))
        self.assertEqual(render(FORMULA, proposal), expected)

    def test_same_version_and_downgrade_noop(self):
        for tag in ("v0.1.1", "v0.1.0"):
            self.release["tag_name"] = tag
            self.assertIsNone(self.proposal())

    def test_numeric_version_order(self):
        self.assertGreater(version("v0.10.0"), version("v0.9.99"))

    def test_rejects_nonstable_tags(self):
        for tag in ("main", "v0.1.2-rc1", "v01.2.3", "v1.2", "v1.2.3\n", "v1.2.3;echo nope"):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                version(tag)

    def test_rejects_unpublished_and_prerelease(self):
        for field, value in (("draft", True), ("prerelease", True), ("published_at", None)):
            original = self.release.copy()
            self.release[field] = value
            with self.assertRaises(ValueError):
                self.proposal()
            self.release = original

    def test_rejects_unmerged_release(self):
        for status in ("behind", "diverged"):
            self.status = status
            with self.assertRaisesRegex(ValueError, "not on main"):
                self.proposal()

    def test_rejects_moved_tag(self):
        self.commits = [COMMIT, "b" * 40]
        with self.assertRaisesRegex(ValueError, "tag moved"):
            self.proposal()

    def test_rejects_changed_formula(self):
        proposal = self.proposal()
        with self.assertRaisesRegex(ValueError, "Formula changed"):
            render(FORMULA + "# concurrent edit\n", proposal)

    def test_rejects_tampered_url_or_checksum(self):
        proposal = self.proposal()
        for field, value in (("url", "https://example.com/source.tar.gz"), ("sha256", '"; system "bad"')):
            altered = {**proposal, field: value}
            with self.assertRaises(ValueError):
                render(FORMULA, altered)

    def test_rejects_ambiguous_formula(self):
        with self.assertRaises(ValueError):
            prepare(FORMULA + FORMULA, self.fetch, lambda _: b"archive")

    def test_repo_formula_supported(self):
        formula = (Path(__file__).resolve().parents[2] / "Formula/clipport.rb").read_text()
        self.assertIsInstance(version(current_tag(formula)), tuple)


if __name__ == "__main__":
    unittest.main()
