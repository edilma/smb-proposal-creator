"""Tiny check that we can call the Meta Muse API.

Usage:
    uv run python -m smb_proposal_creator.check_muse

Reads MODEL_API_KEY and MUSE_MODEL from the environment (see .env). Sends one
short chat completion and prints the reply plus the model id the response
reports. Calls Meta only; no other provider.
"""

import os
import sys

from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APIError,
    AuthenticationError,
    NotFoundError,
    OpenAI,
)

META_BASE_URL = "https://api.meta.ai/v1"


def main() -> None:
    """Send one tiny chat completion and print the result."""
    sys.stdout.reconfigure(encoding="utf-8")
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

    client = OpenAI(base_url=META_BASE_URL, api_key=api_key)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with exactly: Muse connection OK"}],
            # 20 tokens is not enough: the model spends ~18 on reasoning and
            # gets cut off before emitting text (finish_reason "length").
            max_tokens=100,
            temperature=0,
            # Verified against the API: without this the model burns the whole
            # token budget on reasoning and returns null content.
            reasoning_effort="minimal",
        )
    except AuthenticationError:
        print(
            "Authentication failed. Check that MODEL_API_KEY in your .env file "
            "is a valid Meta Model API key."
        )
        sys.exit(1)
    except NotFoundError:
        print(
            f'Model "{model}" was not found or is not available. '
            "Check MUSE_MODEL in your .env file."
        )
        sys.exit(1)
    except APIConnectionError as exc:
        print(f"Could not reach the Meta API (network error). Details: {exc}")
        sys.exit(1)
    except APIError as exc:
        print(f"The Meta API returned an error. Details: {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"Unexpected error calling the Meta API. Details: {exc}")
        sys.exit(1)

    reply = response.choices[0].message.content
    print(f"Reply: {reply if reply is not None else '(empty reply)'}")
    print(f"Model: {response.model}")


if __name__ == "__main__":
    main()
