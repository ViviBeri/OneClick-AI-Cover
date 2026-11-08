from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from demucs import audio as demucs_audio
from oneclick_cover.demucs_audio import save_audio_without_torchcodec

# Patch before importing demucs.separate, which imports save_audio by name.
demucs_audio.save_audio = save_audio_without_torchcodec

from demucs.separate import main


if __name__ == "__main__":
    main()
