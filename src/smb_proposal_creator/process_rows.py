"""Sheet round-trip: analyze rows marked "Analyze", write verdicts back.

Usage:
    uv run python -m smb_proposal_creator.process_rows
"""

import os
import sys
from datetime import date
from pathlib import Path

import gspread
from dateutil import parser as date_parser
from dotenv import load_dotenv
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound

from smb_proposal_creator.analyze import analyze_opportunity

MAX_ROWS_PER_RUN = 3


def _deadline_passed(close_text: str) -> bool:
    """True if close_text parses as a date strictly before today.

    Anything unparseable returns False, so the row goes to full analysis.
    """
    try:
        return date_parser.parse(close_text, dayfirst=False).date() < date.today()
    except Exception:
        return False


def main() -> None:
    """Process up to 3 rows marked "Analyze" and write back verdicts."""
    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv()

    spreadsheet_id = os.environ.get("SPREADSHEET_ID", "").strip()
    key_file = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    worksheet_name = os.environ.get("WORKSHEET_NAME", "").strip()

    missing = [
        name
        for name, value in (
            ("SPREADSHEET_ID", spreadsheet_id),
            ("GOOGLE_APPLICATION_CREDENTIALS", key_file),
            ("WORKSHEET_NAME", worksheet_name),
        )
        if not value
    ]
    if missing:
        print(
            "Missing required environment variable(s): "
            + ", ".join(missing)
            + ". Check your .env file."
        )
        sys.exit(1)

    if not Path(key_file).exists():
        print(
            f"Service-account key file not found: {key_file}. "
            "Check GOOGLE_APPLICATION_CREDENTIALS in your .env file."
        )
        sys.exit(1)

    try:
        client = gspread.service_account(filename=key_file)
    except Exception as exc:
        print(
            "Authentication failed. Check that the key file is a valid "
            f"service-account JSON key. Details: {exc}"
        )
        sys.exit(1)

    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
    except SpreadsheetNotFound:
        print("Spreadsheet not found. Check SPREADSHEET_ID in your .env file.")
        sys.exit(1)
    except APIError as exc:
        print(
            "Could not open the spreadsheet. The sheet may not be shared "
            f"with the service-account email. Details: {exc}"
        )
        sys.exit(1)

    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
    except WorksheetNotFound:
        print(
            f'Worksheet "{worksheet_name}" not found. '
            "Check WORKSHEET_NAME in your .env file."
        )
        sys.exit(1)
    except APIError as exc:
        print(
            "Could not open the worksheet. The sheet may not be shared "
            f"with the service-account email. Details: {exc}"
        )
        sys.exit(1)

    try:
        rows = worksheet.get_all_values()
    except APIError as exc:
        print(f"Could not read the rows. Details: {exc}")
        sys.exit(1)

    headers = list(rows[0]) if rows else []
    columns = {}
    try:
        for name in ("Status", "Verdict", "Blockers"):
            match = next(
                (i for i, h in enumerate(headers) if h.strip() == name), None
            )
            if match is None:
                empty = next(
                    (i for i, h in enumerate(headers) if not h.strip()),
                    len(headers),
                )
                worksheet.update_cell(1, empty + 1, name)
                if empty == len(headers):
                    headers.append(name)
                else:
                    headers[empty] = name
                match = empty
                print(f'Added column "{name}".')
            columns[name] = match + 1
    except APIError as exc:
        print(f"Could not add a column header. Details: {exc}")
        sys.exit(1)

    status_col = columns["Status"]
    close_match = next(
        (i for i, h in enumerate(headers) if h.strip() == "Close Date"), None
    )
    close_col = close_match + 1 if close_match is not None else None
    candidates = []
    for row_number, cells in enumerate(rows[1:], start=2):
        status = cells[status_col - 1].strip() if status_col - 1 < len(cells) else ""
        if status.lower() == "analyze":
            close_text = ""
            if close_col is not None and close_col - 1 < len(cells):
                close_text = cells[close_col - 1].strip()
            candidates.append((row_number, close_text))

    if not candidates:
        print('No rows marked "Analyze". Nothing to do.')
        return

    profile_path = Path("docs/COMPANY_PROFILE.md")
    sample_path = Path("samples/sample_solicitation.txt")
    for path in (profile_path, sample_path):
        if not path.exists():
            print(f"Required file not found: {path}.")
            sys.exit(1)
    profile_text = profile_path.read_text(encoding="utf-8")
    # TEMPORARY STAND-IN: every row uses the same sample solicitation for now.
    # To be replaced with real per-row document reading (Files API) in a later step.
    solicitation_text = sample_path.read_text(encoding="utf-8")

    processed = []
    for row_number, close_text in candidates[:MAX_ROWS_PER_RUN]:
        if close_text and _deadline_passed(close_text):
            verdict = "CANNOT BID"
            blockers = f"Response deadline ({close_text}) has already passed."
            try:
                worksheet.update_cell(row_number, columns["Verdict"], verdict)
                worksheet.update_cell(row_number, columns["Blockers"], blockers)
                worksheet.update_cell(row_number, status_col, "Done")
            except APIError as exc:
                print(f"Could not write results to row {row_number}. Details: {exc}")
                sys.exit(1)
            processed.append((row_number, verdict, True))
            continue
        try:
            result = analyze_opportunity(profile_text, solicitation_text)
        except Exception as exc:
            print(f"Analysis failed for row {row_number}. Details: {exc}")
            sys.exit(1)
        verdict = result["verdict"]
        blockers = result.get("blockers", "")
        status = "Needs me" if verdict == "NEEDS INFO" else "Done"
        try:
            worksheet.update_cell(row_number, columns["Verdict"], verdict)
            worksheet.update_cell(row_number, columns["Blockers"], blockers)
            worksheet.update_cell(row_number, status_col, status)
        except APIError as exc:
            print(f"Could not write results to row {row_number}. Details: {exc}")
            sys.exit(1)
        processed.append((row_number, verdict, False))

    print(f"Processed {len(processed)} row(s):")
    for row_number, verdict, skipped in processed:
        note = " (skipped: response deadline passed)" if skipped else ""
        print(f"  Row {row_number}: {verdict}{note}")


if __name__ == "__main__":
    main()
