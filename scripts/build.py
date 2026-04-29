# -claude-fix- Build the desktop executable with Python/PyInstaller.
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    entry = repo_root / "run.py"
    dist = repo_root / "dist"
    build = repo_root / "build"
    dist.mkdir(exist_ok=True)

    if not shutil.which("pyinstaller") and subprocess.run([sys.executable, "-m", "PyInstaller", "--version"], capture_output=True).returncode != 0:
        print("PyInstaller is not installed. Run: python -m pip install pyinstaller")
        return 1

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        "AIWorkspaceAccountManager",
        "--distpath",
        str(dist),
        "--workpath",
        str(build),
        "--specpath",
        str(build),
        str(entry),
    ]
    return subprocess.call(cmd, cwd=str(repo_root))


if __name__ == "__main__":
    raise SystemExit(main())
