# Auth Flow

Use this browser flow only when the user explicitly authorizes Firecrawl account sign-in and credential setup for the named project. A missing key alone does not authorize login, account creation, or consent submission. Let the human perform those browser steps; never treat agent continuation as consent. Do not expose API keys or the code verifier in chat/logs, or reuse another account's session.

## Step 1: Generate auth parameters

```bash
SESSION_ID=$(openssl rand -hex 32)
CODE_VERIFIER=$(openssl rand -base64 32 | tr '+/' '-_' | tr -d '=\n' | head -c 43)
CODE_CHALLENGE=$(printf '%s' "$CODE_VERIFIER" | openssl dgst -sha256 -binary | openssl base64 -A | tr '+/' '-_' | tr -d '=')
```

## Step 2: Ask the user to open this URL

```text
https://www.firecrawl.dev/cli-auth?code_challenge=$CODE_CHALLENGE&source=coding-agent#session_id=$SESSION_ID
```

The user completes the browser authorization flow. If successful, the API key becomes available through the polling endpoint.

## Step 3: Poll for completion

```http
POST https://www.firecrawl.dev/api/auth/cli/status
Content-Type: application/json

{"session_id":"$SESSION_ID","code_verifier":"$CODE_VERIFIER"}
```

Responses:

- `{"status":"pending"}` - continue polling within the flow's documented interval and expiry; honor user cancellation and terminal errors, and stop after expiry instead of silently starting a new login session
- `{"status":"complete","apiKey":"fc-...","teamName":"..."}` - treat the key as a secret and keep it out of chat, logs, and status output (including the code verifier)

## Step 4: Save the key

Use the project's approved secret destination from [project setup](project-setup.md). Have the user enter the value securely; do not echo it into shell history or append duplicate keys blindly. Confirm the project/environment, preserve unrelated configuration, and verify `.env` is ignored if that is the chosen destination. Account authorization does not grant permission to publish, upload other files, or copy credentials to other environments.
