from __future__ import annotations

import os
from openai import OpenAI


def get_client() -> OpenAI:
    # Uses OPENAI_API_KEY automatically.
    return OpenAI()


def get_model() -> str:
    return os.getenv("POG_OPENAI_MODEL", "gpt-4o-mini")
