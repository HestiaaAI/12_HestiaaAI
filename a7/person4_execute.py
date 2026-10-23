"""Execute only the two lightweight integration notebooks, never SLM training."""
from pathlib import Path
import sys
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpec


def main():
    root = Path(__file__).resolve().parents[1]
    for relative in ('a7/multi_model_system.ipynb', 'a7/slm/person4_comparison.ipynb'):
        path = root/relative
        print(f'Executing {relative}', flush=True)
        notebook = nbformat.read(path, as_version=4)
        manager = KernelManager(kernel_name='python3')
        # Use this exact environment without installing a global user kernelspec.
        manager._kernel_spec = KernelSpec(argv=[sys.executable, '-m', 'ipykernel_launcher',
                                                '-f', '{connection_file}'],
                                          display_name='Assignment environment', language='python',
                                          env={'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '2',
                                               'MKL_NUM_THREADS': '2'})
        client = NotebookClient(notebook, km=manager, timeout=180,
                                resources={'metadata': {'path': str(root)}})
        client.execute(cleanup_kc=True)
        nbformat.write(notebook, path)
        print(f'Executed and saved {relative}', flush=True)


if __name__ == '__main__':
    main()
