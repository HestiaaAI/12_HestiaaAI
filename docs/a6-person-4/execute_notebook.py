"""Execute P4's notebook with a locally registered hestia-p4 kernel.

Before running: python -m ipykernel install --prefix .venv --name hestia-p4
Run with the Python 3.11 benchmark environment from the repository root.
"""
import os
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.environ["JUPYTER_PATH"] = str(ROOT / ".venv/share/jupyter")
os.environ["JUPYTER_RUNTIME_DIR"] = str(ROOT / ".local-backups/jupyter-runtime")
os.environ["JUPYTER_CONFIG_DIR"] = str(ROOT / ".local-backups/jupyter-config")
os.environ["IPYTHONDIR"] = str(ROOT / ".local-backups/ipython")

import nbformat
from nbclient import NotebookClient

parser = argparse.ArgumentParser()
parser.add_argument("--notebook", default="llm-test/person4_small_reference.ipynb")
path = ROOT / parser.parse_args().notebook
notebook = nbformat.read(path, as_version=4)
client = NotebookClient(notebook, timeout=900, kernel_name="hestia-p4", resources={"metadata": {"path": str(ROOT)}})
try:
    client.execute()
finally:
    nbformat.write(notebook, path)
errors = [output for cell in notebook.cells for output in cell.get("outputs", []) if output.output_type == "error"]
if errors:
    raise RuntimeError("Notebook execution recorded errors")
print("Executed", sum(cell.cell_type == "code" for cell in notebook.cells), "code cells without errors:", path)
