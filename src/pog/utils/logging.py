from __future__ import annotations

import datetime
import sys


def log(message: str) -> None:
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    sys.stdout.write(f"[pog {ts}] {message}\n")
    sys.stdout.flush()
