@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo ==========================================
echo   OneClick-AI-Cover - Automatic Setup
echo ==========================================
echo This setup downloads a managed Python runtime and AI dependencies.
echo You do NOT need to install Python manually.
echo A stable internet connection and several GB of free disk space are required.
echo.
if not exist ".runtime" mkdir ".runtime"
if not exist ".cache" mkdir ".cache"
if not exist "vendor" mkdir "vendor"
if not exist "models\voices" mkdir "models\voices"
if not exist "outputs" mkdir "outputs"
if not exist "logs" mkdir "logs"
set "UV_EXE=%CD%\.runtime\uv.exe"
set "UV_CACHE_DIR=%CD%\.cache\uv"
set "UV_PYTHON_INSTALL_DIR=%CD%\.runtime\python"
set "RVC_COMMIT=81eed5e8f68b6bed1789f682fe78cdd324495afc"
set "UV_VERSION=0.13.7"
set "UV_SHA256=0cdc5b38fe5a8168ed6a25814f5ba43c21d313dd3187314fccb37b7cec46e021"
set "RVC_DIR=%CD%\vendor\rvc"
set "SETUP_STAGE=Preparing folders"
if not exist "%UV_EXE%" (
  set "SETUP_STAGE=Downloading the uv runtime manager"
  echo [1/7] Downloading uv runtime manager...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/astral-sh/uv/releases/download/%UV_VERSION%/uv-x86_64-pc-windows-msvc.zip' -OutFile '%CD%\.runtime\uv.zip'; $actual=(Get-FileHash '%CD%\.runtime\uv.zip' -Algorithm SHA256).Hash.ToLower(); if ($actual -ne '%UV_SHA256%') { throw 'uv archive SHA-256 mismatch' }; Expand-Archive -Force '%CD%\.runtime\uv.zip' '%CD%\.runtime\uv-unpack'; Copy-Item '%CD%\.runtime\uv-unpack\uv.exe' '%UV_EXE%' -Force"
  if errorlevel 1 goto failed
)
set "SETUP_STAGE=Installing managed Python 3.10 and 3.12"
echo [2/7] Installing managed Python 3.10 for the main app and Python 3.12 for RVC...
"%UV_EXE%" python install 3.10
if errorlevel 1 goto failed
"%UV_EXE%" python install 3.12
if errorlevel 1 goto failed
set "SETUP_STAGE=Creating the main app environment and installing dependencies"
echo [3/7] Creating the app environment...
if not exist ".venv\Scripts\python.exe" "%UV_EXE%" venv --python 3.10 .venv
if errorlevel 1 goto failed
set "SETUP_STAGE=Installing pinned CPU PyTorch for Demucs"
echo Installing CPU PyTorch 2.8.0 and torchaudio 2.8.0 from the official PyTorch wheel index...
"%UV_EXE%" pip install --python ".venv\Scripts\python.exe" --index-url https://download.pytorch.org/whl/cpu torch==2.8.0 torchaudio==2.8.0
if errorlevel 1 goto failed
"%UV_EXE%" pip install --python ".venv\Scripts\python.exe" --index-url https://pypi.org/simple -e .
if errorlevel 1 goto failed
if not exist "%RVC_DIR%\webui.py" (
  set "SETUP_STAGE=Downloading the pinned RVC backend"
  echo [4/7] Downloading pinned RVC inference backend...
  if exist "%RVC_DIR%" rmdir /s /q "%RVC_DIR%"
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI/archive/%RVC_COMMIT%.zip' -OutFile '%CD%\.runtime\rvc.zip'; Expand-Archive -Force '%CD%\.runtime\rvc.zip' '%CD%\.runtime\rvc-unpack'; $src=Get-ChildItem '%CD%\.runtime\rvc-unpack' -Directory | Select-Object -First 1; Move-Item $src.FullName '%RVC_DIR%'"
  if errorlevel 1 goto failed
)
if not exist "%RVC_DIR%\webui.py" (
  echo ERROR: RVC training UI entry point webui.py was not found.
  echo The pinned backend may have changed or downloaded incorrectly.
  goto failed
)
if not exist "%RVC_DIR%\infer\cli.py" (
  echo ERROR: RVC inference CLI infer\cli.py was not found.
  echo The pinned backend cannot run singing-cover conversion.
  goto failed
)
set "SETUP_STAGE=Installing RVC Python 3.12 dependencies"
echo [5/7] Creating the separate RVC Python 3.12 environment...
if not exist "%RVC_DIR%\.venv\Scripts\python.exe" (
  pushd "%RVC_DIR%"
  "%UV_EXE%" venv --python 3.12 .venv
  if errorlevel 1 (
    popd
    goto failed
  )
  popd
)
if not exist "%RVC_DIR%\.runtime-ready-py312" (
  if not exist "%RVC_DIR%\requirments_cpu_py312.txt" (
    echo ERROR: RVC CPU requirements file was not found in the downloaded backend.
    goto failed
  )
  rem Remove upstream mirror directives and use official PyPI plus the official CPU wheel index.
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $source=Get-Content '%RVC_DIR%\requirments_cpu_py312.txt'; $body=$source | Where-Object { $_ -notmatch '^\s*--(index-url|extra-index-url)\s+' }; $patched=@('--index-url https://pypi.org/simple','--extra-index-url https://download.pytorch.org/whl/cpu') + $body; [IO.File]::WriteAllLines('%RVC_DIR%\requirments_cpu_py312.local.txt', $patched, [Text.UTF8Encoding]::new($false))"
  if errorlevel 1 goto failed
  "%UV_EXE%" pip install --index-strategy unsafe-best-match --python "%RVC_DIR%\.venv\Scripts\python.exe" -r "%RVC_DIR%\requirments_cpu_py312.local.txt"
  if errorlevel 1 goto failed
  echo ready>"%RVC_DIR%\.runtime-ready-py312"
)
set "SETUP_STAGE=Downloading and verifying required HuBERT and RMVPE inference assets"
echo [6/7] Downloading pinned HuBERT and RMVPE assets from the public Hugging Face repository...
".venv\Scripts\python.exe" scripts\download_rvc_assets.py --rvc-root "%RVC_DIR%"
if errorlevel 1 goto failed
set "SETUP_STAGE=Checking app dependencies"
echo [7/7] Checking app imports...
".venv\Scripts\python.exe" -c "import gradio, demucs, soundfile; print('UI and separation dependencies are available.')"
if errorlevel 1 goto failed
echo.
echo Setup completed. Double-click run.bat to launch OneClick-AI-Cover.
pause
exit /b 0
:failed
echo.
echo SETUP FAILED during: %SETUP_STAGE%
echo Keep this window open and save the last error lines above.
echo Check internet access, free disk space, and security software download restrictions.
echo If the error mentions SSL/TLS, check Windows date/time and retry on an unrestricted network.
echo This installer requires HTTPS with TLS 1.2 support.
echo If dependency resolution fails, check configured Python package mirrors and retry.
echo Troubleshooting guide: https://github.com/ViviBeri/OneClick-AI-Cover/blob/main/docs/troubleshooting.md
echo Fix the reported issue, then run install.bat again.
pause
exit /b 1
