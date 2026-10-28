# Verification status and clean-machine test plan

## Current verified scope

The repository has automated unit tests and a Windows GitHub Actions workflow. The Windows workflow now also checks key dependency imports and attempts to launch the Gradio app as a local HTTP service, then verifies that the page responds with the expected application title.

**This is CI smoke coverage, not a clean-machine installer certification.** GitHub-hosted runners do not reproduce every Windows 10 version, hardware limit, network condition, or large model download. A passing CI run does not prove that Demucs separation, RVC inference, MP3 export, or voice training succeeds end-to-end.

## CI smoke test

The workflow tests Python 3.10 and 3.11 on Windows and runs:

1. Install the project and test dependencies.
2. Compile the application and source/test scripts.
3. Run the unit tests.
4. Import Gradio, Demucs, NumPy, SoundFile, and imageio-ffmpeg.
5. Start `app.py` as a subprocess, request `http://127.0.0.1:7860/`, check HTTP 200 and the app title, then stop the process.
6. Run `python scripts/check_installer_contract.py` to check that the installer and launcher still agree on the managed Python versions, pinned RVC revision, required RVC entry points, and explicit failure paths. This is a static check and does not run the installer.
7. Check that the Windows setup files and this guide exist.

Review the [Windows Checks workflow](../.github/workflows/windows-checks.yml) and the latest [GitHub Actions runs](https://github.com/ViviBeri/OneClick-AI-Cover/actions).

## Manual clean-machine test plan

Use a fresh Windows 10/11 x64 virtual machine or physical machine with no Python installed. Record the exact Windows build, CPU, RAM, available disk space, and network type.

1. Download a ZIP from the repository's main branch and extract it into a writable folder.
2. Confirm there is no preinstalled Python dependency, then run `install.bat` as a standard user.
3. Save the complete installer output. Note download sizes, duration, disk space, warnings, and the first failure if any.
4. Run `run.bat`; confirm the app opens at its local address and that no public sharing/tunnel is created.
5. Confirm the voice-model list can refresh with no models present and that invalid file selections produce understandable errors.
6. Test **Prepare Voice Recordings** with a short recording you own or have permission to use. Confirm that the output dataset is local and contains mono WAV files.
7. Test MP3-to-WAV conversion and MP3 export using a short, rights-cleared audio fixture. Confirm the managed FFmpeg fallback works on a machine without system FFmpeg.
8. With a compatible RVC model and a short audio file you are authorized to process, run a complete cover: input conversion → Demucs separation → RVC conversion → mixing → WAV export. Then repeat with MP3 export.
9. Save the resulting logs, exact command/output, timings, and whether each stage passed. Do not commit recordings, voice models, generated audio, credentials, or unredacted private paths.
10. Repeat after a clean reboot. Record whether install and launch work from a non-administrator account.

## Results template

Copy this into a test report when a real machine run is completed:

- Date:
- Tester / Windows version and build:
- CPU / RAM / GPU:
- Free disk space before install:
- Internet type / restrictions:
- Install result and duration:
- App launch result:
- Dependency import result:
- Recording preparation result:
- Managed FFmpeg import/export result:
- Demucs separation result:
- RVC conversion result (model version and authorized test asset, no private files attached):
- Mixing and WAV export result:
- MP3 export result:
- Logs / sanitized error excerpts:
- Overall result: PASS / FAIL / BLOCKED

## Current status

No physical clean-machine test result has been recorded in this repository yet. The full end-to-end workflow must remain marked pending until a tester records successful results. Do not change the README status banner to "verified" based only on CI.
