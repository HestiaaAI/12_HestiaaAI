# Reproduce the official Vega-Lite editor check

The official editor supports local development:
https://github.com/vega/editor#development-setup

Keep this tooling outside the Hestia repository and deployment. It is needed
only to author/check charts; the Django website does not depend on Node.js.
Prerequisites: Git, Node.js and npm. The commands below were verified on Windows.

## First-time setup (PowerShell)

From a separate tools directory, clone the upstream editor and select the exact
revision used for the submitted screenshots:

```powershell
git clone https://github.com/vega/editor.git editor
Set-Location editor
git checkout 84a605ccc791fd73644ab86b7e25547af044accb
npm.cmd ci --ignore-scripts --no-audit --no-fund
New-Item -ItemType Directory -Force -Path public/spec/vega,public/spec/vega-lite | Out-Null
Invoke-WebRequest 'https://vega.github.io/editor/spec/vega/index.json' -OutFile public/spec/vega/index.json
Invoke-WebRequest 'https://vega.github.io/editor/spec/vega-lite/index.json' -OutFile public/spec/vega-lite/index.json
```

The two indexes satisfy the editor's example-menu imports. This Windows setup
skips the upstream Bash vendor script and does not install the full example
gallery or its datasets; Hestia's charts use the Django API instead.

## Run and capture evidence

1. In the Hestia project, run `.venv/Scripts/python.exe manage.py runserver 8000`.
2. In the editor directory, run:

   ```powershell
   $env:BROWSER = 'none'
   npm.cmd run start -- --host 127.0.0.1 --port 1234 --strictPort
   ```

3. Open http://127.0.0.1:1234/editor/ and select Vega-Lite.
4. Paste `docs/a4-person-1/specs/task-priorities.vl.json` into the editor and Run.
5. Check the bars against http://127.0.0.1:8000/api/charts/task-priorities/.
   Save a screenshot showing both the JSON `data.url` and the rendered chart.
6. Repeat with `task-creations.vl.json` and the task-creations API. The line counts
   are daily UTC totals, with zero days between first and last creation.
7. Use Export > JSON > Vega-Lite to save specs, and Export > PNG for snapshots.
   The checked-in specs are also served by Hestia's `/vega-lite/chart1.json` and
   `/vega-lite/chart2.json` routes, so the website uses the same definitions.
8. Stop the editor with Ctrl+C when finished. Keep it out of PythonAnywhere.

For the existing setup on this computer, the editor directory is
`E:/Hestia/a4-vega-editor/editor`; the first-time setup is already done.

After the in-class deployment, use the public HTTPS API URLs in the hosted
editor at https://vega.github.io/editor/ and save additional deployed evidence.
Do not replace URL data with inline values to work around a connection problem.
