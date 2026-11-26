# Performance engineering

## Current low-risk optimization

The Demucs pipeline requires stereo 44.1 kHz audio. Previously, every input
was decoded and rewritten to a temporary WAV, including WAV files that already
matched that contract.

The `prepare_demucs_input` helper inspects WAV metadata first. A non-empty
stereo 44.1 kHz WAV is passed directly to Demucs. Other formats, mono files,
and WAV files at other sample rates continue through the existing transcode
path.

This avoids one complete decode/write pass and one temporary audio copy for
compatible WAV inputs. The exact time saved depends on file duration, storage,
and decoder performance; no fixed speed-up is claimed.

## Stage timing reports

Every pipeline run writes a path-free JSON timing report under
`outputs/diagnostics/` by default. The report records:

- Per-stage wall-clock seconds for validation, audio preparation, separation,
  conversion, sample-rate matching, mixing, export when requested, and output
  validation.
- Total wall-clock seconds and a UTC start timestamp.
- Completion or failure status and, on failure, the exception class only.
- Non-sensitive execution settings such as output format, separation backend,
  device, and Demucs segment setting.

The report does not contain audio, model bytes, input paths, model paths, or
exception messages. Failed runs retain their timing report even though the
temporary job directory is cleaned up. Callers can supply
`timing_report_path` to write the report to a different location.

## Reproducible benchmark runner

The benchmark script runs the real local Demucs-to-RVC pipeline. It records
system metadata, audio duration when SoundFile can probe the input, real-time
factor, and sampled process-tree memory.

Install the optional benchmark dependency:

```powershell
python -m pip install -e ".[benchmark]"
```

Run the benchmark with an authorized source recording and an authorized,
inference-ready RVC checkpoint:

```powershell
python scripts/benchmark.py --input "D:\\Audio\\source.wav" --model "models\\voices\\authorized-model.pth" --output-dir "outputs\\benchmarks" --report "outputs\\benchmarks\\run-01.json" --device cpu --demucs-segment 5
```

Run it a second time with the same input, model, settings, and machine to
compare first-run and warm-run behavior. Keep each report; do not overwrite
the first result. Compare runs only when their environment, model revision,
input, and settings match.

The `benchmark` optional dependency group contains `psutil`; it is not part
of the production installation. If psutil is unavailable, the conversion and
timing report still run, and memory measurement is marked unavailable.

Memory is sampled every 100 ms by default across the benchmark process and its
child processes, including the separate RVC process. The reported peak is the
highest sampled sum of process RSS, not an exact physical-memory peak. Short
spikes between samples may be missed, and summing RSS can count shared pages
more than once. Never present this measurement as total system peak RAM.

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

1. Benchmark Demucs segment sizes and shifts on the same authorized fixture
   set before changing quality/performance defaults.
2. Add an explicit multi-song workflow that runs one RVC CLI process for a
   batch. The pinned RVC CLI constructs one VC instance and loads the selected
   model once before processing its input jobs, so a batch can amortize model
   startup across tracks.
3. Evaluate a long-lived RVC worker only after measuring process startup and
   confirming safe model switching, cancellation, and GPU-memory cleanup.
4. Compare optional separation engines on a fixed fixture set and retain the
   default Demucs path unless quality, memory, platform, and licensing evidence
   supports a change.

## Benchmark reporting

Report first-run and warm-run time separately. Record audio duration, real-time
factor (audio seconds divided by wall-clock seconds), CPU model, RAM, GPU and
driver where applicable, backend/model versions, settings, and output quality
metrics. Do not compare runs with different model weights or settings as if
they were equivalent.
