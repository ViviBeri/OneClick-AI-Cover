# Verification status and clean-machine test plan

This document defines evidence required before calling a manual verification step **PASS**. A CI success is not a substitute for any manual test below. Use [`verification-results/TEMPLATE.md`](../verification-results/TEMPLATE.md) for each test run and attach sanitized evidence to the relevant issue.

## Current verified scope

The repository has automated unit tests and a Windows GitHub Actions workflow. The Windows workflow checks key dependency imports and attempts to launch the Gradio app as a local HTTP service, then verifies that the page responds with the expected application title.

**This is CI smoke coverage, not a clean-machine installer certification.** GitHub-hosted runners do not reproduce every Windows version, hardware limit, network condition, proxy, or large model download. A passing CI run does not prove that Demucs separation, RVC inference, MP3 export, or voice training succeeds end-to-end. Automated unit coverage now includes matching vocal/instrumental sample rates, resampling a 48 kHz converted vocal to a 44.1 kHz instrumental when FFmpeg is available, rejecting stale RVC output, and mixing a mono converted vocal with stereo accompaniment. These tests verify the relevant utility behavior; they do **not** replace a real RVC + Demucs end-to-end run.

## CI smoke test

The workflow tests Python 3.10 and 3.11 on Windows and runs:

1. Install the project and test dependencies.
2. Compile the application and source/test scripts.
3. Run the unit tests.
4. Import Gradio, Demucs, NumPy, SoundFile, and imageio-ffmpeg.
5. Start `app.py` as a subprocess, request `http://127.0.0.1:7860/`, check HTTP 200 and the app title, then stop the process.
6. Run `python scripts/check_installer_contract.py` to check that the installer and launcher still agree on the managed Python versions, pinned RVC revision, required RVC entry points, and explicit failure paths. This is a static check and does not run the installer.
7. Check that the Windows setup files and this guide exist.

Review the [Windows Checks workflow](../.github/workflows/windows-checks.yml) and [GitHub Actions runs](https://github.com/ViviBeri/OneClick-AI-Cover/actions).

## Manual clean-machine test plan

### Section 1 — Test environment and prerequisites

Use a fresh Windows x64 virtual machine or physical machine with no Python installed. A fresh VM counts; testers do not need spare physical hardware. **Target matrix:** Windows 11 24H2 x64 is the primary baseline; Windows 11 23H2 x64 and Windows 10 22H2 x64 are additional legacy-compatibility targets where a tester has access. Record exact edition/version/build because support status differs by edition and servicing channel. ARM64 and non-admin installation are best-effort compatibility checks: record results if available, but their absence alone does not block the baseline verification. Record CPU, RAM, free disk space, GPU/driver if applicable, and network type/restrictions.

**Windows Sandbox option:** On supported Windows 10/11 Pro, Enterprise, or Education editions, enable **Windows Sandbox** in “Turn Windows features on or off,” restart if requested, and launch Windows Sandbox from Start. Copy the project ZIP into the sandbox and run the checks there. Sandbox changes are discarded when it closes. **Before shutdown, copy the report, logs, screenshots, output metadata, and any permitted test artifacts to a host-shared folder (for example, a mapped folder accessible through `\\tsclient` in a Remote Desktop session) or another approved host location.** Verify the files are present on the host before closing Sandbox. Availability depends on Windows edition, virtualization support, and device policy.

**Hyper-V / VM option:** Use an isolated fresh Windows VM if Sandbox is unavailable. A new VM snapshot with no Python installed is acceptable. Do not use a work device or VM in a way that violates organization policy.

**Pass criteria:** The report records the environment fields above, and the tester confirms Python was not installed before the test. Otherwise mark BLOCKED, not PASS.

### Section 2 — Download and integrity check

Download the exact ZIP or installer being tested and record its source URL, filename, file size, and SHA-256. In PowerShell, run:

```powershell
Get-FileHash .\OneClick-AI-Cover.zip -Algorithm SHA256
```

Replace the path with the actual downloaded filename. If a versioned release later publishes an official checksum, compare the calculated hash with that release value and mark the comparison PASS only if they match. Until an official checksum is published, the calculated value is evidence identifying the tested file, **not proof of publisher authenticity**.

For a signed installer, verify the signature from PowerShell with `Get-AuthenticodeSignature .\installer.exe` and, where Windows SDK SignTool is available, run:

```powershell
signtool verify /pa /v .\installer.exe
```

**Pass criteria:** Download source and SHA-256 are recorded; any published checksum matches exactly. Record signature status as **SIGNED AND VALID**, **UNSIGNED — EXPECTED**, **INVALID SIGNATURE**, or **NOT CHECKED**. Unsigned is expected for the current project unless a signed release is explicitly published; it is not itself a failure. A published signature that fails verification is a failure. If no official checksum exists, record that no official checksum is available rather than implying a comparison passed.

### Section 3 — Install and first launch

1. Extract the ZIP to a writable path containing spaces, e.g. `C:\Users\Test User\OneClick Cover Test\`. If practical, repeat with non-ASCII characters in the path.
2. Run `install.bat` as a **standard non-administrator user**. Do not elevate unless a failure is being investigated.
3. Save the complete console output and record start/end time, network conditions, warnings, and first failure.
4. Launch with `run.bat`. Confirm the local Gradio interface loads at its local address and does not create public sharing or a tunnel.
5. Confirm the app can start again after a clean reboot.

**Pass criteria:** Installation exits successfully, required managed runtime/dependencies are present, the UI loads locally within 60 seconds after `run.bat` starts (excluding first-time install/download time), and logs contain no unhandled startup error. Record whether the test used an administrator or standard account. Standard non-admin installation is best-effort and should be reported when available; if it is not tested, mark it NOT TESTED rather than blocking the primary baseline. If a different launch-time threshold is required by the environment, record the measured time and reason; do not silently change the threshold.

Record any Microsoft Defender SmartScreen warning exactly. Do not advise contributors to bypass organizational security policy. If a warning blocks execution, mark the result BLOCKED/FAIL as appropriate and attach a screenshot with personal information redacted.

### Section 4 — Architecture and Windows-specific compatibility

Run the install/launch checks on Windows 10 and Windows 11 where available. Record the actual architecture: x64 or ARM64. Do not assume x64 dependencies work on ARM64.

Check the following:
- [ ] Standard (non-admin) account can install and launch.
- [ ] Path with spaces works.
- [ ] Non-ASCII path works, or the limitation is documented.
- [ ] SmartScreen behavior is recorded; no undocumented bypass is required.
- [ ] Missing Visual C++ runtime behavior is recorded. If a dependency requires the Microsoft Visual C++ Redistributable, the error must identify the missing prerequisite or provide a documented, legitimate install route.
- [ ] ARM64 tested, or explicitly marked NOT TESTED/unsupported. Do not report ARM64 as passed based on x64 results.

**Pass criteria:** Every item is PASS, FAIL, or NOT TESTED with a note. A platform not tested must never be described as verified.

### Section 5 — Managed FFmpeg success and failure modes

First confirm system FFmpeg is not on PATH (for example, `where.exe ffmpeg` returns no executable), so the managed fallback is genuinely tested. Use a short test audio file that you own or have permission to use.

| Test | Expected result / pass criterion |
|---|---|
| MP3 import/conversion to WAV | Output exists, is non-empty, opens in an audio probe/player, and duration is plausible. |
| WAV export to MP3 | Output exists, is non-empty, can be reopened/probed, and has plausible duration. |
| No network during first managed FFmpeg download | App reports a clear actionable error; no unhandled traceback or false success. If FFmpeg is already cached, repeat with its cache temporarily unavailable. |
| Corporate proxy / restricted network | Failure is understandable and logged; app does not hang indefinitely or claim FFmpeg is ready when it is not. Record proxy policy without secrets. |
| Insufficient disk space | Safely simulate only in a disposable VM/test volume. Operation fails clearly; no success status for a missing/truncated output. |
| Corrupted or partial FFmpeg download | In a disposable test environment, interrupt a download or corrupt only the test cache. App detects/retries or reports a clear error; it must not execute a truncated binary or silently accept it. |
| Invalid or unsupported input | User sees a readable validation error; the app remains usable. |

Do not deliberately fill a production drive. Record which failures could not be safely reproduced as NOT TESTED.

**Pass criteria:** Both normal conversions work without system FFmpeg, and each tested failure mode degrades gracefully with a readable message, a useful sanitized log, and no false success. A failure mode not exercised is NOT TESTED, not PASS.

### Section 6 — Uninstall verification

This project currently uses a ZIP + batch-file setup rather than a verified MSI/EXE installer. Record the actual cleanup steps; do not claim a formal uninstaller exists unless one is added.

1. Close the app and any related Python/RVC/FFmpeg processes.
2. Remove the extracted project folder and any app-managed runtime/cache folders created by the setup, using only paths confirmed to belong to this test installation.
3. Inspect `%APPDATA%`, `%LOCALAPPDATA%`, and `%TEMP%` for folders/files created by this test. Do not delete unrelated user data.
4. Check Task Manager for orphaned processes.
5. Check installed-app entries and registry only if the test actually created any. Do not edit/delete registry keys speculatively.
6. Reboot and repeat the process check.

**Pass criteria:** No project-created background process remains; all documented app-managed files are removed by the documented cleanup procedure; any retained logs/models/output are explicitly documented as user data. Report unexpected leftovers with exact path redacted as needed. Registry cleanup is N/A if the app did not create registry entries.

### Section 7 — Complete end-to-end conversion

With a compatible RVC model and a short audio file you are authorized to process:

1. Convert/import the input.
2. Run Demucs separation.
3. Run RVC inference.
4. Mix converted vocals with the instrumental.
5. Export WAV.
6. Export MP3.
7. Reopen/probe both outputs and compare their duration with the input.
8. Save sanitized logs and per-stage timings.

**Pass criteria:** Each stage completes without an unhandled error; both output files exist, are non-empty and playable/probeable; output duration is plausible relative to the source; the report records model/backend versions and the result of every stage. A successful UI launch alone is not an end-to-end pass.

### Section 8 — Share evidence and final result

Attach the completed [results template](../verification-results/TEMPLATE.md) to the relevant issue, along with sanitized logs, screenshots, output-file metadata, and ffprobe output where relevant. Do not upload copyrighted audio, voice recordings, voice models, generated audio, credentials, tokens, or unredacted private paths.

Use only **PASS**, **FAIL**, **BLOCKED**, or **NOT TESTED** per check. Overall PASS is allowed only when all criteria required by that issue pass. Otherwise use FAIL/BLOCKED and state the first reproducible failure.

### Verified issue closure record

A `verified` label requires either (a) an external tester's completed results template, or (b) a maintainer's own test on a fresh VM, with the tested ZIP/installer SHA-256 recorded. Maintainer self-tests must be identified as such and must not be described as independent verification. The applicable acceptance criteria and evidence must be attached either way.

When closing a verification issue, add a closing comment with:
- Tester and date (UTC)
- Windows edition/version/build and architecture
- Installer/ZIP filename and SHA-256
- Exact sections/checks completed and PASS/FAIL/BLOCKED/NOT TESTED results
- Artifact links (sanitized logs, screenshots, ffprobe output; no private media/model files)
- Known limitations and any follow-up issue

A `verified` label should be applied only after evidence meets the acceptance criteria. Closing an issue without the record does not establish what was tested.

## Results template

Copy [`verification-results/TEMPLATE.md`](../verification-results/TEMPLATE.md) for each run. Add completed reports to the `verification-results/` folder when appropriate and update the [results index](../verification-results/README.md) with the date, Windows build, tester, scope, outcome, and report link. The template includes a compact checkbox table and fields suitable for later aggregation.

## Known issues / current limitations

- No published signed installer release artifact or official release SHA-256 is available yet.
- Clean-machine installation and formal uninstall behavior are not yet verified.
- Windows ARM64 is not claimed as supported or verified.
- The CI installer-contract check is static; it does not execute `install.bat`.
- Full Demucs → RVC → mixing → export has not yet been recorded as a verified end-to-end run.
- Corporate proxy, offline first-run, corrupted download, and low-disk-space FFmpeg failure modes require manual validation.

## Current status

No physical clean-machine test result has been recorded in this repository yet. The full end-to-end workflow must remain marked pending until a tester records successful results. Do not change the README status banner to “verified” based only on CI.
