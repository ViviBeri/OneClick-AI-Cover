# Local-first application architecture

## Product decision

OneClick AI Cover is a local-first, Windows-first AI singing-cover workstation. A user supplies (1) an original song containing the performance to reproduce and (2) a recording of their own voice or a dedicated voice model they are authorized to use.

The application analyses the original vocal performance, converts that performance into the target user's voice, and mixes the converted vocal with the original instrumental. The goal is to preserve the original performance's musical structure and expressive details as closely as the selected conversion backend allows.

The core workflow must not require a cloud account, hosted database, paid AI API, subscription, or cloud GPU.

## Product experience

1. Import an original song.
2. Add or select a target voice.
3. Analyse and separate the original vocal and instrumental.
4. Inspect the vocal performance and derive conversion guidance.
5. Convert the vocal into the target voice.
6. Align and validate the converted vocal.
7. Mix it with the original instrumental.
8. Preview and export WAV or MP3.

The interface should expose understandable progress and actionable errors without requiring users to operate Demucs, RVC, Python, or command-line tools directly.

## Two supported voice-input modes

Both modes are first-class product requirements. They share one target-voice contract so the downstream conversion pipeline does not need separate product logic.

### Mode A — Short voice recording

A beginner can provide a short, clean recording of their own voice. The application validates the recording and routes it to a compatible reference-conditioned or few-shot voice-conversion backend when one is installed and verified.

Requirements:
- Guide users to record clean, dry speech or singing with minimal background noise, reverb, clipping, and competing voices.
- Check duration, sample rate, channels, clipping, silence, and usable voiced content.
- Show whether the selected backend supports the supplied recording length and language.
- Keep the recording local by default.
- Do not imply that standard RVC inference can create a voice identity from an arbitrary short sample. Standard RVC inference normally requires a compatible trained checkpoint.
- If no compatible short-reference backend is available, explain that a dedicated model must be created or imported. Do not silently fall back or claim unsupported conversion.

### Mode B — Dedicated personal voice model

An advanced user can prepare a larger dataset, train a dedicated voice model, and reuse it across projects.

Requirements:
- Prepare and validate recordings for a single speaker.
- Keep the current RVC training bridge clearly labelled experimental until the full workflow is automated and verified.
- Support importing an inference-ready compatible checkpoint and its optional matching retrieval index.
- Retain checkpoint quarantine, explicit trust acknowledgement, and model provenance/permission guidance.
- Keep datasets, checkpoints, and generated files outside Git.
- Make training hardware and time requirements clear.

The current RVC training interface is a bridge to upstream tooling, not yet an automated end-to-end training pipeline.

## Target voice contract

Both modes resolve to a common internal target-voice profile containing:
- A stable local voice-profile identifier.
- The selected backend and backend version.
- A reference recording or local checkpoint reference, as appropriate.
- Optional compatible retrieval-index metadata.
- Sample-rate and preprocessing metadata.
- User confirmation that they own the voice or have permission to use it.
- Model/recording provenance and trust state.

Do not store raw audio or model binaries inside job metadata. Keep them in managed local storage and store only validated references and metadata.

## Performance-preserving conversion pipeline

The original song supplies the performance reference. The target voice supplies the voice identity. Keep those responsibilities separate.

~~~text
Original song
    |
    +--> Validate / decode / normalize
    |
    +--> Vocal separation --------------------> Original instrumental
    |            |
    |            v
    |       Original vocal
    |            |
    |            v
    |       Performance analysis
    |       - F0 / melody contour
    |       - timing / note onsets / durations
    |       - vibrato rate and depth, plus amplitude-modulation (tremolo) rate and depth where measurable
    |       - pitch bends and transitions
    |       - dynamics / loudness envelope
    |       - phrasing / pauses / syllable alignment
    |            |
    |            v
    |       Conversion guidance / alignment
    |            |
    |            +-----------------------------+
    |                                          |
Target voice input                             |
    |                                          |
    +--> Short reference recording              |
    |       -> validation                       |
    |       -> compatible few-shot backend      |
    |                                          |
    +--> Dedicated voice model                  |
            -> model preflight                  |
            -> compatible RVC/backend           |
                                               |
                                               v
                                  Voice conversion
                                               |
                                               v
                                  Output alignment and QA
                                  - duration / timing
                                  - pitch contour
                                  - vocal level
                                  - clipping / silence
                                  - artefact checks
                                               |
                                               v
                                  Mix with original instrumental
                                               |
                                               v
                                  Preview -> WAV / MP3 export
~~~

### Performance attributes to analyse

Where technically reliable, extract:
- Fundamental-frequency contour and note transitions.
- Note onsets, offsets, durations, and phrase boundaries.
- Vibrato rate and depth, plus amplitude-modulation (tremolo) rate and depth where measurable.
- Pitch bends, slides, and transitions.
- Amplitude/loudness envelope and dynamic changes.
- Syllable timing, pauses, and lyric alignment where supported.
- Vocal/instrumental timing and sample-rate relationships.

These measurements guide conversion and quality control. They do not guarantee that every conversion model can reproduce every nuance. Backend capabilities differ; report unsupported or low-confidence attributes rather than claiming exact preservation.

### Output quality gates

Before mixing, compare the converted vocal with the source performance for plausible duration and phrase alignment, pitch contour and note transitions, vibrato and amplitude-modulation rate/depth where measurable, loudness and dynamics, clipping, silence, discontinuities, and obvious conversion artefacts.

Keep the original separated vocal as a non-destructive reference. Do not overwrite it. Allow the user to preview the converted vocal before final mixing.

## Current architecture

~~~text
User's browser
      |
      | localhost / reviewed same-origin broker
      v
Local Gradio interface (app.py)
      |
      v
Authenticated local job API (127.0.0.1)
      |
      v
Local job runner and processing pipeline
      |
      +--> Audio validation and preparation
      +--> Demucs / selected separation backend
      +--> Vocal performance analysis
      +--> Target voice resolver
      |      +--> Short-reference backend (future capability)
      |      +--> Dedicated RVC model
      +--> Alignment and output quality checks
      +--> Audio mixing and FFmpeg export
      |
      v
Local files: uploads, references, datasets, models, outputs
Local metadata: SQLite job history
~~~

The local app must bind to 127.0.0.1 by default. The native API remains bearer-token authenticated. Browser integration must use a separately reviewed same-origin broker with short-lived sessions, HttpOnly cookies, CSRF protection, and strict Host/Origin checks. Never expose the native bearer token to browser JavaScript, URLs, or browser storage. Do not expose the local API or Gradio server to a LAN or public internet without a separately reviewed device-pairing and network-security design.

## Product modes

### 1. Local desktop mode — primary

- Browser UI and processing backend run on the user's Windows computer.
- Songs, voice recordings, datasets, checkpoints, and outputs stay local.
- CPU is the safe default; CUDA is available only when supported and explicitly selected/detected.
- Offline use is possible only after required dependencies, model weights, and inference assets have been downloaded.
- No paid API key, cloud GPU, hosted database, or account is required.
- Voice model training is separate from inference and has substantially higher hardware requirements.

### 2. Same-network companion access — future

An Android/PWA client may control a paired Windows PC over private Wi-Fi. This requires device pairing, identity, short-lived credentials, explicit approval, origin/CSRF protections, and a narrowly scoped API. Do not solve this by binding to 0.0.0.0 or exposing the bearer token.

### 3. Remote processing — not part of the zero-budget core

A hosted service introduces infrastructure, storage, bandwidth, and GPU costs. It must not be a silent fallback or required feature. No unlimited free cloud inference is promised.

Any optional provider must define explicit consent, rights confirmation, authentication, per-user isolation, quotas, cost limits, encryption, retention/deletion controls, model licensing, checkpoint trust, and a provider-neutral job contract.

## Local persistence

The local API stores job metadata in SQLite at data/jobs.sqlite3. Job records, status, progress, timestamps, errors, and output references persist across restarts. Audio and model files remain in managed local folders. Interrupted jobs are marked failed on next launch; they are not automatically resumed. Never store raw audio or model binaries in SQLite.

## Low-end PC strategy

1. Keep CPU as the safe default and expose CUDA only when a compatible runtime is detected.
2. Retain short Demucs segments as a low-memory option.
3. Encourage short test clips and close other memory-heavy applications when RAM is limited.
4. Benchmark supported CPU/RAM/GPU combinations before publishing hardware profiles.
5. Show clear progress and actionable diagnostics; never silently switch to cloud processing.
6. Explain that dedicated voice training is more demanding than inference.
7. Let users select short-reference mode only when a compatible backend and hardware profile are available.

## Implementation sequence

### M1 — Performance Contract & Analyser (backend-independent)

1. Specify and validate the versioned VoiceProfile and VocalPerformanceDescriptor contracts.
2. Add VoiceProfile persistence, consent/ownership metadata, artifact references, and quality-score provenance.
3. Migrate existing imported RVC .pth models to `mode=imported` profiles with idempotency and rollback.
4. Validate source-separation quality on a fixed, rights-cleared evaluation set; failed separation blocks performance scoring.
5. Implement the backend-neutral vocal analyser and descriptor serialization.
6. Build the objective evaluation harness and record identity-conversion baseline metrics.

M1 must be independently closable. It must not depend on selecting or integrating a voice-conversion backend.

### M2 — Backend Integration & Preservation Validation

1. Evaluate short-reference backends against the M1 fixed set and metric harness.
2. Wire RVC inference through `VoiceProfile(mode=trained|imported)`.
3. Set preservation thresholds using M1 identity-baseline and repeatability results.
4. Validate converted vocal performance against the descriptor and agreed thresholds.
5. Mix the converted vocal with the original instrumental and verify loudness, timing, and listening quality.

### Product integration after the engine gates

1. Complete the secure browser broker and upload/job-control integration.
2. Connect the responsive Studio UI to the validated profile and job contracts.
3. Add secure same-network Android/PWA pairing.
4. Evaluate remote processing only if a separately funded, opt-in design is approved.

## Non-goals

- Replacing the local-first product with a cloud-only service.
- Requiring an account to generate a local cover.
- Uploading audio or voice models without explicit user action.
- Claiming short voice samples work with standard RVC checkpoints without a compatible reference-conditioned backend.
- Claiming exact preservation of every vocal nuance before objective and listening validation.
- Exposing local APIs publicly or promising free unlimited cloud GPU processing.

## Acceptance criteria

The architecture is considered implemented when:
- Local mode works without cloud credentials.
- Users can select either a validated short-reference voice path or a compatible dedicated voice model.
- Both modes produce the same job/output contract.
- The original vocal performance is analysed for pitch, timing, dynamics, and supported expressive attributes.
- The converted vocal is checked against the original performance before mixing.
- The original instrumental is retained and mixed with the converted vocal.
- The UI shows progress, errors, preview, and result retrieval.
- Local audio and model files are not transmitted in local mode.
- Job metadata persists locally without a hosted database.
- Any future remote provider remains optional and meets security, privacy, consent, and cost requirements.
