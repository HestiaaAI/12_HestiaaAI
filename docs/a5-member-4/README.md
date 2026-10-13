# A5 Member 4 — three alternative uses of the public API

Public production API (same URL as Member 3’s Vega-Lite chart):

https://hestia12.pythonanywhere.com/api/charts/task-priorities/

No login required. Response is database-backed JSON: `label` and `count` only.

## Use case 1 — Python aggregation

Someone else can call the API from a Python script and compute simple workload
stats (total tasks, High + Urgent share, largest priority bucket) without using
the Hestia UI.

- Test code: [use-cases/01_python_aggregation.py](use-cases/01_python_aggregation.py)
- Screenshot: [screenshots/01_python_aggregation.png](screenshots/01_python_aggregation.png)

## Use case 2 — Import into a spreadsheet

The same JSON can be exported to CSV and opened in Excel, Google Sheets, or
Numbers so others can build their own tables or charts.

- Test code: [use-cases/02_export_csv.py](use-cases/02_export_csv.py)
- CSV output: [outputs/task_priorities.csv](outputs/task_priorities.csv)
- Screenshots: [screenshots/02_export_csv.png](screenshots/02_export_csv.png),
  [screenshots/02_numbers.png](screenshots/02_numbers.png)

## Use case 3 — Statistical summary

The API can also support a notebook-style analysis: mean tasks per priority,
max bucket, whether Urgent is empty, and a weighted attention score.

- Test code: [use-cases/03_priority_stats.py](use-cases/03_priority_stats.py)
- Screenshot: [screenshots/03_priority_stats.png](screenshots/03_priority_stats.png)

## Opening slide (video)

[video/opening-slide.html](video/opening-slide.html) 