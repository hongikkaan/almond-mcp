"""Keep the one-input policy enforceable without opening Rhino or the model."""
from pathlib import Path
import unittest


class TestInputs(unittest.TestCase):
    def test_only_the_existing_representative_model_is_stored(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(sorted(str(p.relative_to(root)) for p in root.rglob('*')
                                if p.is_file() and p.suffix.lower() == '.3dm'), ['TEST.3dm'])
