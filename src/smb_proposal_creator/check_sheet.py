"""Read-only check that we can open and read the Google Sheet.

Usage:
    uv run python -m smb_proposal_creator.check_sheet

Reads SPREADSHEET_ID, GOOGLE_APPLICATION_CREDENTIALS, and WORKSHEET_NAME
from the environment (see .env). Prints the tab names, then the header row
and first 5 data rows of the chosen worksheet. Writes nothing to the sheet.
"""

import os
import sys
from pathlib import Path

import gspread
from dotenv import load_dotenv
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound


def main() -> None:
    """Open the spreadsheet and print its tabs plus a few rows."""
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
        tabs = [ws.title for ws in spreadsheet.worksheets()]
    except APIError as exc:
        print(
            "Could not list the worksheets. The sheet may not be shared "
            f"with the service-account email. Details: {exc}"
        )
        sys.exit(1)

    print("Worksheets:")
    for title in tabs:
        print(f"  - {title}")

    try:
        if worksheet_name:
            worksheet = spreadsheet.worksheet(worksheet_name)
        else:
            worksheet = spreadsheet.sheet1
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

    print(f'First rows of "{worksheet.title}":')
    if not rows:
        print("  (the worksheet is empty)")
        return
    for row in rows[:6]:
        print("  " + " | ".join(str(cell) for cell in row))


if __name__ == "__main__":
    main()
