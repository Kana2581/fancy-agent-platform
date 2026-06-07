# Webhook Smoke Test

Use environment variables so webhook secrets stay out of Git history.

## Bash / Git Bash

```bash
export WEBHOOK_SMOKE_URL='http://host/api/v1/webhooks/<slug>'
export WEBHOOK_SMOKE_SECRET='<secret>'
export WEBHOOK_SMOKE_BODY='{"content":"hello"}'

BODY="${WEBHOOK_SMOKE_BODY:-{\"content\":\"hello\"}}"
SIG=$(printf %s "$BODY" | openssl dgst -sha256 -hmac "$WEBHOOK_SMOKE_SECRET" | awk '{print $2}')

curl -X POST "$WEBHOOK_SMOKE_URL" \
  -H "X-Signature: sha256=$SIG" \
  -H "Content-Type: application/json" \
  --data-raw "$BODY"
```

## PowerShell

```powershell
$env:WEBHOOK_SMOKE_URL = 'http://host/api/v1/webhooks/<slug>'
$env:WEBHOOK_SMOKE_SECRET = '<secret>'
$env:WEBHOOK_SMOKE_BODY = '{"content":"hello"}'

powershell -ExecutionPolicy Bypass -File scripts\smoke_webhook.ps1
```

The pre-push hook runs this smoke test only when `WEBHOOK_SMOKE_URL` and
`WEBHOOK_SMOKE_SECRET` are set.
