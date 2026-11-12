#!/usr/bin/env bash
# Run on PythonAnywhere, not the local/grading checkout. See deployment.md.
set -euo pipefail
umask 077

if [[ ${1:-} == --help ]]; then
    echo 'Usage: bash deploy.sh (on PythonAnywhere; deploys household-member-management)'
    exit 0
fi
[[ $# == 0 ]] || { echo 'Unexpected arguments. Use --help.' >&2; exit 1; }

readonly code=/home/hestia12/hestia-household-invitations
readonly runtime=/home/hestia12/hestia-phase3-runtime
readonly branch=household-member-management
cd "$code"
exec 9>"$runtime/deploy.lock"
flock -n 9 || { echo 'Another deployment is running.' >&2; exit 1; }
source /home/hestia12/.virtualenvs/hestia-a4/bin/activate
export PYTHONPATH="$runtime:$code"
export DJANGO_SETTINGS_MODULE=deployment_settings

[[ $(git branch --show-current) == "$branch" ]] || {
    echo "Expected branch $branch; switch deliberately using deployment.md first." >&2; exit 1;
}
[[ -z $(git status --porcelain --untracked-files=normal) ]] || {
    echo 'Preserve local changes before deploying. Nothing was overwritten.' >&2; exit 1;
}

git fetch origin "refs/heads/$branch:refs/remotes/origin/$branch"
readonly target=$(git rev-parse "refs/remotes/origin/$branch")
git merge-base --is-ancestor HEAD "$target" || {
    echo 'Local history diverges from remote; resolve it before deploying.' >&2; exit 1;
}
if ! git diff --quiet HEAD "$target" -- requirements.txt; then
    echo 'Requirements changed. Review/install the new dependencies, then rerun with the checkout updated per deployment.md.' >&2
    git diff HEAD "$target" -- requirements.txt
    exit 1
fi

# Back up before changing the checkout or schema; never copy secrets to Git.
python - <<'PY'
from datetime import datetime, timezone
from pathlib import Path
import shutil
import sqlite3
import subprocess
import django

django.setup()
from django.conf import settings
runtime = Path('/home/hestia12/hestia-phase3-runtime')
database = runtime / 'product.sqlite3'
assert Path(settings.DATABASES['default']['NAME']).resolve() == database
assert database.is_file(), 'Product database missing'
backup = runtime / 'backups' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
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

git merge --ff-only "$target"
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python - <<'PY'
from pathlib import Path
import django

django.setup()
from django.conf import settings
root = Path(settings.STATIC_ROOT).resolve()
assert root == Path('/home/hestia12/hestia-household-invitations/staticfiles')
root.chmod(0o755)
for item in root.rglob('*'):
    if item.is_symlink():
        raise RuntimeError('Unexpected symlink in public static tree')
    item.chmod(0o755 if item.is_dir() else 0o644)
PY
printf '\nPrepared release: %s\n' "$(git rev-parse --short HEAD)"
echo 'Now reload hestia12.pythonanywhere.com from PythonAnywhere → Web, then smoke-test the site.'
