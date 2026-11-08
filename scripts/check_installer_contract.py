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
workflow = read(".github/workflows/windows-checks.yml")

# The main application and the pinned upstream RVC backend deliberately use
# separate Python versions because their dependency constraints differ.
require('python install 3.11' in installer, "installer provisions Python 3.11 for the app")
require('python install 3.12' in installer, "installer provisions Python 3.12 for RVC")
require('RVC_COMMIT=81eed5e8f68b6bed1789f682fe78cdd324495afc' in installer,
        "installer pins the reviewed RVC backend revision")
require('requirments_cpu_py312.txt' in installer,
        "installer checks for the pinned backend CPU requirements file")
require('webui.py' in installer, "installer verifies the RVC UI entry point")
require('infer\\cli.py' in installer, "installer verifies the RVC inference CLI entry point")
require("$ErrorActionPreference='Stop'" in installer, "installer makes PowerShell download errors fatal")
require(installer.count("$ErrorActionPreference='Stop'") >= 2,
        "both runtime-manager and RVC downloads stop on PowerShell errors")
require('if errorlevel 1 goto failed' in installer.lower(),
        "installer has explicit failure handling after setup commands")
require(':failed' in installer.lower(), "installer has a failure exit path")
require('UV_VERSION=0.13.7' in installer, "installer pins the uv runtime-manager version")
require('UV_SHA256=0cdc5b38fe5a8168ed6a25814f5ba43c21d313dd3187314fccb37b7cec46e021' in installer,
        "installer verifies the pinned uv archive SHA-256")
require('download.pytorch.org/whl/cpu' in installer,
        "installer uses the official PyTorch CPU wheel index")
require('requirments_cpu_py312.local.txt' in installer,
        "RVC dependencies are installed from a patched requirements copy")
require('pypi.org/simple' in installer,
        "RVC dependencies use official PyPI rather than upstream mirrors")
require('scripts\\download_rvc_assets.py' in installer,
        "installer downloads required HuBERT and RMVPE assets")
require('torch==2.13.0' in project and 'torchaudio==2.11.1' in project,
        "main app pins matching PyTorch and torchaudio versions")
require("torch.version.cuda is None" in installer,
        "installer verifies the main app uses CPU-only PyTorch")
require("Download and verify pinned RVC inference assets" in workflow,
        "Windows CI downloads the pinned HuBERT and RMVPE assets")
require("scripts/download_rvc_assets.py" in workflow,
        "Windows CI exercises the RVC asset downloader")

require((ROOT / "scripts" / "download_rvc_assets.py").is_file(),
        "RVC asset downloader exists")
require('SETUP_STAGE=' in installer, "installer tracks the current setup stage for diagnostics")
require('SETUP FAILED during:' in installer, "installer reports which setup stage failed")
require('docs/troubleshooting.md' in installer, "installer links to troubleshooting guidance on failure")
require(re.search(r'requires-python\s*=\s*">=3\.11,<3\.13"', project) is not None,
        "project Python range matches the supported Python 3.11–3.12 app environment")
require('.venv\\Scripts\\python.exe' in launcher and 'app.py' in launcher,
        "launcher checks the managed app interpreter and starts app.py")
require('exit /b 1' in launcher.lower(),
        "launcher returns a non-zero code when setup is missing")

print("Installer contract checks passed. This is static validation only, not an installation test.")
