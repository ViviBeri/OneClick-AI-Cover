"""Static checks for the Windows installer contract.

These checks catch accidental drift in setup scripts; they do not execute
PowerShell downloads or certify a clean-machine installation.
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}", file=sys.stderr)
        raise SystemExit(1)
    print(f"PASS: {message}")


def read(relative_path: str) -> str:
    path = ROOT / relative_path
    require(path.is_file(), f"{relative_path} exists")
    return path.read_text(encoding="utf-8")


installer = read("install.bat")
launcher = read("run.bat")
project = read("pyproject.toml")

# The main application and the pinned upstream RVC backend deliberately use
# separate Python versions because their dependency constraints differ.
require('python install 3.10' in installer, "installer provisions Python 3.10 for the app")
require('python install 3.12' in installer, "installer provisions Python 3.12 for RVC")
require('RVC_COMMIT=81eed5e8f68b6bed1789f682fe78cdd324495afc' in installer,
        "installer pins the reviewed RVC backend revision")
require('requirments_cpu_py312.txt' in installer,
        "installer checks for the pinned backend CPU requirements file")
require('webui.py' in installer, "installer verifies the RVC UI entry point")
require('infer\\\\cli.py' in installer, "installer verifies the RVC inference CLI entry point")
require("$ErrorActionPreference='Stop'" in installer, "installer makes PowerShell download errors fatal")
require('if errorlevel 1 goto failed' in installer.lower(),
        "installer has explicit failure handling after setup commands")
require(':failed' in installer.lower(), "installer has a failure exit path")
require(re.search(r'requires-python\s*=\s*">=3\.10,<3\.12"', project) is not None,
        "project Python range matches the main app environment")
require('.venv\\Scripts\\python.exe' in launcher and 'app.py' in launcher,
        "launcher checks the managed app interpreter and starts app.py")
require('exit /b 1' in launcher.lower(),
        "launcher returns a non-zero code when setup is missing")

print("Installer contract checks passed. This is static validation only, not an installation test.")
