"""Independently rerun the tiny supplied training recipe without changing peer exports."""
import copy
import json
import platform
from pathlib import Path

import torch
from a7.person3.finetune_slm import calculate_loss, get_batch, encode, training_examples, baseline_prompt
from a7.slm.handoff import load_selected, generate, state_hash


def main():
    root=Path(__file__).resolve().parents[1]
    source=json.loads((root/'a7/person3/results/finetune_results.json').read_text())
    config=source['fine_tune']
    torch.set_num_threads(config['threads'])
    model,vocab=load_selected()
    original=state_hash(model)
    before=copy.deepcopy(model.state_dict())
    examples=training_examples(source['documents'],source['questions'])
    assert examples==source['examples'] and original==source['original_state_sha256']
    data=encode(('\n'.join(examples)+'\n')*40,vocab)
    torch.manual_seed(config['seed'])
    model.train()
    optimizer=torch.optim.AdamW(model.parameters(),lr=config['learning_rate'],weight_decay=config['weight_decay'])
    losses=[]
    for _ in range(config['steps']):
        x,y=get_batch(data,model.context_length,config['batch_size'],'cpu')
        optimizer.zero_grad()
        loss=calculate_loss(model(x),y)
        loss.backward()
        optimizer.step()
        losses.append(loss.item())
    model.eval()
    tuned=state_hash(model)
    rows=[]
    for row in source['after']:
        response=generate(model,vocab,row['prompt'],**{k:source['generation'][k] for k in
            ('seed','temperature','max_new_tokens')})[len(row['prompt']):]
        rows.append(dict(question_id=row['question_id'],exact_match=response==row['response'],
                         local_response=response))
    report=dict(method='Independent original checkpoint plus supplied 300-step recipe; source exports and checkpoint files not modified.',
                environment=dict(platform=platform.platform(),torch=torch.__version__),
                original_state_sha256=original,local_finetuned_state_sha256=tuned,
                exported_finetuned_state_sha256=source['finetuned_state_sha256'],
                exact_state_match=tuned==source['finetuned_state_sha256'],
                weights_updated=any(not torch.equal(before[k],v) for k,v in model.state_dict().items()),
                local_initial_loss=losses[0],local_final_loss=losses[-1],
                matching_responses=sum(r['exact_match'] for r in rows),total_responses=len(rows),responses=rows,
                limitation='Floating point training can differ across platforms; mismatches do not replace source evidence.')
    (root/'a7/results/architecture/finetune_reproduction_check.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f"Fine-tune reproduction: exact state={report['exact_state_match']}, responses={report['matching_responses']}/5; changed weights={report['weights_updated']}")


if __name__=='__main__':
    main()
