# VoiceProfile and VocalPerformanceDescriptor contracts

**Status:** Proposed domain contract for M1 — Performance Contract & Analyser.

This document defines backend-neutral, serializable domain objects. It is a specification, not a claim that the schema, analyser, persistence layer, or metrics harness are implemented.

## Design constraints

- Domain contracts must not import or depend on Demucs, RVC, Gradio, PyTorch, or a specific conversion provider.
- Persist metadata and managed-artifact references, never raw audio/model bytes in SQLite.
- Artifact references are opaque application-managed identifiers or validated paths relative to approved storage roots. Do not accept arbitrary absolute paths, URLs, or path traversal.
- All persisted objects carry an explicit schema version.
- Unknown optional fields may be ignored by older readers; unknown enum values must fail validation clearly.
- Consent/ownership attestation is required before a voice profile can be used for conversion. A profile with revoked or unknown consent is not eligible.
- A quality score is an observation with provenance, not a universal measure of identity or permission.

## 1. VoiceProfile

### Purpose

VoiceProfile is the stable domain object used to resolve either a short reference recording or a dedicated voice model. The conversion engine receives a validated profile reference and resolves its artifacts through an application-controlled storage service.

### Proposed schema

~~~json
{
  "schema_version": 1,
  "profile_id": "vp_01J...",
  "display_name": "My voice",
  "mode": "reference",
  "engine": {
    "provider": "provider-neutral-engine-id",
    "backend": "backend-adapter-id",
    "backend_version": "1.2.3",
    "capabilities": ["reference-conditioned-conversion"]
  },
  "artifacts": [
    {
      "artifact_id": "artifact_01J...",
      "role": "voice_reference",
      "storage_ref": "voices/vp_01J/reference.wav",
      "media_type": "audio/wav",
      "sha256": "hex-encoded-sha256",
      "size_bytes": 123456
    }
  ],
  "consent": {
    "status": "confirmed",
    "voice_subject": "self",
    "rights_basis": "self_recorded",
    "attested_by": "local-user",
    "attested_at": "2026-11-26T10:00:00Z",
    "statement_version": 1
  },
  "quality": {
    "score": null,
    "scale": "0_to_1",
    "dimensions": {},
    "evaluated_by": null,
    "evaluated_at": null
  },
  "created_at": "2026-11-26T10:00:00Z",
  "updated_at": "2026-11-26T10:00:00Z"
}
~~~

### Field rules

| Field | Rule |
|---|---|
| `schema_version` | Required positive integer. |
| `profile_id` | Required stable opaque identifier; immutable after creation. |
| `display_name` | Required non-empty user-facing label; no filesystem semantics. |
| `mode` | Required enum: `reference`, `trained`, or `imported`. |
| `engine.provider` | Required provider-neutral engine/provider identifier. |
| `engine.backend` | Required adapter identifier; must be registered by the application before use. |
| `engine.backend_version` | Required version or explicit backend build identifier. |
| `engine.capabilities` | Declared capabilities; validation must not infer unsupported capabilities. |
| `artifacts` | At least one artifact. Each role must be compatible with the selected mode/backend. |
| `artifacts[].storage_ref` | App-managed relative reference; reject traversal, external URLs, and unapproved absolute paths. |
| `artifacts[].sha256` | Required for immutable model/reference artifacts; verify before loading where feasible. |
| `consent.status` | Enum: `confirmed`, `revoked`, `unknown`. Only `confirmed` is usable. |
| `consent.voice_subject` | Enum/string: `self`, `other_with_permission`, `unknown`. |
| `consent.rights_basis` | Required non-empty attestation basis when status is confirmed. |
| `consent.attested_at` | UTC timestamp required when status is confirmed. |
| `quality.score` | Nullable numeric value in [0, 1]; null means not evaluated. Never use as a consent substitute. |

### Mode-specific artifact rules

- `reference`: requires a `voice_reference` audio artifact. The selected backend must explicitly support reference-conditioned/few-shot input and the recording must pass that backend's duration/content constraints.
- `trained`: requires a locally trained `voice_checkpoint`; optional `retrieval_index` must identify the matching checkpoint and compatible backend.
- `imported`: requires an externally sourced but locally stored `voice_checkpoint`; optional `retrieval_index` must match it. Preserve source/provenance metadata and checkpoint trust acknowledgement.

A standard RVC checkpoint belongs to `trained` or `imported`, not `reference`. A short recording must never be silently promoted to a checkpoint.

### Validation and lifecycle

Validation is split into:
1. Structural schema validation.
2. Mode/artifact compatibility validation.
3. Backend capability validation.
4. Artifact existence, containment, size, and checksum validation.
5. Consent/ownership eligibility validation.
6. Existing checkpoint preflight and explicit trust confirmation for checkpoint-backed profiles.

Revocation disables use immediately but does not silently erase files; provide a separate explicit deletion workflow. Profile updates create an auditable updated timestamp. Do not log raw audio, checkpoint contents, or secrets.

## 2. VocalPerformanceDescriptor

### Purpose

VocalPerformanceDescriptor is the backend-neutral analysis result for one separated source vocal. It describes measurable performance characteristics and confidence. It is not a MIDI transcription and does not claim that all expressive details can be recovered.

### Proposed schema

~~~json
{
  "schema_version": 1,
  "descriptor_id": "vpd_01J...",
  "source_audio_ref": "jobs/job_123/source.wav",
  "separated_vocal_ref": "jobs/job_123/vocals.wav",
  "separation": {
    "engine": "demucs",
    "model": "model-id-and-revision",
    "quality_gate": "passed",
    "quality_metrics": {
      "vocal_bleed_estimate": null,
      "instrumental_bleed_estimate": null,
      "review_status": "listening_reviewed"
    }
  },
  "audio": {
    "sample_rate_hz": 44100,
    "channels": 1,
    "duration_seconds": 12.5
  },
  "analysis": {
    "engine": "analyser-id",
    "version": "0.1.0",
    "frame_hop_seconds": 0.01,
    "f0_hz": [null, 220.0, 221.2],
    "voiced_mask": [false, true, true],
    "onsets_seconds": [0.42, 0.91],
    "notes": [
      {
        "start_seconds": 0.42,
        "end_seconds": 0.89,
        "midi_pitch": 57,
        "confidence": 0.94
      }
    ],
    "vibrato": [
      {
        "start_seconds": 1.1,
        "end_seconds": 1.8,
        "rate_hz": 5.4,
        "depth_cents_peak": 32.0,
        "confidence": 0.78
      }
    ],
    "rms_envelope": [
      {"time_seconds": 0.0, "rms": 0.0},
      {"time_seconds": 0.01, "rms": 0.12}
    ],
    "pause_map": [
      {"start_seconds": 0.0, "end_seconds": 0.4}
    ],
    "alignment": {
      "unit": "phoneme",
      "status": "unavailable",
      "segments": []
    }
  },
  "created_at": "2026-11-26T10:00:00Z"
}
~~~

### Field rules

- `source_audio_ref` and `separated_vocal_ref` are opaque app-managed references, not arbitrary paths.
- Separation provenance must include engine and model/revision. `quality_gate` is `passed`, `failed`, or `not_evaluated`. Analysis used for acceptance evaluation requires `passed`.
- `sample_rate_hz`, `channels`, and `duration_seconds` describe the exact separated vocal analysed.
- `frame_hop_seconds` is positive. `f0_hz` and `voiced_mask` have equal lengths and share the same frame grid. Unvoiced frames use null F0 and false mask; voiced frames require finite positive F0.
- `onsets_seconds` are sorted, finite, and within the audio duration.
- Note and vibrato intervals are ordered, non-overlapping where required by the extractor, bounded by duration, and carry confidence in [0, 1].
- Vibrato rate and depth are nullable when no reliable periodic modulation is detected. Do not manufacture zero values for unmeasurable estimates.
- `rms_envelope` is time-ordered, finite, and uses a documented window/hop configuration. RMS values are non-negative.
- `pause_map` intervals are sorted, non-overlapping, and bounded by duration.
- `alignment.unit` is `syllable` or `phoneme`; status is `available`, `unavailable`, or `failed`. Empty segments are valid only when status is not `available`.
- Alignment segments include start/end times, text/token where available, and confidence. Do not require lyric transcription to run the core F0/onset/dynamics analyser.
- Store analyser and algorithm versions so results can be reproduced and compared.

### Separation quality gate — M1 precondition

Before using separated vocals to establish analyser baselines, validate separation on the fixed M1 song set. Record per-track listening review and measurable bleed/artifact indicators. If separation fails the documented gate, mark that sample invalid for analyser/backend scoring; do not interpret leakage-driven F0, vibrato, or dynamics as source-performance truth.

## 3. Evaluation harness contract

Input: a source VocalPerformanceDescriptor and a converted-vocal descriptor generated with the same analysis configuration, plus the corresponding audio references.

Required reports:

| Metric | Definition |
|---|---|
| F0 contour correlation | Correlation over mutually voiced, time-aligned frames; report voiced coverage and undefined/insufficient-overlap cases. |
| Onset timing error | Absolute source-to-converted onset differences after documented matching; report median and 95th percentile in milliseconds. |
| Vibrato rate delta | Absolute difference in Hz for matched reliable vibrato regions; report matched-region coverage. |
| Vibrato depth delta | Absolute difference in cents for matched reliable vibrato regions; report matched-region coverage. |
| Loudness envelope correlation | Correlation of time-aligned RMS/log-loudness envelopes using a documented smoothing and silence policy. |
| Syllable/phoneme alignment score | Alignment similarity over matched tokens; report unavailable separately from zero. |

The harness must include an **identity-conversion baseline**: use the source vocal itself as the converted-vocal input. This is the null-change reference, not a model-generated result. It should establish the expected ceiling/floor and expose metric bugs. Report metric values, coverage, configuration, and invalid samples; do not collapse everything into one opaque score.

The M1 fixed evaluation set must be small, documented, rights-cleared, and stable by checksum. Include varied vocal ranges and expressive cases, but keep the set small enough for repeatable local CI or a documented manual evaluation. A sample with failed separation quality is excluded with its reason recorded.

## 4. Migration from existing RVC .pth import

Existing imported RVC checkpoints map to `mode: "imported"`; checkpoints trained through the app map to `mode: "trained"`.

Migration requirements:
1. Preserve existing model files and current import/trust behavior.
2. Create a VoiceProfile record with a stable ID, backend identity/version, checkpoint artifact reference, optional matching index reference, checksum, provenance if known, and consent status.
3. Profiles with missing consent evidence or unknown provenance remain visible for review but are not eligible for conversion until the user confirms rights and trust.
4. Do not infer voice ownership from the filename, model card, or checkpoint metadata.
5. Keep the existing model browser and Generate Cover selection compatible during a staged migration.
6. Make migration idempotent: re-running it must not create duplicate profiles or modify model bytes.
7. Provide a rollback path that leaves existing model files and the legacy model registry readable until the new profile store is verified.

The exact persistence table/index design and migration version are implementation decisions, but schema versioning, stable IDs, idempotency, and rollback are required.

## 5. M1 definition of done

M1 — Performance Contract & Analyser is complete only when:

- VoiceProfile schema validation covers all modes, required fields, mode/artifact rules, invalid paths, consent states, and quality-score bounds.
- Existing imported .pth models migrate to `mode: "imported"` profiles with an idempotent, tested migration and rollback strategy.
- The analyser runs on the fixed, rights-cleared song set whose separation has passed the documented quality gate.
- Descriptors serialize, deserialize, validate, and round-trip without loss of required fields.
- F0/voicing, onsets, vibrato, RMS/dynamics, pauses, and optional syllable/phoneme alignment are represented with confidence and explicit unavailable states.
- The harness reports every required metric and coverage on the identity-conversion baseline.
- No conversion backend is selected or required to close M1.
- Documentation and tests state that descriptor estimates depend on source separation quality.

M2 — Backend Integration & Preservation Validation consumes these contracts. It evaluates short-reference candidates against the same harness, wires RVC through trained/imported profiles, derives acceptance thresholds from M1 identity-baseline and repeatability results, then validates alignment and mixing with the original instrumental.
