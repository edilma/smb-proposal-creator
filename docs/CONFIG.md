# Configuration

All settings and secrets live in `.env`, which is never committed. `.env.example`
is the template with the keys and blank values. These follow Meta's and Google's
standard variable names.

## Variables

- `MODEL_API_KEY` — the Meta Model API key (a Bearer token). This is Meta's
  standard name.
- `MUSE_MODEL` — the Muse model id the agent calls.
- `SPREADSHEET_ID` — the id of the Google Sheet, taken from its URL (the string
  between `/d/` and `/edit`).
- `WORKSHEET_NAME` — the tab the agent reads from and writes to.
- `GOOGLE_APPLICATION_CREDENTIALS` — path to the service-account JSON key inside
  `secrets/`. This is Google's standard name, and the Google client libraries
  pick it up automatically.

## .env.example

```
MODEL_API_KEY=
MUSE_MODEL=
SPREADSHEET_ID=
WORKSHEET_NAME=
GOOGLE_APPLICATION_CREDENTIALS=secrets/your-service-account.json
```

## Notes

- Never put any of these values in code. Read them from `.env`.
- The `secrets/` folder and `.env` are gitignored and must never be committed.
