# Troubleshooting

## Installer fails
- Run `install.bat` from an extracted folder, not inside the ZIP viewer.
- Keep the console open and copy the last error lines.
- Ensure internet access and several GB of free space.
- Security software or a restricted network may block downloads.
- The installer has not yet been verified on a clean Windows machine.

## First separation is slow
Demucs downloads model weights on first use. CPU-only separation can take a long time and use substantial RAM.

## RVC backend or model error
- Confirm the setup completed and `vendor/rvc/webui.py` exists. The pinned RVC backend uses Python 3.12 and `requirments_cpu_py312.txt` for CPU/Intel/AMD systems.
- Use an RVC model compatible with the pinned backend.
- The installer now downloads the pinned HuBERT Transformers files (`assets/hubert_base/config.json`, `preprocessor_config.json`, and `pytorch_model.bin`) plus `assets/rmvpe/rmvpe.pt` from the public `lj1995/VoiceConversionWebUI` Hugging Face repository. The downloader pins the repository revision and verifies file sizes and SHA-256 for the large weight files.
- If asset setup fails, rerun `install.bat` after restoring network access. Check that the installer reaches the **Downloading and verifying required HuBERT and RMVPE inference assets** stage. The downloader is safe to rerun and skips files that already pass verification.
- Some models need a matching index file; the app uses `--index-rate 0` by default, so an added index is not required for the current Generate Cover flow.
- Do not use models without permission.

## MP3 export unavailable
Choose WAV, or install FFmpeg and ensure `ffmpeg.exe` is on PATH.

## Find logs
The app writes diagnostics to `logs/oneclick-cover.log`. Keep logs free of private paths or personal information before posting them publicly.
