# Web-first, local-first hybrid architecture

## Decision

OneClick AI Cover will use a **web-based interface with a local processing engine as its primary deployment**. The current Gradio application already follows this model: the interface is served by the local Python process and opens in the user's browser.

A remote processing service may be added later as an optional provider. It is not part of the current product and must not become a mandatory dependency.

## Why this direction

A browser interface is easier to update, works across desktop operating systems, and avoids maintaining separate native user interfaces. Keeping the inference engine local preserves the project's no-required-cloud-compute goal and avoids automatically uploading songs, recordings, datasets, and voice models.

A browser interface does **not** reduce the CPU, RAM, or GPU needed for local Demucs and RVC inference. Moving inference to a remote server can help low-end computers, but it introduces GPU hosting costs, upload bandwidth, storage, privacy, consent, abuse-prevention, and operational requirements.

## Current architecture

```text
User's browser
      |
      | localhost
      v
Local Gradio interface (app.py)
      |
      v
Local Python processing pipeline
      |
      +--> Demucs vocal separation
      +--> RVC voice conversion
      +--> Audio mixing and FFmpeg export
      |
      v
Local output files
```

The app should continue binding to `127.0.0.1` by default. Do not expose the development server to a LAN or the public internet without authentication, request limits, upload validation, CSRF/origin protections, safe file handling, and a documented threat model.

## Product modes

### 1. Local mode — primary

- Browser UI communicates with the local backend.
- Audio and voice models remain on the user's machine.
- Processing uses CPU by default; CUDA is an explicit option when supported.
- Offline operation is expected only after dependencies, model weights, and required inference assets have been downloaded.
- No paid API key, cloud GPU, or account is required for the local pipeline.

### 2. Remote mode — optional future capability

A future hosted service may run inference for users whose computers cannot handle local processing. It must be an explicitly selected provider, not a silent fallback.

Before implementation, define:
- A user-visible upload and retention policy for songs, stems, voice recordings, and generated files.
- Explicit consent and rights confirmation for every uploaded audio/model asset.
- Authentication, per-user isolation, quotas, rate limits, abuse reporting, and job cancellation.
- GPU capacity planning, queueing, cost limits, and a sustainable free/paid model.
- Encryption in transit and at rest, deletion controls, and operational logging that avoids storing audio content.
- Model licensing and checkpoint trust controls; remote execution does not make untrusted pickle checkpoints safe.
- A provider-neutral job contract so the UI does not depend on a specific cloud vendor.

No cloud inference provider should be selected until these requirements and operating costs are evaluated.

## Low-end PC strategy

The local mode should degrade gracefully rather than promise that every machine can run every model.

1. Keep CPU as the safe default and expose CUDA only when the runtime detects a compatible GPU.
2. Retain short Demucs segments as the low-memory option; smaller segments can reduce peak memory but may increase runtime.
3. Encourage short input clips and close other memory-heavy applications when RAM is limited.
4. Add measured hardware profiles only after benchmarking supported CPU/RAM combinations.
5. Show clear estimates and progress, and fail with actionable diagnostics instead of silently switching to cloud processing.
6. Keep model training clearly separate from inference; training is substantially more demanding.

## Implementation sequence

1. **Stabilize the current engine:** retain regression tests for Demucs, RVC adapter contracts, mixing, cleanup, and output validation.
2. **Improve the web UI:** responsive layout, clear processing stages, accessible controls, and useful error/progress states while retaining the local backend.
3. **Define a processing-job boundary:** separate UI event handlers from job creation, status, cancellation, and result retrieval. Keep the first implementation local.
4. **Add low-resource profiles:** benchmark and document CPU/RAM behavior before choosing defaults.
5. **Evaluate remote processing:** only after privacy, security, cost, and provider requirements above are approved.

## Non-goals

- Replacing the current working pipeline with a cloud-only product.
- Uploading audio or voice models without an explicit user action.
- Exposing the local Gradio development server publicly.
- Claiming that a browser UI makes local inference faster.
- Promising free unlimited cloud GPU processing.

## Acceptance criteria

The architecture is considered implemented when:
- The local browser interface remains the default and works without a cloud account.
- The backend can run independently of UI event handlers through a tested job interface.
- The UI can display queued/running/completed/failed/cancelled states and retrieve local outputs.
- Local audio and model files are not transmitted to a remote service in local mode.
- Any future remote provider is opt-in and meets the security, privacy, consent, and cost requirements above.
