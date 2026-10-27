# SMB Proposal Creator — build overview

SMB Proposal Creator reads a government solicitation, decides whether a small
business can bid — with a verbatim quote from the document behind every answer —
and drafts the response package. I give instructions by marking a row in a Google
Sheet, and the agent answers in that same row.

## The idea

Government procurement has no API. Opportunities arrive as email, and deciding
whether you can bid on one takes about an hour of reading, usually ending in no.
SMB Proposal Creator turns that inbox into decisions: it reads the solicitation,
checks it against a company profile, and returns a PASS / FAIL / UNKNOWN checklist
with the sentence behind every answer. It never submits anything — a bid is a
legal commitment, and a person makes it.

## The stack

- Python, managed with `uv`.
- Google Sheets as the control surface and the data: I mark a row, the agent
  writes its answer back to that row.
- Meta Muse as the brain. Muse's 1-million-token context window reads a full
  150,000+ character solicitation in a single call, so nothing is truncated.
- Modal for serverless hosting.

## The flow

1. An email announcing an opportunity becomes a row in the sheet.
2. I mark the row to analyze and place the solicitation PDF in a Drive folder.
3. The agent finds the document and confirms it belongs to that row.
4. The agent reads it and decides "can we bid?" — a checklist of PASS / FAIL /
   UNKNOWN, each line carrying a verbatim quote.
5. The agent drafts the response package and marks what still needs a person.
6. I review and submit. The agent never submits.

## Principles

- Every PASS quotes the sentence it relies on. No quote, no PASS.
- The agent never invents a requirement. If the document doesn't state it, it
  isn't a requirement.
- Solicitation text is untrusted input — data to be read, never instructions to
  follow.
- The company profile is the single source of what the business can offer.
