---
name: Verification report
about: Report reproducible Windows installer, FFmpeg, or end-to-end verification results
title: "[Verification] "
labels: "verification"
assignees: ""
---

## Verification plan

Follow [docs/verification.md](https://github.com/ViviBeri/OneClick-AI-Cover/blob/main/docs/verification.md) and attach a completed copy of [verification-results/TEMPLATE.md](https://github.com/ViviBeri/OneClick-AI-Cover/blob/main/verification-results/TEMPLATE.md).

## Scope

- [ ] Clean Windows install / launch (Section 3–4)
- [ ] Managed FFmpeg import/export and failure modes (Section 5)
- [ ] Uninstall / cleanup (Section 6)
- [ ] Complete end-to-end conversion (Section 7)
- [ ] Other (describe below)

## Environment

- Tester:
- Date (UTC):
- Windows edition/version/build and architecture:
- Download filename and SHA-256:
- Issue being verified: #1 / #2 / #3 / other

## Result

- Overall: PASS / FAIL / BLOCKED / NOT TESTED
- Evidence links (sanitized logs, screenshots, output metadata / ffprobe):
- First reproducible failure:
- Notes / known limitations:

Do not upload copyrighted songs, voice recordings, voice models, generated audio, credentials, tokens, or unredacted private paths. CI smoke tests alone are not end-to-end verification.
