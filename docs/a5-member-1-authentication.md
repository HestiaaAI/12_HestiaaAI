# A5 Member 1: Django authentication

A5 adds username/password authentication to the existing Hestia project. This
supersedes A4's public-page behavior. Work is on `shivani/a5-django-auth`.

## Implemented

- Custom `/accounts/signup/` and `/accounts/login/` pages reuse django-allauth.
  Signup requires username, email, and matching validated passwords. Login accepts
  username or email. Email verification is not required in development/production.
- Successful signup/login opens the task board, or a safe local login `next` URL.
  Passwords are hashed by Django; signup cannot grant staff or superuser privileges.
- Sign out uses a CSRF-protected POST. GET cannot end a session.
- Anonymous visitors see Home, Sign in, and Create account; private navigation and
  home cards appear after login.
- `households/access.py` gates the workflows, task_forms, task_search, reports,
  analytics, and vega namespaces, plus product lookup. Private HTML redirects to
  login. APIs in the api namespace return JSON HTTP 401 before executing the view.
- The sole public API exception is `api:chart-priorities`:
  `/api/charts/task-priorities/`. It returns database-backed aggregate counts,
  not task records. The allowlist lives in `PUBLIC_API_VIEW_NAMES`.

This is an authentication gate, not new household ownership isolation. Signed-in
users retain the assignment's shared household/task behavior. No model migration,
database edits, Google configuration, or dependency changes are included.

## Local verification (October 11, 2026)

```bash
venv/bin/python manage.py test
venv/bin/python manage.py makemigrations --check --dry-run
venv/bin/python manage.py runserver 8025
```

105 tests passed. No model changes detected. Coverage includes username signup
and login, email login, invalid/duplicate signup, safe redirects, CSRF, POST
logout, hidden navigation, anonymous page/API denial, the public API exception,
and existing reports, forms, search, charts and exports after authentication.
Optional legacy mandatory-verification tests explicitly enable that mode.
Access-policy tests also run with DEBUG=False; this is not deployment proof.
Browser checks confirmed the signup form and anonymous reports-to-login redirect.

## Team handoff

**Member 2:** Add Google integration to the existing custom login/signup templates
and account routes; retain username/password login, the access middleware, and
the public API exception. Deploy and verify with the production settings module.
The legacy `shared` settings still have their separate SMTP signup gate; the
A5 development/production flow does not need SMTP.

**Member 3:** Use the deployed `/api/charts/task-priorities/` URL for the public
Vega-Lite demonstration. If the team selects a different public endpoint, update
the single allowlist entry and access tests together. The daily-creation API is
now private, so its downloaded spec cannot fetch anonymously in an external
editor. Both embedded A4 charts are intended for signed-in site users.

**Member 4:** Record production signup, login, private navigation, logout, a
protected API's anonymous 401, and the public API's anonymous JSON response.
Use the same public endpoint for the alternative demonstrations.

## Production checklist (pending deployment)

1. Open an incognito browser at the production home page; private links are hidden.
2. Visit the task board/reports directly; confirm a login redirect.
3. Create a disposable account, then sign out and sign in with username/password.
4. Confirm task board, reports/downloads, search, lookup and both charts work.
5. Sign out; confirm private access is blocked again.
6. Confirm the public priority API returns JSON without login, and all other APIs
   return 401 without login.
7. Member 2 verifies Google OAuth locally and on the production domain.

Do not commit real credentials or account-bearing local database changes.
The tracked A4 demonstration database is unchanged by this implementation.


## Integration update — October 12, 2026

Integrated origin/main at 071914d, including Member 2 Google OAuth and Member 3
API access control and chart deliverables. Google buttons/configuration and
social-account tests are preserved. Username signup remains enabled.
Member 3's ApiAccessMiddleware owns API, export and private chart-output access
(including no-store responses). AssignmentAccessMiddleware protects the remaining
private HTML pages. Anonymous exports return JSON 401 rather than redirecting.
The public Vega page and chart1 outputs remain available; chart2 remains private.
The private navigation links are hidden for anonymous visitors.
117 combined tests passed. This supersedes the original implementation notes
about all Vega routes being private and Google code still needing implementation.
Real Google credentials, callback behavior and production deployment require
Member 2's live verification. No credentials were added to this branch.
