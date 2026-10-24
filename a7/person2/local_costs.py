"""Reproducible 90-case inference-tier planning estimate; never launches models/cloud VMs."""
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path
from a7.benchmark_contract import MODEL_REGISTRY
from a7.architecture_analysis import TRAFFIC

ROOT = Path(__file__).resolve().parents[2]


def capacity_rate(parameters, anchors):
    """Explicit size-only proxy for unmeasured models, not empirical throughput."""
    anchors = sorted(anchors)
    if parameters <= anchors[0][0]:
        return anchors[0][1]
    if parameters >= anchors[-1][0]:
        return anchors[-1][1] * anchors[-1][0] / parameters
    for (p0, r0), (p1, r1) in zip(anchors, anchors[1:]):
        if p0 <= parameters <= p1:
            fraction = math.log(parameters/p0) / math.log(p1/p0)
            return math.exp(math.log(r0) + fraction*math.log(r1/r0))
    raise ValueError('No interpolation bracket')


def machines_needed(daily_output_tokens, rate, config, rate_factor=1.0):
    if daily_output_tokens < 0 or rate <= 0 or rate_factor <= 0:
        raise ValueError('Use nonnegative token load and positive rates')
    if not 0 < config['target_utilization'] <= 1 or config['peak_to_average'] < 1:
        raise ValueError('Invalid utilization/peak assumption')
    effective = rate * rate_factor * config['target_utilization'] / config['service_time_penalty']
    count = math.ceil(daily_output_tokens * config['peak_to_average'] / (86400*effective))
    return max(config['minimum_replicas'], count) + config['standby_replicas']


def build_tables(config, benchmark_rows):
    registry = {m['model_id']:m for m in MODEL_REGISTRY}
    measured = {}
    for model in MODEL_REGISTRY:
        rows = [r for r in benchmark_rows if r['model_id']==model['model_id'] and r['status']=='ok']
        if rows:
            if len(rows) != 25 or len({r['prompt_id'] for r in rows}) != 25:
                raise ValueError('Capacity anchors require all 25 successful distinct prompts')
            measured[model['model_id']] = statistics.median(float(r['tokens_per_second']) for r in rows)
    if len(measured) != 4:
        raise ValueError('Expected exactly the four labeled Person 2 T4 anchors')
    anchors = [(registry[mid]['params_b'],rate) for mid,rate in measured.items()]
    cloud = config['cloud']; costs=[]; sensitivity=[]; rates=[]
    compute_daily = cloud['compute_usd_per_hour'] * config['hours_per_day']
    storage_daily = (cloud['container_disk_gb']+cloud['volume_disk_gb'])*cloud['running_storage_usd_per_gb_month']/config['days_per_month']
    for model in MODEL_REGISTRY:
        mid=model['model_id']; rate=measured.get(mid,capacity_rate(model['params_b'],anchors))
        rate *= config['capacity']['hardware_transfer_multiplier']
        origin='measured_T4_proxy_transferred_to_3090' if mid in measured else 'assumed_size_interpolation_T4_proxy_transferred_to_3090'
        memory=model['params_b']*config['capacity']['weight_budget_bytes_per_parameter']+config['capacity']['runtime_and_kv_budget_gb']
        if memory>cloud['gpu_vram_gb']:
            raise ValueError(f'Planning memory fit fails for {mid}; choose and price a larger machine')
        rates.append(dict(model_id=mid,params_b=model['params_b'],planning_tokens_per_second=rate,
                          rate_basis=origin,planning_memory_gb=memory,memory_fit_assumed=True))
        for traffic,dau in TRAFFIC.items():
            requests=dau*config['requests_per_user']; daily_out=requests*config['output_tokens_per_request']
            machines=machines_needed(daily_out,rate,config)
            source=f"{cloud['price_source']} checked {config['as_of_date']}; {origin}; explicit assumptions in a7/person2/cost_assumptions.json"
            costs.append(dict(model_id=mid,model_category=model['category'],traffic_category=traffic,daily_active_users=dau,
                requests_per_user=config['requests_per_user'],input_tokens_per_request=config['input_tokens_per_request'],
                output_tokens_per_request=config['output_tokens_per_request'],avg_tokens_per_user=config['requests_per_user']*config['output_tokens_per_request'],
                total_daily_requests=requests,total_daily_input_tokens=requests*config['input_tokens_per_request'],
                total_daily_output_tokens=daily_out,total_daily_token_load=daily_out,
                assumptions_id=config['assumptions_id'],source_or_assumption=source,
                cloud_configuration=cloud['configuration'],gpu=cloud['gpu'],gpu_vram_gb=cloud['gpu_vram_gb'],
                vcpu_per_machine=cloud['vcpu_per_machine'],host_ram_gb=cloud['host_ram_gb'],
                planning_memory_gb=round(memory,6),planning_tokens_per_second=round(rate,6),rate_basis=origin,
                hardware_transfer_multiplier=config['capacity']['hardware_transfer_multiplier'],
                target_utilization=config['target_utilization'],peak_to_average=config['peak_to_average'],service_time_penalty=config['service_time_penalty'],
                per_machine_compute_usd_hour=cloud['compute_usd_per_hour'],per_machine_compute_usd_day=compute_daily,
                per_machine_storage_usd_day=round(storage_daily,8),per_machine_total_usd_day=round(compute_daily+storage_daily,8),
                machines_needed=machines,gpus_needed=machines*cloud['gpu_count_per_machine'],
                total_machine_compute_usd_day=round(machines*compute_daily,6),
                total_storage_usd_day=round(machines*storage_daily,6),
                total_daily_cost_usd=round(machines*(compute_daily+storage_daily),6),
                scope='inference tier only; see explicit exclusions',price_checked_date=config['as_of_date']))
            for factor in (.5,1.,2.):
                count=machines_needed(daily_out,rate,config,rate_factor=factor)
                sensitivity.append(dict(model_id=mid,traffic_category=traffic,rate_factor=factor,
                    machines_needed=count,total_daily_cost_usd=round(count*(compute_daily+storage_daily),6),
                    scenario='assumed throughput sensitivity, not measured batching or hardware speedup'))
    return costs,rates,sensitivity


def write_csv(path, rows):
    with Path(path).open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def main():
    path=ROOT/'a7/person2/cost_assumptions.json';config=json.loads(path.read_text())
    benchmark=ROOT/'a7/results/person2_nf4_colab/person2_benchmark.csv'
    with benchmark.open(newline='') as f: rows=list(csv.DictReader(f))
    costs,rates,sensitivity=build_tables(config,rows)
    assert len(costs)==90 and len({(r['model_id'],r['traffic_category']) for r in costs})==90
    write_csv(ROOT/'a7/results/local_costs.csv',costs)
    write_csv(ROOT/'a7/results/person2_capacity_assumptions.csv',rates)
    write_csv(ROOT/'a7/results/person2_local_cost_sensitivity.csv',sensitivity)
    (ROOT/'a7/results/local_costs.provenance.json').write_text(json.dumps({
        'assumptions_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'benchmark_sha256':hashlib.sha256(benchmark.read_bytes()).hexdigest(),
        'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'rows':len(costs),'measured_T4_anchors':4,'unmeasured_model_capacity_proxies':11,
        'all_RTX3090_capacities_are_unvalidated':True,
        'scope':'Planning estimates; no cloud resources provisioned or production load test performed.'},indent=2)+'\n')
    print('Wrote 90 local costs, 15 capacity assumptions and 270 sensitivity cases.')


if __name__=='__main__':main()
