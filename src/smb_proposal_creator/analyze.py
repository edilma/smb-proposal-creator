"""Core eligibility analysis: one Muse call per opportunity.

Usage:
    uv run python -m smb_proposal_creator.analyze
"""

import json
import os
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from smb_proposal_creator.prompts import SYSTEM_PROMPT

META_BASE_URL = "https://api.meta.ai/v1"


def _strip_fences(text: str) -> str:
    """Remove wrapping ``` fences so fence-wrapped JSON still parses."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return stripped


def analyze_opportunity(
    company_profile_text: str, solicitation_text: str
) -> dict:
    """Assess whether the company can bid; return the verdict dict."""
    load_dotenv()

    api_key = os.environ.get("MODEL_API_KEY", "").strip()
    model = os.environ.get("MUSE_MODEL", "").strip()

    missing = [
        name
        for name, value in (
            ("MODEL_API_KEY", api_key),
            ("MUSE_MODEL", model),
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

    user_message = (
        f"TODAY'S DATE: {date.today().isoformat()}\n"
        "\n"
        "COMPANY PROFILE:\n"
        f"{company_profile_text}\n"
        "\n"
        "SOLICITATION TEXT:\n"
        f"{solicitation_text}"
    )

    client = OpenAI(base_url=META_BASE_URL, api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        max_tokens=4000,
        temperature=0,
        reasoning_effort="minimal",
        response_format={"type": "json_object"},
    )

    reply = response.choices[0].message.content or ""
    try:
        return json.loads(_strip_fences(reply))
    except json.JSONDecodeError:
        print("Could not parse the model's reply as JSON. Raw reply:")
        print(reply)
        sys.exit(1)


def main() -> None:
    """Analyze the sample files and print the verdict readably."""
    sys.stdout.reconfigure(encoding="utf-8")
    profile = Path("samples/sample_company_profile.md").read_text(encoding="utf-8")
    solicitation = Path("samples/sample_solicitation.txt").read_text(encoding="utf-8")
    result = analyze_opportunity(profile, solicitation)

    print(f"Verdict: {result.get('verdict', '')}")
    print(f"Title: {result.get('title', '')}")
    print(f"Solicitation type: {result.get('solicitation_type', '')}")
    print(f"Due date: {result.get('due_date', '')}")
    print(f"Summary: {result.get('summary', '')}")
    print(f"Blockers: {result.get('blockers', '')}")
    print("Checks:")
    for check in result.get("checks", []):
        print(f"  - {check.get('requirement', '')}: {check.get('result', '')}")
        print(f"    Evidence: {check.get('evidence', '')}")
    print("Missing information:")
    for item in result.get("missing_information", []):
        print(f"  - {item}")


if __name__ == "__main__":
    main()
