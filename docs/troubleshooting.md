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
- The installer downloads four required assets from the pinned revision of the public `lj1995/VoiceConversionWebUI` Hugging Face repository. The SHA-256 values for `hubert_base/pytorch_model.bin` (`cc8c20f4b90a520757260197a3ff2505705a7adbd20ad9eeaa4e1a9b38442ef5`) and `rmvpe.pt` (`6d62215f4306e3ca278246188607209f09af3dc77ed4232efdd069798c4ec193`) match the SHA-256 values displayed by Hugging Face for those large files at the pinned revision. Hugging Face does not expose corresponding SHA-256 metadata for the two small JSON files. Their hashes (`config.json`: `0346950779dfb7f9316fa74ed846e2b8a22a08eedfdc5387b73f327cb1a4a7cf`; `preprocessor_config.json`: `7c1976a680fb7acc757cd36fb08eef878fa36c70b4c9d2d595df9c608bbbbf0e`) were calculated locally from the first download of each file at that revision and pinned in the downloader. These locally pinned JSON hashes protect against later content changes but are not independently published Hugging Face checksums.
- If asset setup fails, rerun `install.bat` after restoring network access. Check that the installer reaches the **Downloading and verifying required HuBERT and RMVPE inference assets** stage. The downloader is safe to rerun and skips files that already pass verification.
- Some models need a matching index file; the app uses `--index-rate 0` by default, so an added index is not required for the current Generate Cover flow.
- Do not use models without permission.

## MP3 export unavailable
Choose WAV, or install FFmpeg and ensure `ffmpeg.exe` is on PATH.

## Find logs
The app writes diagnostics to `logs/oneclick-cover.log`. Keep logs free of private paths or personal information before posting them publicly.
