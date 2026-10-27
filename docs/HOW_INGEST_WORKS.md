# How the existing ingestion works

The Gmail → Sheets pipeline that feeds SMB Proposal Creator. It has been running since spring 2025 and is **not** being changed for this project.

It lives in a **standalone** Apps Script project called `extractProcurementData`, in Drive — not bound to the spreadsheet. It reaches the sheet by ID.

---

## Entry point

```js
function main() {
  extractProcurementData();  // MFMP
  extractOpenGovEmails();    // OpenGov
}
```

One function per source, run in sequence.

---

## Source 1 — MyFloridaMarketPlace (`extractProcurementData`)

**Gmail search:** `from:MFMP.NoReply@dms.myflorida.com newer_than:30d`
**Writes to:** tab `MFMP_EMAIL_LIST`

**How it parses.** MFMP emails are `Label: value` pairs in the plain-text body, so it builds a regex per field:

```js
const match = body.match(new RegExp(label + ':\\s*(.+)'));
```

Every value goes through `cleanValue()`, which strips leading `*`, `•`, `:` and
whitespace — those come from the email's bullet formatting.

**Columns written:**

| # | Column | Example |
|---|---|---|
| A | Timestamp | when the script ran, not the notice date |
| B | Organization | Department of Children and Families (DCF) |
| C | Advertisement Number | RFI-16679 |
| D | Agency Advertisement Number | DCF RFI 2627 030 |
| E | Advertisement Type | Request for Information |
| F | Title | ELECTRONIC HEALTH RECORD (EHR) SYSTEM |
| G | Commodity Code | 81112200 |
| H | Open Date | Aug 13, 2026 |
| I | Close Date | Oct 7, 2026 |
| J | Agency Contact | Joshua Burns |
| K | Phone | |
| L | Address | |
| M | Email | joshua.burns@myflfamilies.com |
| N | Message ID | Gmail message id — hidden column, used for de-duplication |

**Highlighting.** Rows are painted yellow (`#fff2cc`) when Advertisement Type is
`Request for Information` or `Request for Proposals`.

---

## Source 2 — OpenGov (`extractOpenGovEmails`)

**Gmail search:** `from:procurement-notifications@opengov.com subject:"New Opportunity Issued by" newer_than:30d`
**Writes to:** tab `OpenGov_Emails`

**How it parses.** OpenGov emails are prose, so everything comes from the *subject line*:

```
New Opportunity Issued by Town of Davie: ITB# RS-26-56 Potable Reuse Pilot Laboratory
                          └── location ──┘  └─ code ─┘  └────────── title ──────────┘
```

A regex splits location from title, then a second regex hunts for a solicitation code
inside the title — `ITQ#`/`ITB#`, `RFP#`, `NTSS-`, `Y26-123-ABC`, `MP-26-01`, `GR-26-27`,
`RS-26-56`, and a general `XX-99-A1` shape. If it finds one, the code is pulled out and
removed from the title.

**Columns written:**

| # | Column | Example |
|---|---|---|
| A | Timestamp | when the script ran |
| B | Location | Pinellas County |
| C | Opportunity Code | ITB# GR-26-27 — **often empty** |
| D | Title | Janitorial Services for Solid Waste |
| E | Message ID | hidden, used for de-duplication |

**Highlighting.** Rows are painted pink (`#ffd6e7`) when the title contains the word "software".

---

## Shared behaviour

**De-duplication.** Before processing, the script reads every Message ID already in the sheet and skips any message it recognises. This is why re-running it is safe and why the
30-day search window doesn't create duplicates.

**Labelling and archiving.** Every thread it processes gets the Gmail label `Processed Bids`, and all processed threads are archived together at the end of the run with `GmailApp.moveThreadsToArchive()`.

**Header setup.** On an empty sheet it writes the header row, freezes it, bolds it and adds a filter. The Message ID column is hidden at the end of every run.

---

## What it does not capture

- **The OpenGov body.** Everything comes from the subject line, so the prose summary with the requirement bullets is never stored. Not a problem for Proposal Desk — the agent reads the solicitation document itself, not the announcement email.
- **The opportunity link.** The "View Opportunity" URL isn't extracted.
- **Attachments.** Never touched.

## Quirks worth knowing

- **`Timestamp` is when the script ran**, not when the notice was issued or when the  email arrived. Close Date (MFMP) is the only real deadline captured.
- **`Opportunity Code` is frequently blank** on OpenGov rows, because many subject lines carry no code the regex recognises. Matching a document to an OpenGov row will often have to fall back to the title.
- **The highlighting is a rule, not a judgement.** Yellow means "this is an RFI or RFP." 
  Pink means "the word software appears in the title." Neither means "I could bid on   this" — which is precisely the gap Proposal Desk fills.
- **The spreadsheet ID is hardcoded** in both functions.
- **It writes with `appendRow` inside the loop**, one round-trip per row. Fine at this
  volume; would need batching at ten times the size.

## Rule for this project

> **This code is never run from the SMB Proposal Creator script.**

It reaches the production sheet by hardcoded ID and it archives real email. A copy is
kept in `apps-script/Ingest.gs` for reference only.
