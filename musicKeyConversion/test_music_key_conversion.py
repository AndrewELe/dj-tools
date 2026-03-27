import importlib.util
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent


def load_module(filename: str, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, HERE / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


camelot_to_comments = load_module("camelot_to_comments.py", "camelot_to_comments")
camelot_converter = load_module("camelot_converter.py", "camelot_converter")


class SharedBehaviorTests(unittest.TestCase):
    def test_parse_key_handles_common_spellings(self):
        cases = {
            "Am": ("A", "minor"),
            "A minor": ("A", "minor"),
            "C#": ("C#", "major"),
            "Db": ("C#", "major"),
            "Ebm": ("D#", "minor"),
            "Initial Key: F# minor": ("F#", "minor"),
            "key: bbm": ("A#", "minor"),
        }

        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(camelot_to_comments.parse_key(raw), expected)
                self.assertEqual(camelot_converter.parse_key(raw), expected)

    def test_extract_key_info_preserves_invalid_candidate(self):
        candidates = ["DefinitelyNotAKey"]

        self.assertEqual(
            camelot_to_comments.extract_key_info(candidates),
            ("DefinitelyNotAKey", None),
        )
        self.assertEqual(
            camelot_converter.extract_key_info(candidates),
            ("DefinitelyNotAKey", None),
        )

    def test_extract_key_info_uses_first_valid_candidate(self):
        candidates = ["DefinitelyNotAKey", "C#m"]

        self.assertEqual(
            camelot_to_comments.extract_key_info(candidates),
            ("C#m", ("C#", "minor")),
        )
        self.assertEqual(
            camelot_converter.extract_key_info(candidates),
            ("C#m", ("C#", "minor")),
        )

    def test_comment_builder_omits_missing_bpm(self):
        self.assertEqual(
            camelot_to_comments.build_comment_value("9A", "Em", ""),
            "9A | Em",
        )
        self.assertEqual(
            camelot_to_comments.build_comment_value("9A", "Em", "174"),
            "9A | Em | 174",
        )

    def test_default_filename_builder_omits_missing_bpm(self):
        self.assertEqual(
            camelot_converter.build_default_filename_stem("9A", "Em", "", "Artist", "Title"),
            "9A | Em - Artist - Title",
        )
        self.assertEqual(
            camelot_converter.build_default_filename_stem("9A", "Em", "174", "Artist", "Title"),
            "9A | Em | 174 - Artist - Title",
        )

    def test_title_builder_prefixes_camelot_and_key_without_stacking(self):
        self.assertEqual(
            camelot_to_comments.build_title_value("9A", "Em", "Sunday Sunrise"),
            "9A | Em - Sunday Sunrise",
        )
        self.assertEqual(
            camelot_to_comments.build_title_value("10A", "Bm", "9A | Em - Sunday Sunrise"),
            "10A | Bm - Sunday Sunrise",
        )
        self.assertEqual(
            camelot_converter.build_title_value("9A", "Em", "Sunday Sunrise"),
            "9A | Em - Sunday Sunrise",
        )

    def test_script_folder_can_be_relocated(self):
        for filename in ("camelot_to_comments.py", "camelot_converter.py", "inspect_tags.py"):
            with self.subTest(filename=filename):
                self.assertTrue((HERE / filename).is_file())

    def test_decode_value_handles_scalar_text_attribute(self):
        class DummyTextFrame:
            text = "174"

        self.assertEqual(camelot_to_comments.decode_value(DummyTextFrame()), ["174"])
        self.assertEqual(camelot_converter.decode_value(DummyTextFrame()), ["174"])

if __name__ == "__main__":
    unittest.main()
