"""Drift guard for helpers vendored from the author's other HerdR plugins."""
import hashlib
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / 'src' / 'herdr_fleet'

VENDORED = {
    'search.py': 'f925011c6200d598de507aecef34e91a707e8658bcbc07ed2078a15496abc408',
    'terminal.py': '1b8260c746e18eb338f9535f586abfed01aaabea7832135b7362713325711a20',
    'text.py': 'c9467cc4bd0cd09580f512682d9e20578b4e51414f70212383afbd36b3532db8',
    'theme.py': '771f66e17901fc4465284c90da6ff9a51d16791e41796ccdefd7fb5d790a9d9d',
}


class VendoredHelpersTest(unittest.TestCase):
    def test_hashes_match(self):
        for name, expected in VENDORED.items():
            actual = hashlib.sha256((SRC / name).read_bytes()).hexdigest()
            self.assertEqual(
                actual, expected,
                '%s is a vendored helper and must be changed deliberately: '
                'update its hash in tests/test_vendored.py and add a CHANGELOG entry.' % name)


if __name__ == '__main__':
    unittest.main()
