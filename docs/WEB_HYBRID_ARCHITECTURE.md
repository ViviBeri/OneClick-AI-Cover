# Local-first application architecture

## Decision

OneClick AI Cover is a local-first application with a browser-based interface and a local processing engine. The Windows desktop app starts the Gradio interface and an authenticated loopback API on the user's computer.

The core product has no cloud account, hosted database, cloud storage, paid AI API, or remote inference dependency.

## Why this direction

Local processing keeps songs, recordings, datasets, voice checkpoints, and generated audio on the user's computer. It avoids mandatory accounts, recurring service costs, and dependence on a third-party backend.

A browser interface provides a responsive UI while the local Python engine performs the compute-intensive work. The browser is a presentation and control layer; it does not make local inference faster or remove hardware requirements.

## Current architecture

```text
User's browser
      |
      | localhost
      v
Local Gradio interface (app.py)
      |
      v
Authenticated local job API (127.0.0.1)
      |
      v
Local job runner and processing pipeline
      |
      +--> Demucs vocal separation
      +--> RVC voice conversion
      +--> Audio mixing and FFmpeg export
      |
      v
Local files: uploads, models, datasets, outputs
```

The local app must bind to `127.0.0.1` by default. Do not expose the local API or Gradio server to a LAN or public internet without a separately reviewed device-pairing and network-security design.

## Product modes

### 1. Local desktop mode — primary

- The browser UI communicates with the local backend.
- Audio, voice models, datasets, and generated files stay on the user's machine.
- Processing uses CPU by default; CUDA is an explicit option when supported.
- Offline operation is expected only after dependencies, model weights, and required inference assets have been downloaded.
- No paid API key, cloud GPU, hosted database, or account is required.
- Job execution and local API access remain on the same machine.

### 2. Same-network companion access — future

A future Android/PWA client may control a paired Windows PC over the user's private Wi-Fi network. This requires a dedicated pairing flow, device identity, short-lived credentials, explicit approval, origin/CSRF protections, and a narrowly scoped API. Do not solve this by binding the API to `0.0.0.0` or exposing its bearer token to arbitrary browser code.

### 3. Remote processing — not part of the zero-budget core

A future hosted service would introduce infrastructure, storage, bandwidth, and GPU operating costs. It must not be added as a silent fallback or required feature. The project will not promise unlimited free cloud inference.

Any future optional provider must first define:
- Explicit user consent and rights confirmation for every uploaded audio/model asset.
- Authentication, per-user isolation, quotas, rate limits, abuse reporting, and cancellation.
- GPU capacity planning, queueing, cost limits, and a sustainable funding model.
- Encryption in transit and at rest, retention limits, and deletion controls.
- Model licensing and checkpoint trust controls.
- A provider-neutral job contract so the UI does not depend on one vendor.

## Local persistence

The local API stores job metadata in SQLite at `data/jobs.sqlite3`. Job records, status, progress, timestamps, errors, and output paths persist across application restarts; audio and model files remain in managed local folders. Jobs that were queued or running when the application last closed are marked failed with an interruption message on the next launch. This is recovery of job history, not automatic resumption of interrupted audio processing. The database is local application state and is excluded from version control.

## Low-end PC strategy

The local mode should degrade gracefully rather than promise that every machine can run every model.

1. Keep CPU as the safe default and expose CUDA only when the runtime detects a compatible GPU.
2. Retain short Demucs segments as the low-memory option; smaller segments can reduce peak memory but may increase runtime.
3. Encourage short input clips and close other memory-heavy applications when RAM is limited.
4. Add measured hardware profiles only after benchmarking supported CPU/RAM combinations.
5. Show clear progress and actionable diagnostics instead of silently switching to cloud processing.
6. Keep model training separate from inference; training is substantially more demanding.

## Implementation sequence

1. Stabilize the local processing engine and regression tests.
2. Complete the authenticated local API lifecycle and job endpoints.
3. Connect the UI to job creation, progress, cancellation, and result retrieval without exposing API credentials to browser code.
4. Add local SQLite persistence for project metadata and job history.
5. Improve the responsive browser UI while retaining the local backend.
6. Add secure same-network Android/PWA pairing.
7. Evaluate remote processing only if a separately funded, opt-in design is approved.

## Non-goals

- Replacing the working pipeline with a cloud-only product.
- Requiring users to register for an account to generate covers.
- Uploading audio or voice models without explicit user action.
- Exposing the local API or Gradio development server publicly.
- Claiming that a browser UI makes local inference faster.
- Promising free unlimited cloud GPU processing.

## Acceptance criteria

The local-first architecture is implemented when:
- Local mode works without any cloud account or credentials.
- The backend runs independently through a tested job interface.
- The UI can display job states and retrieve local outputs.
- Local audio and model files are not transmitted in local mode.
- Project metadata and job history can persist locally without a hosted database.
- Any future remote provider is optional and meets security, privacy, consent, and cost requirements.
