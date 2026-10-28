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
- Confirm the setup completed and `vendor/rvc/infer/cli.py` exists.
- Use an RVC model compatible with the pinned backend.
- Some models need a matching index file and additional HuBERT/RMVPE assets.
- Do not use models without permission.

## MP3 export unavailable
Choose WAV, or install FFmpeg and ensure `ffmpeg.exe` is on PATH.

## Find logs
The app writes diagnostics to `logs/oneclick-cover.log`. Keep logs free of private paths or personal information before posting them publicly.
