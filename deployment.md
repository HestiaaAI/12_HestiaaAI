# Deploy Hestia to PythonAnywhere

Use the accepted `household-member-management` branch. `main` and `/home/hestia12/12_HestiaaAI` remain the assignment/grading environment: do not update or migrate them for this product release.

## Existing production layout

- Site: https://hestia12.pythonanywhere.com/
- Code: `/home/hestia12/hestia-household-invitations` (the folder name stays the same when its branch changes).
- Environment: `/home/hestia12/.virtualenvs/hestia-a4`.
- Django settings: `deployment_settings` in `/home/hestia12/hestia-phase3-runtime`.
- Product database: `/home/hestia12/hestia-phase3-runtime/product.sqlite3`.
- Private SMTP/provider configuration: `.env` inside the product code folder.
- WSGI: `/var/www/hestia12_pythonanywhere_com_wsgi.py`.
- Static mapping: `/static/` → `/home/hestia12/hestia-household-invitations/staticfiles`.

Keep these paths consistent. Using plain production/development settings instead of `deployment_settings` can select the tracked historical database.

## 1. Open a PythonAnywhere Bash console

```sh
cd /home/hestia12/hestia-household-invitations
source /home/hestia12/.virtualenvs/hestia-a4/bin/activate
export PYTHONPATH="/home/hestia12/hestia-phase3-runtime:$PWD"
export DJANGO_SETTINGS_MODULE=deployment_settings

git status --short
git branch --show-current
git log -1 --oneline
```

Resolve/preserve any tracked local edits before switching branches. Keep `.env`, databases and private setup files out of Git. Do not use `reset --hard` or `clean` to force an update.

## 2. Back up the product database and active deployment settings

Run before applying migrations. This creates a consistent SQLite backup without reading application records into the console.

```sh
python - <<'PY'
from datetime import datetime, timezone
from pathlib import Path
import shutil, sqlite3, subprocess
runtime = Path('/home/hestia12/hestia-phase3-runtime')
database = runtime / 'product.sqlite3'
assert database.is_file(), 'Expected product database is missing; verify settings first.'
backup = runtime / 'backups' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
backup.mkdir(parents=True, mode=0o700)
backup.chmod(0o700)
with sqlite3.connect(str(database)) as source:
    with sqlite3.connect(str(backup / 'product.sqlite3')) as target:
        source.backup(target)
for source in [runtime / 'deployment_settings.py', Path('/var/www/hestia12_pythonanywhere_com_wsgi.py')]:
    shutil.copy2(source, backup / source.name)
(backup / 'release.txt').write_text(subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True))
for item in backup.iterdir():
    item.chmod(0o600)
print('Backup:', backup)
PY
```

Keep the printed backup path for rollback. For a busy production site, arrange a maintenance window so writes do not race a schema cutover.

## 3. Fetch and update the accepted branch

The explicit fetch refspec works even if the original server clone fetched only `main`.

```sh
# Register the branch in a main-only clone so --track recognizes it.
refspec='+refs/heads/household-member-management:refs/remotes/origin/household-member-management'
git config --get-all remote.origin.fetch | grep -Fx -- "$refspec" >/dev/null || git config --add remote.origin.fetch "$refspec"
git fetch origin refs/heads/household-member-management:refs/remotes/origin/household-member-management

if git show-ref --verify --quiet refs/heads/household-member-management; then
    git switch household-member-management
else
    git switch --track origin/household-member-management
fi

git merge --ff-only origin/household-member-management
git log -1 --oneline
```

`fetch` downloads commits; switching/updating changes the checkout. Reload activates the new application workers. If fast-forward fails, inspect the divergence and preserve local commits; do not reset them away.

## 4. Install new dependencies, migrate the correct database, collect assets

This expenses/thermostat integration introduces migrations. The earlier Phase 4 instruction saying no migrations were needed applied only to that release.

The incremental dependency added by this integration is:

```sh
python -m pip install pywebpush==2.5.0
```

For future releases, inspect changes to `requirements.txt` and install the appropriate requirements for the hosted runtime. Local AI model packages/weights remain a separate runtime capability; do not substitute mock AI in production.

```sh
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py showmigrations --plan
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

Run one command at a time and stop if a check fails. Preserve both household migration histories and their merge migration; do not use `--fake` to bypass an error. Do not run demo seed commands on production.

If the console uses a restrictive umask, ensure only the public static tree is readable by the static server:

```sh
python - <<'PY'
from pathlib import Path
from django.conf import settings
import django
django.setup()
root = Path(settings.STATIC_ROOT).resolve()
assert root == Path('/home/hestia12/hestia-household-invitations/staticfiles')
root.chmod(0o755)
for item in root.rglob('*'):
    item.chmod(0o755 if item.is_dir() else 0o644)
PY
```

Keep the database, backups and `.env` private; do not apply those permissions outside the static tree. Existing database-cache configuration and SMTP settings stay in place.

## 5. Reload the web app

Open **PythonAnywhere → Web → Reload hestia12.pythonanywhere.com**. Keep the current WSGI, source/working-directory and static mappings above. If the free site's expiry has passed, renew it from the Web tab.

Wait for worker startup, then open https://hestia12.pythonanywhere.com/. A brief backend startup response can occur immediately after reload; persistent failures require checking the Web error/server logs with sensitive data redacted.

## 6. Verify the release

- Home/login/signup and their CSS/scripts load.
- Existing accounts, households and invitations remain available.
- Tasks, Groceries, Household, Expenses and thermostat use the same selected household.
- Household settings/ownership/member actions retain owner checks.
- Captured automated tests cover mail/provider behavior; a real SMTP smoke test requires an authorized inbox. Gmail authentication alone does not prove inbox delivery.
- Never display `.env`, cookies, app passwords or token-bearing invitation URLs in shared logs/screenshots.

Optional Web Push needs its own private `WEBPUSH_*` configuration and scheduling. Do not run reminder delivery commands or schedule messages without authorization. Weather/model/provider access and real notification delivery are separate checks.

## Later routine updates

Repeat the backup, fetch, fast-forward, dependency/migration/static checks, reload and smoke verification. Record the deployed commit and backup path each time.

## Rollback

Use the saved release SHA, WSGI/settings and product database backup as one compatible release. Stop writes before restoring. Restoring a database backup discards writes made after that snapshot, so assess and preserve new records first. Extra columns can make an old application's inserts incompatible even when reads appear to work. Do not blindly switch old code over an upgraded schema or overwrite live data.

The original assignment checkout/database is not the product rollback target.

## Local checkout

The local product code is `/Users/darshan/Documents/Projects/12_HestiaaAI-household-demo`. Fetch/fast-forward the same accepted branch while preserving uncommitted changes. The local preview's settings and database live under `/Users/darshan/.local/share/hestia/phase3`.

Back up the local product SQLite database before new migrations, then restart with:

```sh
/Users/darshan/.local/share/hestia/phase3/run-local.sh
```

Open http://127.0.0.1:8012/. That script applies migrations to its separate local product database. Keep its SMTP backend configuration and the code folder's ignored `.env`; never migrate the original grading checkout's database.
