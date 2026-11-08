# Verification result

> Copy this file to a new report (for example, `verification-results/2026-10-29-windows11-issue1.md`). Do not overwrite the template. Do not attach private audio, voice models, credentials, or generated media.

## Run metadata

- Tester:
- Date (UTC):
- Issue: #1 / #2 / #3 / other
- Windows edition/version/build:
- Architecture: x64 / ARM64 / other
- CPU:
- RAM:
- GPU / driver:
- Free disk space before test:
- Network: home / corporate proxy / restricted / offline / other
- Download source URL:
- Download filename and size:
- SHA-256:
- Official published SHA-256 available? YES / NO
- Official checksum comparison: PASS / FAIL / N/A
- Authenticode / SignTool result: PASS / FAIL / NOT AVAILABLE / N/A

## Results checklist

| Check | Result (PASS / FAIL / BLOCKED / NOT TESTED) | Evidence / notes |
|---|---|---|
| Fresh environment; no preinstalled Python | NOT TESTED | |
| Standard non-admin install | NOT TESTED | |
| SmartScreen behavior recorded | NOT TESTED | |
| Install path with spaces | NOT TESTED | |
| Non-ASCII install path | NOT TESTED | |
| Missing VC++ runtime behavior | NOT TESTED | |
| ARM64 compatibility (if relevant) | NOT TESTED | |
| App launches locally; no public tunnel | NOT TESTED | |
| Relaunch after reboot | NOT TESTED | |
| Managed FFmpeg MP3 → WAV | NOT TESTED | |
| Managed FFmpeg WAV → MP3 | NOT TESTED | |
| FFmpeg no-network/proxy failure | NOT TESTED | |
| FFmpeg low-disk failure | NOT TESTED | |
| FFmpeg corrupted/partial download | NOT TESTED | |
| Demucs separation | NOT TESTED | |
| RVC inference with authorized model | NOT TESTED | |
| Mixing and WAV export | NOT TESTED | |
| MP3 export and output probe | NOT TESTED | |
| App cleanup / orphan process check | NOT TESTED | |

## End-to-end details

- App version / commit:
- Python runtime version:
- RVC backend revision:
- Model compatibility/version (no model file attached):
- Input fixture description (no copyrighted/private file attached):
- Install duration:
- First launch duration:
- Per-stage timings:
- Sanitized log / screenshot / ffprobe artifact links:

## Summary

- Overall result: BLOCKED / FAIL / PASS
- First reproducible failure:
- Known issues / limitations observed:
- Follow-up issue(s):
- Tester statement: I have only marked checks PASS where the listed acceptance criteria were met.

