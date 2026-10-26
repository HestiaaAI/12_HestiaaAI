"""Prevent accidental weight/credential inclusion in the course upload bundle."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from a7.package_submission import build,validate


class SubmissionPackageTests(unittest.TestCase):
    def test_missing_deliverable_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError,'Missing required deliverable'):
                validate(Path(folder))

    def test_excludes_private_files_and_preserves_evidence_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            paths={'a7/results/evidence.csv':b'column\r\noriginal bytes\r\n',
                   'a7/SUBMISSION.md':b'Synthetic package fixture, not experiment evidence.',
                   'a7/slm/checkpoints/selected_baseline.pt':b'private',
                   'a7/results/accidental.bin':b'private',
                   'a7/.env':b'private',
                   'a7/model_cache/config.json':b'private',
                   'assignment2/unrelated.txt':b'unrelated'}
            for name,content in paths.items():
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(content)
            with patch('a7.package_submission.validate'):
                output=build(root)
            with zipfile.ZipFile(output) as archive:
                names=set(archive.namelist())
                self.assertEqual(names,{'README.md','MANIFEST.json','a7/SUBMISSION.md','a7/results/evidence.csv'})
                self.assertEqual(archive.read('a7/results/evidence.csv'),paths['a7/results/evidence.csv'])
                manifest=json.loads(archive.read('MANIFEST.json'))
                self.assertEqual(manifest['files']['a7/results/evidence.csv']['sha256'],
                                 hashlib.sha256(paths['a7/results/evidence.csv']).hexdigest())

    def test_credential_pattern_aborts_before_archive_creation(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'a7').mkdir()
            (root/'a7/SUBMISSION.md').write_text('hf_'+'x'*32,encoding='utf-8')
            with patch('a7.package_submission.validate'):
                with self.assertRaisesRegex(ValueError,'Possible credential'):
                    build(root)
            self.assertFalse((root/'dist/hestia-a7-submission.zip').exists())
