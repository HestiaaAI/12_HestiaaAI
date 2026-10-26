"""Validate the approved-account Llama run and replace only its old error rows."""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re
import zipfile
from html.parser import HTMLParser

import nbformat
from a7.benchmark_contract import PROMPTS
from a7.benchmark_runner import RESULT_COLUMNS, select_models, validate_result_rows

ROOT=Path(__file__).resolve().parents[1]
MODEL='meta-llama/Llama-3.2-3B-Instruct'
CSV='architecture_llama_cuda.csv'
ENV='architecture_llama_cuda.environment.json'


class DisplayRows(HTMLParser):
    """Read saved dataframe text without executing notebook HTML or scripts."""
    def __init__(self):
        super().__init__();self.in_table=False;self.in_cell=False;self.row=[];self.rows=[]
    def handle_starttag(self,tag,attrs):
        if tag=='table':self.in_table=True
        if self.in_table and tag=='tr':self.row=[]
        if self.in_table and tag=='td':self.in_cell=True;self.text=[]
    def handle_data(self,data):
        if self.in_cell:self.text.append(data)
    def handle_endtag(self,tag):
        if tag=='td' and self.in_cell:
            self.row.append(''.join(self.text));self.in_cell=False
        if tag=='tr' and self.in_table and self.row:self.rows.append(self.row)
        if tag=='table':self.in_table=False


def verified_rows(bundle, notebook, root=ROOT):
    with zipfile.ZipFile(bundle) as archive:
        if set(archive.namelist())!={CSV,ENV} or len(archive.namelist())!=2:
            raise ValueError('Expected only Llama CSV and environment, no weights or unrelated files')
        if any(i.file_size>10_000_000 for i in archive.infolist()):
            raise ValueError('Evidence file unexpectedly large')
        payloads={name:archive.read(name) for name in (CSV,ENV)}
    environment=json.loads(payloads[ENV]);condition=environment['condition']
    expected={'model_id':MODEL,'owner':'architecture','device':'cuda','dtype':'float16',
              'quantization':'none','max_new_tokens':220,'do_sample':False,'batch_size':1}
    if any(condition.get(k)!=v for k,v in expected.items()):
        raise ValueError('Unexpected model/device/generation condition')
    if hashlib.sha256(payloads[CSV]).hexdigest()!=environment['result_csv_sha256']:
        raise ValueError('CSV does not match exported hash')
    source_files={'__init__.py','benchmark_contract.py','benchmark_runner.py','review_results.py'}
    if set(condition['contract_source_sha256'])!=source_files:
        raise ValueError('Unexpected shared source set')
    for name,digest in condition['contract_source_sha256'].items():
        if hashlib.sha256((root/'a7'/name).read_text().encode()).hexdigest()!=digest:
            raise ValueError(f'Shared benchmark source differs: {name}')
    rows=list(csv.DictReader(io.StringIO(payloads[CSV].decode())))
    validate_result_rows(rows,select_models(model_ids=[MODEL]),PROMPTS)
    prompts={p['prompt_id']:p for p in PROMPTS}
    model=select_models(model_ids=[MODEL])[0]
    for row in rows:
        prompt=prompts[row['prompt_id']]
        latency=float(row['latency_seconds']);rate=float(row['tokens_per_second'])
        if (row['status']!='ok' or row['error'] or row['device']!='cuda'
                or row['owner']!='architecture' or row['model_category']!=model['category']
                or row['prompt']!=prompt['input'] or row['prompt_type']!=prompt['prompt_type']
                or int(row['max_new_tokens'])!=220 or not row['generated_output'].strip()
                or not 0<int(row['output_tokens'])<=220
                or not math.isfinite(latency) or latency<=0
                or not math.isfinite(rate) or rate<=0):
            raise ValueError('Requires 25 successful exact-contract Llama generations')
        tolerance=.0001+int(row['output_tokens'])*.000051/(latency*(latency-.000051))
        if abs(rate-int(row['output_tokens'])/latency)>tolerance:
            raise ValueError('Reported throughput differs from tokens divided by latency')
    nb=nbformat.read(notebook,as_version=4);nbformat.validate(nb)
    cells=[c for c in nb.cells if c.cell_type=='code']
    if any(c.execution_count is None or any(o.output_type=='error' for o in c.outputs) for c in cells):
        raise ValueError('Notebook must preserve completed cells without saved errors')
    text=Path(notebook).read_text()
    for pattern in (r'hf_[A-Za-z0-9]{20,}',r'gsk_[A-Za-z0-9]{20,}'):
        if re.search(pattern,text):
            raise ValueError('Credential pattern in notebook; remove credentials before import')
    parser=DisplayRows()
    for cell in cells:
        for output in cell.outputs:
            parser.feed(''.join(output.get('data',{}).get('text/html','')))
    previews={r[0]:r[1] for r in parser.rows if len(r)==2 and r[0] in prompts}
    timings={r[0]:r[1:] for r in parser.rows if len(r)==5 and r[0] in prompts}
    for row in rows:
        expected_output=row['generated_output'].replace('\n','\\n')
        preview=previews.get(row['prompt_id'],'')
        matches=(expected_output.startswith(preview[:-3]) if preview.endswith('...')
                 else expected_output==preview)
        if not preview or not matches:
            raise ValueError('Notebook response preview differs from CSV')
        if timings.get(row['prompt_id'])!=[row[k] for k in
                ('status','latency_seconds','output_tokens','tokens_per_second')]:
            raise ValueError('Notebook timing/status table differs from CSV')
    audit=json.loads((root/'a7/architecture/llama_review_audit.json').read_text())
    entries={e['prompt_id']:e for e in audit['entries']}
    if len(entries)!=25 or len(audit['entries'])!=25:
        raise ValueError('One inspected review per prompt is required')
    for row in rows:
        entry=entries[row['prompt_id']]
        if hashlib.sha256(row['generated_output'].encode()).hexdigest()!=entry['response_sha256']:
            raise ValueError('Changed continuation needs a fresh review')
        components=entry['components']
        if len(components)!=5 or any(type(v) is not int or not 0<=v<=cap
                                    for v,cap in zip(components,[3,2,2,2,1])):
            raise ValueError('Invalid rubric components')
        row.update(dict(zip(audit['component_order'],components)))
        row['self_evaluation_score_1_to_10']=max(1,sum(components))
        row['review_notes']='Assistant response-level review; student signoff pending. '+entry['notes']
    return rows,payloads,condition


def import_results(bundle,notebook,root=ROOT):
    rows,payloads,condition=verified_rows(bundle,notebook,root)
    folder=root/'a7/results';canonical=folder/'architecture_benchmark.csv'
    old=canonical.read_bytes()
    original=list(csv.DictReader(io.StringIO(old.decode())))
    retained=[r for r in original if r['model_id']!=MODEL]
    merged=retained+rows
    validate_result_rows(merged,select_models(owner='architecture'),PROMPTS)
    archive=folder/'architecture_before_llama_colab.csv'
    if not archive.exists():archive.write_bytes(old)
    for name,payload in payloads.items():(folder/name).write_bytes(payload)
    (root/'a7/architecture_llama_colab.ipynb').write_bytes(Path(notebook).read_bytes())
    temporary=canonical.with_suffix('.csv.tmp')
    with temporary.open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=RESULT_COLUMNS,lineterminator='\n')
        writer.writeheader();writer.writerows(merged)
    temporary.replace(canonical)
    path=folder/'architecture_benchmark_environment.json';metadata=json.loads(path.read_text())
    metadata['models'][MODEL]={'device':'cuda','dtype':'float16','gpu':condition['gpu'],
        'environment_file':ENV,'status':'25 successful approved-account Colab evaluations; review audit retained'}
    path.write_text(json.dumps(metadata,indent=2)+'\n')
    report={'raw_csv_sha256':hashlib.sha256(payloads[CSV]).hexdigest(),
        'notebook_sha256':hashlib.sha256(Path(notebook).read_bytes()).hexdigest(),
        'successful_rows':25,'source_hashes_match':True,'notebook_response_previews_match':True,
        'notebook_timings_match':True,
        'preview_limitation':'Long notebook outputs are truncated previews; full responses preserved/reviewed in raw CSV.',
        'prior_non_llama_rows_preserved':len(retained),
        'raw_outputs_unchanged':True,'reviews':'AI-assisted; student signoff pending',
        'old_matrix_archive':str(archive.relative_to(root))}
    (folder/'architecture_llama_import_verification.json').write_text(json.dumps(report,indent=2)+'\n')
    return merged


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle',type=Path);parser.add_argument('notebook',type=Path)
    args=parser.parse_args();rows=import_results(args.bundle,args.notebook)
    print('Imported/reviewed 25 Llama generations; architecture matrix:',len(rows),'rows.')
