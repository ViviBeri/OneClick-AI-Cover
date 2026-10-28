# OneClick-AI-Cover

Free, open-source, Windows-first local AI singing-cover creator. Separate vocals from a song, convert the vocal with a compatible RVC voice model, remix it with the instrumental, and export audio locally.

> **Status: early integration build.** The interface, Demucs separation, audio mixing/export, and RVC CLI adapter are scaffolded. The automatic Windows setup and full end-to-end conversion still need testing on a clean Windows machine.

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

See [`docs/voice-training.md`](docs/voice-training.md) for local recording preparation and the experimental RVC training UI. If your PC cannot train the model, read [`docs/remote-training.md`](docs/remote-training.md) for the **free-only, Kaggle-first** plan. No paid GPU provider or paid API is required by the project; free GPU availability is limited, and a tested remote-training notebook is still under development.

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
- [ ] Build and verify a free Kaggle training notebook with checkpoint export
- [ ] Profile CPU/GPU and memory behavior
- [x] Add an experimental launcher for the upstream RVC training UI
- [ ] Automate dataset preparation and guided training workflow
- [ ] Package a reproducible Windows release

MIT license for original project code; see `LICENSE`.