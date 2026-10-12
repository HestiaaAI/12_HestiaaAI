# A5 Member 2: Google sign-in and PythonAnywhere

Google sign-in uses django-allauth's Google provider. The OAuth client lives in
the Google Cloud project, and the client ID and secret are read from `.env` on
each server. They are not stored in `db.sqlite3`, which this repository tracks.

## Google Cloud client

Create a Web application OAuth client with these exact redirect URIs:

- `http://127.0.0.1:8000/accounts/google/login/callback/`
- `https://hestia12.pythonanywhere.com/accounts/google/login/callback/`

Use the `profile`, `email`, and `openid` identity scopes. If the Google app is
in Testing mode, add the Google accounts used for the class demonstration to
its test-user list. The callback is reached through the sign-in button; opening
it directly is not a login test.

## Local setup

Put `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in the untracked project `.env`.
Use the actual Google values; never copy them into tracked files or a `SocialApp`
admin record. Then run:

```sh
python -m pip install -r requirements.txt
python manage.py migrate --settings=hestia_config.settings.development
python manage.py check --settings=hestia_config.settings.development
python manage.py test --settings=hestia_config.settings.development
python manage.py runserver 127.0.0.1:8000 --settings=hestia_config.settings.development
```

Visit `/accounts/login/` and `/accounts/signup/` for the Google button. Its
POST begins the Google OAuth flow. Password signup remains under Member 1's
email-delivery policy; the Google flow accepts a new Google account only when
Google supplies a verified email address.

## PythonAnywhere rollout

After this branch reaches GitHub `main`, open a Bash console as `hestia12`:

```sh
cd ~/12_HestiaaAI
git pull --ff-only origin main
source ~/.virtualenvs/hestia-a4/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate --settings=hestia_config.settings.production
python manage.py check --settings=hestia_config.settings.production
python manage.py test --settings=hestia_config.settings.production
```

Keep both `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in the server's
untracked `/home/hestia12/12_HestiaaAI/.env`. In the PythonAnywhere Web tab,
reload `hestia12.pythonanywhere.com`. Then confirm:

1. `/accounts/login/` and `/accounts/signup/` show **Continue with Google**.
2. Clicking the button reaches Google's consent screen and returns to the
   production site signed in.
3. A previously unknown Google account with a verified email can sign up.
4. Sign out, then check that private A5 routes and APIs again reject anonymous
   requests. The priority chart API remains public.

If Google reports `redirect_uri_mismatch`, compare its displayed URI character
for character with the production URI above, including `https` and the slash.
If the server creates an `http` callback despite an HTTPS browser request,
check the PythonAnywhere Web app's HTTPS configuration before changing Google
Cloud settings.
