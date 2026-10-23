"""Run Person 4's unchanged shared benchmark on CPU, with auditable environment."""
import importlib.metadata
import argparse
import json
import os
from pathlib import Path
import platform
import sys
from datetime import datetime, timezone


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dtype', choices=['float32', 'float16'], default='float32')
    parser.add_argument('--output', type=Path, default=root/'a7/results/person4_benchmark.csv')
    parser.add_argument('--check-access', action='store_true')
    args = parser.parse_args()
    # Keep downloaded weights within the repository's ignored cache directory.
    os.environ.setdefault('HF_HOME', str(root/'model_cache/huggingface'))
    if args.check_access:
        from huggingface_hub import get_token, hf_hub_download
        authenticated = bool(get_token())
        print('Local Hugging Face authentication present:', authenticated, flush=True)
        if not authenticated:
            print('Authenticate in this HF_HOME before accessing the approved gated model.', flush=True)
            return
        try:
            hf_hub_download('meta-llama/Llama-3.2-3B-Instruct', 'config.json')
        except Exception as exc:
            print('Gated model access check failed:', type(exc).__name__, flush=True)
            response = getattr(exc, 'response', None)
            if response is not None:
                print('HTTP status:', response.status_code, flush=True)
            print(str(exc)[:900], flush=True)
            return
        print('Llama gated configuration download succeeded.', flush=True)
        return
    import psutil
    import torch
    from a7.benchmark_runner import run_matrix, select_models
    torch.set_num_threads(4)
    out = root/'a7/results'
    out.mkdir(parents=True, exist_ok=True)
    environment = dict(
        recorded_at_utc=datetime.now(timezone.utc).isoformat(),
        python=sys.version, platform=platform.platform(), processor=platform.processor(),
        physical_cores=psutil.cpu_count(logical=False), logical_cores=psutil.cpu_count(),
        total_ram_bytes=psutil.virtual_memory().total, device='cpu', dtype=args.dtype,
        threads=torch.get_num_threads(), max_new_tokens=220, do_sample=False,
        timing_scope='shared runner: prefill + decode, excludes model loading; no warmup',
        timing_caveat='Interactive workstation; lightweight notebook validation ran concurrently during part of SmolLM. Timings are exploratory, not isolated load-test measurements.',
        packages={name: importlib.metadata.version(name) for name in
                  ('torch', 'transformers', 'huggingface-hub', 'numpy', 'pandas')})
    args.output.with_name(args.output.stem+'_environment.json').write_text(json.dumps(environment, indent=2), encoding='utf-8')
    print('Starting 75 evaluations on CPU; checkpoints after each prompt.', flush=True)
    rows = run_matrix(select_models(owner='P4'), args.output,
                      device_request='cpu', dtype_request=args.dtype)
    print(f"Recorded {len(rows)} attempts, {sum(r['status']=='ok' for r in rows)} successful.", flush=True)


if __name__ == '__main__':
    main()
