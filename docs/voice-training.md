# Train your own voice model (experimental)

The **Train My Voice** tab opens the training interface supplied by the pinned upstream RVC backend. This is a bridge to the upstream UI, not a fully automated trainer.

## Before you start

- Use your own voice recordings or recordings for which you have explicit permission.
- Prepare clean recordings with one speaker. Remove background music, reverb, clipping, and long silences where practical.
- Ten to thirty minutes of clean recordings is a practical starting point, not a guarantee of quality.
- Keep original recordings private and do not commit them to GitHub.

## Launch

1. Run `install.bat` and confirm it finishes without errors.
2. Run `run.bat` and open the local OneClick-AI-Cover interface.
3. Select **Train My Voice (Experimental)** and click **Open RVC Training UI**.
4. A separate console should open. Wait for the upstream backend to print its local web address, then open that address in your browser.
5. Follow the upstream RVC instructions for dataset preparation, preprocessing, F0/feature extraction, training, and index generation.
6. Export an inference-ready `.pth` model. Place it in `models/voices/` and use **Refresh models** in the Generate Cover tab.

## Hardware warning

Training is substantially more demanding than converting a song. A low-end or CPU-only PC may take many hours or days and may run out of memory. An NVIDIA GPU is strongly recommended. Stop if the PC overheats or becomes unstable.

## Current limitations

- The app does not yet prepare datasets, select training settings automatically, monitor training progress, or import the finished model automatically.
- The upstream RVC UI and its model requirements can change. This integration is not yet verified end-to-end on a physical Windows PC.
- Training results vary with dataset quality, hardware, and configuration.
