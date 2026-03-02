from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BuildResult:
    success: bool
    returncode: int
    stdout: str
    stderr: str


def run_dotnet_build(sln_path: Path) -> BuildResult:
    """
    Run: dotnet build <sln_path>
    Returns captured stdout/stderr for logging and later repair loops.
    """
    sln_path = sln_path.resolve()

    proc = subprocess.run(
        ["dotnet", "build", str(sln_path)],
        capture_output=True,
        text=True,
        cwd=str(sln_path.parent),
    )

    return BuildResult(
        success=proc.returncode == 0,
        returncode=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
    )
