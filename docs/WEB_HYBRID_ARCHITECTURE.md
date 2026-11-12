# Web-first, local-first hybrid architecture

## Decision

OneClick AI Cover uses a **web-based interface with a local processing engine as its primary deployment**. The current Gradio application is served by the local Python process and opens in the user's browser.

Supabase is the optional cloud account and metadata layer for a future browser/PWA client. It does not replace local Demucs/RVC inference and is not required for local mode.

## Why this direction

A browser interface is easier to update, works across desktop operating systems, and avoids maintaining separate native user interfaces. Keeping inference local avoids automatically uploading songs, recordings, datasets, and voice models.

Supabase can provide user authentication, Postgres metadata, and Realtime updates for multi-device history and status synchronization. These cloud features are opt-in. They do not provide GPU inference or make local inference available when the PC is offline.

## Current architecture

```text
User's browser
      |
      | localhost
      v
Local Gradio interface (app.py)
      |
      v
Authenticated local job API
      |
      v
Local job runner and processing pipeline
      |
      +--> Demucs vocal separation
      +--> RVC voice conversion
      +--> Audio mixing and FFmpeg export
      |
      v
Local output files

Future signed-in browser/PWA
      |
      +--> Supabase Auth
      +--> Postgres: profile, project labels, job metadata
      +--> Realtime: authorized metadata updates
```

The local app should continue binding to `127.0.0.1` by default. Do not expose the local API to a LAN or public internet without a separately reviewed device-pairing and network-security design.

## Supabase data boundary

The initial schema is in `supabase/migrations/` and is documented in [Supabase integration](SUPABASE_INTEGRATION.md).

- Auth identifies a user for cloud metadata.
- Postgres stores profiles, project labels, and job metadata.
- Realtime can synchronize authorized job metadata.
- Storage is not enabled by the initial integration.
- Audio, stems, datasets, model checkpoints, and local filesystem paths remain local.

All exposed tables must have Row Level Security and least-privilege grants. A publishable key may be used by a client only with RLS correctly configured. Secret/service-role keys must remain server-side.

## Product modes

### 1. Local mode — primary

- Browser UI communicates with the local backend.
- Audio and voice models remain on the user's machine.
- Processing uses CPU by default; CUDA is an explicit option when supported.
- Offline operation is expected only after dependencies, model weights, and required inference assets have been downloaded.
- No paid API key, cloud GPU, or account is required for the local pipeline.
- Supabase is optional and can be disconnected without disabling local generation.

### 2. Cloud account mode — optional

- Users may sign in to synchronize project labels and job metadata.
- Job execution remains on the paired local PC.
- Realtime may update status/history across signed-in clients.
- A cloud job record does not imply that a PC is online or authorize remote control.
- Audio and voice-model uploads are not part of this mode.

### 3. Remote processing — optional future capability

A future hosted service may run inference for users whose computers cannot handle local processing. It must be an explicitly selected provider, not a silent fallback.

Before implementation, define:
- A user-visible upload and retention policy for songs, stems, voice recordings, datasets, and generated files.
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

1. Stabilize the current engine and its regression tests.
2. Improve the responsive browser UI while retaining the local backend.
3. Keep the processing-job boundary and local API independent of UI event handlers.
4. Add the Supabase metadata schema and RLS foundation.
5. Build the browser/PWA authentication and metadata-sync client.
6. Add secure PC pairing for remote control without exposing the local API.
7. Evaluate optional remote processing only after privacy, security, cost, and provider requirements are approved.

## Non-goals

- Replacing the current working pipeline with a cloud-only product.
- Uploading audio or voice models without an explicit user action.
- Exposing the local API or Gradio development server publicly.
- Claiming that a browser UI makes local inference faster.
- Promising free unlimited cloud GPU processing.

## Acceptance criteria

The architecture is considered implemented when:
- Local mode works without a Supabase account.
- The backend can run independently through a tested job interface.
- The UI can display job states and retrieve local outputs.
- Local audio and model files are not transmitted in local mode.
- Supabase metadata is isolated by RLS and can be disabled independently.
- Any future remote provider is opt-in and meets the security, privacy, consent, and cost requirements above.
