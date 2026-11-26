# Performance engineering

## Current low-risk optimization

The Demucs pipeline requires stereo 44.1 kHz audio. Previously, every input
was decoded and rewritten to a temporary WAV, including WAV files that already
matched that contract.

The prepare_demucs_input helper now inspects WAV metadata first. A non-empty
stereo 44.1 kHz WAV is passed directly to Demucs. Other formats, mono files,
and WAV files at other sample rates continue through the existing transcode
path.

This avoids one complete decode/write pass and one temporary audio copy for
compatible WAV inputs. The exact time saved depends on file duration, storage,
and decoder performance; no fixed speed-up is claimed.

## Performance constraints

- Keep all audio and model processing local.
- Preserve the existing Demucs and RVC adapters.
- Do not weaken audio validation, output checks, consent checks, or model trust
  boundaries to improve throughput.
- Keep a CPU-compatible path available.
- Treat GPU support as a separately verified runtime capability; the current
  managed installer pins CPU-only PyTorch in both environments.
- Do not add optional separation packages to the core installation merely to
  chase benchmark numbers.

## Next measured optimization targets

1. Add per-stage wall-clock and peak-memory measurements to the local job
   report, without recording audio content or private paths.
2. Add an explicit multi-song workflow that runs one RVC CLI process for a
   batch. The pinned RVC CLI constructs one VC instance and loads the selected
   model once before processing its input jobs, so a batch can amortize model
   startup across tracks.
3. Benchmark Demucs segment sizes and shifts on the same authorized test
   fixtures before changing quality/performance defaults.
4. Evaluate a long-lived RVC worker only after measuring process startup and
   confirming safe model switching, cancellation, and GPU-memory cleanup.
5. Compare optional separation engines on a fixed fixture set and retain the
   default Demucs path unless quality, memory, platform, and licensing evidence
   supports a change.

## Benchmark reporting

Report first-run and warm-run time separately. Record audio duration, real-time
factor (audio seconds divided by wall-clock seconds), CPU model, RAM, GPU and
driver where applicable, backend/model versions, settings, and output quality
metrics. Do not compare runs with different model weights or settings as if
they were equivalent.
