# Audio separation backend architecture

## Current implementation

The processing pipeline selects a local separation engine through the
oneclick_cover.separation_backends module. The backend contract accepts a
prepared WAV file and a job workspace, reports optional progress, and returns
paths to the vocal and instrumental WAV files.

Demucs remains the only installed backend and the default. Existing CPU-first
settings, process timeout, streamed progress, and output validation remain in
the Demucs implementation.

## Optional engine evaluation

UVR5-UI is a useful reference implementation built on python-audio-separator.
Its documented model families include VR Arch, MDX-Net, Demucs, MDX23C,
Mel-Band Roformer, and BS-Roformer. It also documents ensembles and chunked
processing. These capabilities are not implemented by this backend interface.

Before adding an optional engine:

1. Verify Python and PyTorch compatibility against the managed Windows runtime.
2. Review the engine package license and every model's individual terms.
3. Keep model downloads explicit and store weights outside the source tree.
4. Enforce output paths within the per-job workspace.
5. Apply a hard timeout and terminate child processes on timeout.
6. Test CPU fallback, GPU detection, memory use, progress, and cleanup.
7. Compare separation quality on the same user-authorized audio fixtures.

The UVR5-UI application and its Gradio interface will not be embedded. The
optional engine must integrate through the backend contract and preserve the
existing local-only security boundary.

## Hardware and cost

Advanced MDX/Roformer models can require substantially more memory, storage,
and GPU compute than the current CPU-first Demucs path. Do not download models
automatically or claim that all models are practical on low-resource PCs.
The core workflow remains local and does not depend on paid APIs or hosted GPU
services.
