# Recurring bill calendar and reminders

Bills remain plans until a household member records their actual amount. Calendar projections create no expenses. Recording is idempotent per bill/due date. Monthly schedules retain the original day across short months. Existing recorded bills stay in calendar history. Pause/resume and edits require the creator, usual payer or household owner.

In-app reminders are collected at inbox/calendar visits and by the scheduled command. Reminders go only to active participants and the usual payer. Read state belongs to each user. Rescheduled/paused/recorded occurrences are excluded from current reminders.

## Phone/browser push setup

Install requirements (includes pywebpush). Configure in the server's ignored .env:

- WEBPUSH_PUBLIC_KEY: URL-safe base64 uncompressed P-256 public key
- WEBPUSH_PRIVATE_KEY: absolute path to a private PEM key outside tracked source
- WEBPUSH_SUBJECT: mailto contact or HTTPS contact URL for the deployment

Keep the key pair stable. Never commit the private key. Use a real deployment contact in production.

Run `python manage.py send_bill_reminders` every 15 minutes using the hosting service's scheduler. A local preview can run `python manage.py send_bill_reminders --watch`; stop it when no longer needed. Failed sends remain retryable; expired subscriptions are removed. Each reminder/device has a delivery record to suppress normal repeat sends. Generic lock-screen text excludes amounts and household names. Notifications are best effort: browser/OS settings and connectivity can delay delivery. An overlapping scheduler should be avoided.

Deploy on HTTPS for phones. Add Hestia to the iPhone home screen and open the installed app before requesting permission. Each participant enables notifications on each device from the reminder inbox. Supported push endpoints: Chrome/FCM, Firefox/Mozilla, Apple Web Push. Unsupported browsers retain in-app reminders. A localhost link on a laptop cannot be used as a phone deployment.

The service worker only handles notifications; it does not cache protected pages for offline use. Signing out does not send bill details to the lock screen; the reminder destination still requires login. Disable push on shared devices from the inbox.

## Local validation

Tests cover calendar projection, month-end dates, household isolation, repeated recording, reminder deduplication, per-user read permission, invalid push destinations, and edit restrictions. Real phone delivery must be checked after HTTPS deployment, server scheduling and device permission are enabled.
