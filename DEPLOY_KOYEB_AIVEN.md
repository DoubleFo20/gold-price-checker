# Deploy Portfolio: Koyeb + Aiven

This guide keeps the existing Render and Railway services untouched until the
new deployment has passed acceptance testing.

## 1. Prepare Aiven MySQL

1. Create an Aiven for MySQL Free service.
2. Create or select the target database and record its host, port, database,
   username, and password in a password manager.
3. Import `api/sql/goldapidb.sql` into the selected database. The schema is
   provider-neutral and contains no seeded user.
4. Create the portfolio demo account through the application's Register page.

### Optional safe Railway migration

Do not commit database dumps. Export them to a temporary directory outside the
repository and delete them after the migration has been verified.

If Railway is still reachable:

1. Export the current schema without data.
2. Export data from `price_cache` only.
3. Review both exports for email addresses, tokens, IP addresses, LINE user IDs,
   push subscriptions, and passwords before importing them into Aiven.
4. Import the schema first and `price_cache` data second.

Do not migrate rows from `users`, `sessions`, `price_alerts`,
`saved_forecasts`, `calculation_history`, `notifications`, `email_logs`,
`email_verifications`, `password_resets`, `rate_limits`, `activity_logs`,
`auth_logs`, or `api_request_logs` into the public portfolio database.

## 2. Create the Koyeb service

1. Create a Web Service from the GitHub repository and select branch `main`.
2. Select Buildpack and the Free Instance.
3. Enable automatic deployment from `main`.
4. The buildpack reads `.python-version`; the service command comes from
   `Procfile` and binds Gunicorn to Koyeb's `$PORT`.
5. Configure `/health` as the HTTP health check path.

Set the following values in Koyeb Secrets/Environment Variables. Never paste
real values into this file or commit a local `.env` file.

```text
APP_ENV=production
FLASK_ENV=production
APP_DEBUG=false
COOKIE_SECURE=true
ENABLE_BACKGROUND_CHECKER=false
SECRET_KEY=<random-secret>
JWT_SECRET=<different-random-secret>
JOB_TOKEN=<different-random-secret>
DB_HOST=<aiven-host>
DB_PORT=<aiven-port>
DB_NAME=<aiven-database>
DB_USER=<aiven-user>
DB_PASSWORD=<aiven-password>
LINE_CHANNEL_ACCESS_TOKEN=<line-token>
LINE_CHANNEL_SECRET=<line-secret>
LINE_BOT_ID=@<line-id>
LINE_ADD_FRIEND_URL=https://line.me/R/ti/p/@<line-id>
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=<gmail-address>
SMTP_PASS=<gmail-app-password>
SMTP_FROM_EMAIL=<gmail-address>
SMTP_FROM_NAME=Gold Price Today
VAPID_PUBLIC_KEY=<vapid-public-key>
VAPID_PRIVATE_KEY=<vapid-private-key>
VAPID_SUBJECT=mailto:<contact-email>
FRONTEND_ORIGINS=https://<app-name>.koyeb.app
```

API keys such as `NEWSAPI_KEY` and `ALPHA_VANTAGE_KEY` are optional for the
LINE and notification acceptance tests.

## 3. Configure LINE and scheduled jobs

1. Create a new LINE Messaging API channel and issue its channel access token.
2. Set the webhook URL to `https://<app-name>.koyeb.app/webhook`.
3. Click Verify, enable Use webhook, and disable LINE's automatic reply to
   avoid duplicate responses.
4. In cron-job.org, create a job that runs every five minutes:
   - Method: `POST`
   - URL: `https://<app-name>.koyeb.app/api/jobs/run`
   - Header: `Authorization: Bearer <JOB_TOKEN>`
5. Run the cron job manually once and confirm a successful JSON response.

## 4. Acceptance checklist

- `GET /health` returns HTTP 200.
- `GET /api/debug/db` returns HTTP 404 in production.
- The home page and Thai/world gold price APIs load successfully.
- Register, login, logout, and account linking work against Aiven.
- LINE accepts `ช่วยเหลือ`, `ราคา`, `สถานะ`, `LINK-xxxxxx`, and `ยกเลิก`.
- A triggered alert creates an in-app notification and independently attempts
  LINE, Web Push, and Email delivery.
- Koyeb and cron-job.org logs do not contain tokens, passwords, or connection
  strings.
- Keep Render and Railway available until all checks pass.
