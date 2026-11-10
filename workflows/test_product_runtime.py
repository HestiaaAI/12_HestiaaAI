"""The product must import and render independently of research/model packages."""
import io
import os
import subprocess
import sys
import tarfile
from pathlib import Path
from django.conf import settings
from django.test import SimpleTestCase

class RuntimeBoundaryTests(SimpleTestCase):
    def test_startup_without_research_plotting_or_inference_imports(self):
        script = '''
import importlib.abc, sys
from unittest.mock import patch
class BlockResearch(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'a7','a8','a9','a6_results','matplotlib','torch','transformers','numpy'}:
            raise ImportError('Product eagerly imported removed/heavy package: '+fullname)
sys.meta_path.insert(0, BlockResearch())
patch('environ.Env.read_env').start()
import django
django.setup()
from django.core.checks import run_checks
assert not run_checks()
print('product startup independent')
'''
        env=os.environ.copy()
        env.update(SECRET_KEY='test-only-runtime-imports',DJANGO_SETTINGS_MODULE='hestia_config.settings.development',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
        result=subprocess.run([sys.executable,'-c',script],cwd=settings.BASE_DIR,env=env,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('product startup independent',result.stdout)

    def test_product_archive_excludes_research_and_user_database(self):
        result=subprocess.run(['git','archive','--worktree-attributes','--format=tar','HEAD'],cwd=settings.BASE_DIR,capture_output=True,check=True)
        with tarfile.open(fileobj=io.BytesIO(result.stdout)) as archive:
            names=archive.getnames()
        for name in names:
            self.assertFalse(name.split('/')[0] in {'a7','a8','a9','a6_results','llm-test','db.sqlite3','README_AI.md'},name)
            self.assertFalse(name.endswith('.ipynb'),name)
        self.assertIn('manage.py',names)
        self.assertIn('workflows/ai_views.py',names)
        self.assertIn('workflows/services/hf_local.py',names)
        self.assertIn('requirements.txt',names)
