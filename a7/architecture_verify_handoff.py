"""Reproduce the 25 exported prompts without rebuilding tied retrieval rankings."""
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path


def main():
    import torch
    from a7.slm.handoff import load_selected, generate, state_hash
    root=Path(__file__).resolve().parents[1]
    folder=root/'a7/slm/results/person2_rag_colab'
    verification=json.loads((folder/'verification.json').read_text())
    checked={}
    for name,expected in verification['files_sha256'].items():
        content=(folder/name).read_bytes()
        actual=hashlib.sha256(content).hexdigest()
        normalized=hashlib.sha256(content.replace(b'\r\n',b'\n')).hexdigest()
        if expected not in (actual,normalized):
            raise ValueError(f'Changed handoff file: {name}')
        checked[name]=dict(expected_sha256=expected,checkout_sha256=actual,
                           normalized_lf_sha256=normalized,
                           match_basis='exact bytes' if actual==expected else 'canonical LF; Git Windows checkout changed line endings only')
    evidence=json.loads((folder/'person2_rag_reviewed.json').read_text())
    manifest=json.loads((root/'a7/slm/results/selected_checkpoint.json').read_text())
    torch.set_num_threads(2)
    model,vocab=load_selected()
    before=state_hash(model)
    if before!=manifest['state_sha256'] or before!=evidence['original_state_sha256']:
        raise ValueError('Checkpoint identity mismatch')
    expected_generation={**manifest['generation'],'device':'cpu','threads':2}
    if evidence['generation']!=expected_generation:
        raise ValueError('Generation-setting mismatch')
    rows=[]
    for question in evidence['questions']:
        for condition,row in [('baseline',question['baseline'])]+[
                (f"rag_top_{r['top_k']}",r) for r in question['rag']]:
            text=generate(model,vocab,row['prompt'],**manifest['generation'])[len(row['prompt']):]
            rows.append(dict(question_id=question['question_id'],condition=condition,
                             exact_match=text==row['response'],
                             exported_response_sha256=hashlib.sha256(row['response'].encode()).hexdigest(),
                             local_response_sha256=hashlib.sha256(text.encode()).hexdigest(),
                             local_response=text))
    after=state_hash(model)
    if before!=after:
        raise ValueError('Inference changed weights')
    report=dict(checked_handoff_files_sha256=checked,original_state_sha256=before,
                final_state_sha256=after,weights_unchanged=True,generation=expected_generation,
                local_environment=dict(platform=platform.platform(),python=platform.python_version(),
                                       torch=importlib.metadata.version('torch')),
                exported_environment=evidence.get('environment'),
                matching_responses=sum(r['exact_match'] for r in rows),total_responses=len(rows),
                method='Original checkpoint, exact exported prompts; no retrieval reranking or training.',
                limitation='A mismatch across environments must not silently replace the shared exported baseline.',
                responses=rows)
    out=root/'a7/results/architecture/slm_reproduction_check.json'
    out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(f"Verified handoff file hashes and original weights. Exact response matches: {report['matching_responses']}/{len(rows)}.")


if __name__=='__main__':
    main()
