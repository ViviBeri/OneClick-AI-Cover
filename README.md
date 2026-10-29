# OneClick-AI-Cover

Free, open-source, Windows-first local AI singing-cover creator. Separate vocals from a song, convert the vocal with a compatible RVC voice model, remix it with the instrumental, and export audio locally.

> **Status: early integration build.** The interface, Demucs separation, audio mixing/export, and RVC CLI adapter are scaffolded. CI smoke checks do not certify the Windows installer or prove full end-to-end conversion.

## Verification status

| Area | Status | Verified by |
|---|---|---|
| Build, source compilation, and unit tests | ✅ CI smoke checks | [Windows Checks workflow](.github/workflows/windows-checks.yml) |
| Core dependency imports and local Gradio startup | ✅ CI smoke checks | [Windows Checks workflow](.github/workflows/windows-checks.yml) |
| Installer on a clean Windows 10/11 x64 machine | ⏳ Pending | [Issue #1](https://github.com/ViviBeri/OneClick-AI-Cover/issues/1) |
| Managed FFmpeg MP3 import/export and failure handling | ⏳ Pending | [Issue #2](https://github.com/ViviBeri/OneClick-AI-Cover/issues/2) |
| Complete authorized-audio conversion (Demucs → RVC → mix → export) | ⏳ Pending | [Issue #3](https://github.com/ViviBeri/OneClick-AI-Cover/issues/3) |
| Clean uninstall / removal of app-managed files | ⏳ Pending | [Verification plan](docs/verification.md#section-6-uninstall-verification) |
| Signed installer / published release checksum | ⚪ Not available yet | No signed installer release artifact is published |

CI status badge: ![Windows Checks](https://github.com/ViviBeri/OneClick-AI-Cover/actions/workflows/windows-checks.yml/badge.svg)

Automated regression coverage includes sample-rate matching (including 48 kHz-to-44.1 kHz resampling when FFmpeg is available), mono-vocal mixing, stale/invalid RVC output rejection, and mocked application-pipeline tests for WAV and optional MP3 output. The mocked pipeline tests exercise orchestration with simulated Demucs/RVC stages; they **do not** prove real model inference or end-to-end audio quality. Check the linked Actions runs for the status of the latest commit.

**Important:** a green CI run is not a clean-machine installation test. See [the detailed verification plan](docs/verification.md) and copyable [verification-results template](verification-results/TEMPLATE.md). Do not describe an item as verified until the specified acceptance criteria and evidence are recorded.

### Installer integrity / SHA-256

There is not yet a published, versioned installer release asset with an official SHA-256 value to compare against. Do not treat a locally calculated hash as an official checksum. Once a versioned installer/ZIP is published, the release should include its SHA-256 next to the download link and the same value in the release notes. Testers can calculate and record the downloaded file's hash using the command in [Section 2](docs/verification.md#section-2-download-and-integrity-check).

## Setup without manually installing Python

1. Download this repository as a ZIP and extract it.
2. Double-click `install.bat` while connected to the internet.
3. Wait while it downloads a managed Python runtime, app dependencies, and the pinned RVC backend.
4. Double-click `run.bat` to launch the local interface.
5. Add an RVC `.pth` voice model you are authorized to use under `models/voices/`, select your song and model, then choose **Generate Cover**.

Setup downloads several large packages and may take a long time. You need a stable internet connection and several GB of free disk space. Python does not need to be installed manually.

## Features in this starter build

- Local Gradio interface (bound to `127.0.0.1`)
- MP3, WAV, and FLAC input validation
- Demucs vocal/instrumental separation
- RVC command-line inference adapter
- Mixing converted vocals with the original instrumental
- WAV output and optional MP3 export through FFmpeg
- Local logs and output folders
- Experimental **Train My Voice** tab that launches the upstream RVC training UI
- In-app **Import Voice Model** tab to copy an inference-ready `.pth` file into the local voice-model folder
- **Prepare Voice Recordings** tab to convert multiple recordings to mono WAVs for the RVC training dataset

## Hardware expectations

Windows 10/11 x64; 8 GB RAM is a bare starting point, while 16 GB+ is recommended. An NVIDIA GPU is strongly recommended for usable inference speed. Low-end CPUs may be extremely slow or run out of memory. Voice training is available only through the upstream RVC training interface launched from the experimental tab; the dataset preparation and training stages are not yet automated by this app.

## Training your own voice

See [`docs/voice-training.md`](docs/voice-training.md) for local recording preparation and the experimental RVC training UI. If your PC cannot train the model, read [`docs/remote-training.md`](docs/remote-training.md) for the **free-only, Kaggle-first** plan and try the [Kaggle RVC preflight notebook](notebooks/kaggle_rvc_training_preflight.ipynb). The notebook checks the environment and pinned backend revision; it is **not yet a complete training pipeline** and does not expose a public UI. No paid GPU provider or paid API is required by the project; free GPU availability is limited.

## Legal, ethical use, and community

Use only voices and audio you own or have permission to use. Do not impersonate people deceptively or create abusive/non-consensual audio. Clearly disclose synthetic audio when listeners could mistake it for a real performance or statement. Local processing does not remove copyright or consent obligations. Read [Legal and ethical use](docs/ETHICS_AND_LEGAL.md) and [Community and contribution guide](docs/COMMUNITY.md) before sharing outputs or opening issues.

No voice models or copyrighted songs are bundled. Third-party dependencies and model weights have separate license terms; see `docs/THIRD_PARTY.md`. The MIT license covers original project code only.

## Troubleshooting

- Setup errors: keep the full terminal output and consult `docs/troubleshooting.md`.
- Model errors: the model must be compatible with the pinned RVC backend.
- MP3 export errors: use WAV or install FFmpeg.
- Logs are stored at `logs/oneclick-cover.log`.

## Roadmap

- [x] Starter UI and audio-processing modules
- [x] Automatic managed Python setup script
- [x] RVC CLI integration adapter
- [ ] Verify Windows installer on a clean machine
- [ ] Verify end-to-end conversion with authorized audio/model
- [x] Improve the default conversion path when no optional RVC index is installed
- [x] Add managed FFmpeg fallback for audio import and MP3 export
- [x] Add legal/ethical boundaries and community issue guidance
- [x] Add a guarded Kaggle GPU/backend preflight notebook
- [x] Add Windows CI checks for core imports and local Gradio startup
- [x] Add regression tests for sample-rate mismatch, mono-vocal mixing, and invalid/stale RVC output
- [x] Add mocked pipeline tests for WAV output and optional MP3 export
- [ ] Build and verify private Kaggle training, checkpoint export, and model download
- [ ] Profile CPU/GPU and memory behavior
- [x] Add an experimental launcher for the upstream RVC training UI
- [ ] Automate dataset preparation and guided training workflow
- [ ] Package a reproducible Windows release

MIT license for original project code; see `LICENSE`.
