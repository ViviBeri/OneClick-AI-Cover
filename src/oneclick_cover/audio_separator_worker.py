"""Isolated worker for the optional python-audio-separator runtime."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit("Expected input WAV, output directory, and model path.")

    input_wav = Path(sys.argv[1]).resolve()
    output_dir = Path(sys.argv[2]).resolve()
    model_path = Path(sys.argv[3]).resolve()

    if not input_wav.is_file():
        raise FileNotFoundError(f"Input audio does not exist: {input_wav}")
    if not model_path.is_file():
        raise FileNotFoundError(
            "The selected Audio Separator model is not installed. "
            "Download and verify it before selecting this backend."
        )

    from audio_separator.separator import Separator

    output_dir.mkdir(parents=True, exist_ok=True)
    separator = Separator(
        model_file_dir=str(model_path.parent),
        output_dir=str(output_dir),
        output_format="WAV",
        log_level="WARNING",
    )
    separator.load_model(model_filename=model_path.name)
    output_files = separator.separate(
        str(input_wav),
        {"Vocals": "vocals", "Instrumental": "instrumental"},
    )

    resolved = [Path(path).resolve() for path in output_files]
    if any(path.parent != output_dir for path in resolved):
        raise RuntimeError("Audio Separator returned an output outside the job directory.")

    vocals = next((path for path in resolved if path.name.lower().startswith("vocals.")), None)
    instrumental = next(
        (path for path in resolved if path.name.lower().startswith("instrumental.")),
        None,
    )
    if vocals is None or instrumental is None:
        raise RuntimeError("The selected model did not produce both vocals and instrumental stems.")
    if not vocals.is_file() or not instrumental.is_file():
        raise RuntimeError("Audio Separator reported output files that are missing.")

    print(json.dumps({"vocals": str(vocals), "instrumental": str(instrumental)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
