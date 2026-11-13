# Optional Audio Separator runtime

## Status

The `audio-separator` backend is an opt-in adapter for the upstream
`python-audio-separator` package. Demucs remains the default and the core
installation does not gain the package's dependency tree.

The adapter launches a separate Python interpreter. This avoids resolving
upstream's current NumPy 2+ dependency against the application's NumPy <2
constraint and keeps optional ONNX/PyTorch packages out of the core runtime.
The external runtime must be installed and validated independently.

## Configure

1. Create a dedicated Python 3.11 or 3.12 environment for
   `python-audio-separator`.
2. Install the upstream package and the appropriate CPU or hardware runtime
   using its official installation instructions.
3. Download a supported model deliberately. Review that model's license and
   source before use.
4. Set these environment variables before starting OneClick AI Cover:

   - `ONECLICK_AUDIO_SEPARATOR_PYTHON`: absolute path to the isolated
     environment's Python executable.
   - `ONECLICK_AUDIO_SEPARATOR_MODEL_PATH`: absolute path to the downloaded
     model file.

5. Select `audio-separator` as the pipeline backend in a future UI
   configuration. The current Gradio form still exposes Demucs only.

The adapter refuses to run if the runtime or model file is missing. It does
not download models, access a remote API, or expose the local service to the
network. The worker verifies that both output stems remain inside the job
workspace.

## Model selection

Choose a model that produces both `Vocals` and `Instrumental` stems. The
upstream model catalogue lists multiple MDX and RoFormer choices, but quality,
memory use, and licensing vary by model. A model trained for instrumental
removal or vocal extraction is not a guarantee of lead-singer-only separation
in duets or backing-vocal arrangements.

## Compatibility and hardware

The upstream package currently declares NumPy 2+ and separate optional
ONNX Runtime CPU/GPU/DirectML extras. Keep it isolated until the application's
managed runtime has been deliberately upgraded and regression-tested.
Windows DirectML is experimental upstream; CUDA and CPU support depend on the
installed runtime and hardware. Advanced models can be slow or exceed system
memory on low-resource PCs.

## Validation still required

Unit tests mock the external process. Real Windows CPU/GPU inference, model
license review, output listening tests, memory benchmarks, and model-specific
quality comparisons are still required before this backend is recommended as
production-ready.
