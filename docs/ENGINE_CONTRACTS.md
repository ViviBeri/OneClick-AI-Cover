# VoiceProfile and VocalPerformanceDescriptor contracts

**Status:** M1 contract specification — proposed for implementation review.

This document defines backend-neutral, serializable domain objects and evaluation semantics. It is a specification, not a claim that the schemas, analyser, persistence layer, or metrics harness are implemented.

## 1. Decisions locked for M1

These decisions are intentionally conservative because changing them later would invalidate persisted profiles or evaluation results.

1. **VoiceProfile records are immutable snapshots.** A profile's mode, engine identity, artifact set, consent attestation, and evaluation records are not edited in place. A changed model, reference recording, backend build, or consent statement creates a new profile with `derived_from_profile_id` pointing to its predecessor. Display-name changes may be stored as separate presentation metadata, not by mutating the identity snapshot.
2. **Engine identity is fully versioned.** Use `provider/backend@version+config_sha256:<hex>`. The config hash covers inference-relevant configuration and preprocessing. A friendly backend name alone is not an identity. Metrics are comparable only when their engine, analyser, metric implementation, and evaluation-set identities are compatible.
3. **Artifacts are content-addressed.** The canonical artifact identity is SHA-256 plus byte size and media type. A managed storage locator is only a retrieval location, never the identity. Missing, checksum-mismatched, or inaccessible artifacts put the profile in `broken`; resolution fails closed and never falls back to another profile or file.
4. **Consent is append-only and versioned.** Store an immutable attestation record with the exact statement version and SHA-256 of the statement text, subject/rights basis, attester, and UTC timestamp. Revocation is a new append-only event. Existing attestations are never overwritten.
5. **Quality is a collection of evaluation records, not a scalar.** Every record pins metric implementation, analyser, engine identity, evaluation-set hash, per-metric values, coverage, and timestamp. Do not compare or aggregate across incompatible identities.
6. **Legacy RVC imports remain explicitly unverified.** Existing .pth files migrate as `mode=imported`, `provenance.status=unknown`, and `consent.status=unverified`. They remain visible for review but are ineligible for conversion, sharing, or export until the user supplies the missing trust/rights attestations. Never invent provenance or ownership.
7. **Schema migrations are forward-only and transactional.** Migrate the local profile store in place using ordered versioned migrations and a backup/rollback checkpoint. Do not attempt automatic downgrade; restore the pre-migration backup if a migration must be reversed. Readers reject newer unsupported schema versions with an actionable error.
8. **Deletion uses tombstones and artifact reference tracking.** Deleting a profile creates a tombstone; it does not immediately remove shared artifacts. Physical deletion is permitted only when no live profile/job references the artifact and retention rules allow it.

## 2. VoiceProfile

### Purpose

VoiceProfile is the immutable domain snapshot used to resolve a short reference recording or a dedicated voice model. The conversion engine receives a validated profile ID and resolves content-addressed artifacts through an application-controlled storage service.

### Proposed schema

~~~json
{
  "schema_version": 1,
  "profile_id": "vp_01J...",
  "derived_from_profile_id": null,
  "display_name": "My voice",
  "mode": "reference",
  "status": "ready",
  "engine_identity": {
    "id": "local/provider-neutral-backend@1.2.3+config_sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    "provider": "provider-neutral",
    "backend": "backend-adapter",
    "version": "1.2.3",
    "config_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    "capabilities": ["reference-conditioned-conversion"]
  },
  "artifacts": [
    {
      "artifact_id": "sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
      "role": "voice_reference",
      "storage_locator": "managed-artifacts/sha256/01/0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
      "media_type": "audio/wav",
      "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
      "size_bytes": 123456
    }
  ],
  "provenance": {
    "status": "known",
    "source": "self_recorded",
    "details": null
  },
  "consent": {
    "status": "confirmed",
    "attestation_id": "consent_01J...",
    "statement_version": 1,
    "statement_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    "voice_subject": "self",
    "rights_basis": "self_recorded",
    "attested_by": "local-user",
    "attested_at": "2026-11-26T10:00:00Z"
  },
  "evaluation_records": [],
  "created_at": "2026-11-26T10:00:00Z"
}
~~~

### Field and lifecycle rules

| Field | Rule |
|---|---|
| `schema_version` | Required positive integer. |
| `profile_id` | Stable immutable opaque ID. |
| `derived_from_profile_id` | Optional predecessor profile ID; must not form cycles. |
| `mode` | Immutable enum: `reference`, `trained`, or `imported`. |
| `status` | `ready`, `broken`, `unverified`, or `tombstoned`. Eligibility is evaluated separately and fails closed. |
| `engine_identity.id` | Canonical provider/backend/version/config-hash identity. |
| `config_sha256` | Hash of canonicalized inference-relevant config and preprocessing settings. |
| `artifacts[].artifact_id` | Content identity, derived from SHA-256; immutable. |
| `storage_locator` | Private managed-storage locator only; never used as identity and never accepted from untrusted input without root containment checks. |
| `provenance.status` | `known` or `unknown`; unknown remains unknown until the user supplies evidence. |
| `consent.status` | `confirmed`, `unverified`, or `revoked`. Only confirmed is eligible. |
| `consent.statement_sha256` | Hash of the exact consent statement text shown to the user. |
| `evaluation_records` | Zero or more immutable structured records, each pinned to engine/analyser/metric/evaluation-set versions. |

Mode-specific artifact rules:
- `reference`: requires a `voice_reference` audio artifact and a backend that explicitly supports reference-conditioned/few-shot input.
- `trained`: requires a locally trained `voice_checkpoint`; optional retrieval index must be bound to that checkpoint and compatible engine identity.
- `imported`: requires a locally stored imported `voice_checkpoint`; optional retrieval index must be bound to it. Provenance and consent are independent and must not be inferred.

A standard RVC checkpoint belongs to `trained` or `imported`, never `reference`. A short recording is not a checkpoint.

### Artifact resolution

1. Resolve the exact content hash requested by the profile.
2. Locate only within approved managed storage.
3. Verify existence, byte size, and SHA-256 before use.
4. If absent or mismatched, mark the profile `broken`, return a typed error, and stop.
5. Never select another profile, newest model, or same-named file as a fallback.

### Consent and provenance

Consent attestations and revocations are append-only events. A new attestation creates a new profile snapshot or consent event linked to the profile; it never edits historical attestation content. The statement hash must match the exact text/version presented at attestation time.

Legacy imported checkpoints start with unknown provenance and unverified consent. They may be listed in the local model library for review, but conversion, sharing, and export actions must block until explicit user review resolves the required trust and rights state. Do not infer ownership from filenames, model cards, checkpoint metadata, or directory location.

### Structured quality record

Do not store `quality.score`. Store records shaped like:

~~~json
{
  "evaluation_id": "eval_01J...",
  "engine_identity": "provider/backend@1.2.3+config_sha256:...",
  "analyser_version": "vocal-analyser/0.1.0",
  "metric_implementation": "cover-metrics/0.1.0",
  "evaluation_set_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "metrics": {
    "f0_contour_correlation": {"value": 0.98, "coverage": 0.91, "status": "available"},
    "onset_error_median_ms": {"value": 2.1, "status": "available"},
    "onset_error_p95_ms": {"value": 5.2, "status": "available"},
    "vibrato_rate_delta_hz": {"value": 0.1, "coverage": 0.6, "status": "available"},
    "vibrato_depth_delta_cents": {"value": 2.0, "coverage": 0.6, "status": "available"},
    "rms_envelope_correlation": {"value": 0.97, "coverage": 0.99, "status": "available"},
    "phoneme_alignment_score": {"value": null, "status": "unavailable"}
  },
  "evaluated_at": "2026-11-26T10:00:00Z"
}
~~~

A metric record's status is `available`, `unavailable`, `failed`, or `low_confidence`. Never compare records with different engine/config, analyser, metric implementation, or evaluation-set identities without an explicit compatibility/re-evaluation step.

## 3. VocalPerformanceDescriptor

### Purpose

VocalPerformanceDescriptor is a backend-neutral analysis result for one separated source vocal. It describes measurable characteristics with per-component and per-frame confidence. It is not a MIDI transcription and does not imply that all expressive details can be recovered.

### Canonical time grid

All frame-based arrays use one canonical frame grid:
- `sample_rate_hz`: sample rate of the analysed, canonicalized waveform.
- `hop_samples`: integer hop in samples.
- `hop_seconds = hop_samples / sample_rate_hz`.
- `window_samples`: analysis window size in samples.
- `frame_origin`: fixed enum `centered`; frame i is centered at sample i × hop_samples relative to time zero, with documented padding at the boundaries.
- `n_frames`: explicit frame count, validated against duration and the canonical grid.
- Every frame-based array has exactly `n_frames` entries. If an extractor naturally emits a different grid, resample/interpolate it onto the canonical grid before serialization. Never store F0 and RMS on different implicit grids.

The first implementation should use one declared default hop/window in the analyser configuration (for example, 10 ms hop with a 40 ms window); the actual values are stored in every descriptor and pinned by analyser version. Do not infer frame origin from array length.

### Confidence and result-state taxonomy

Every analysis component and every frame-level estimate has:
- `status`: `available`, `unavailable`, `failed`, or `low_confidence`.
- `confidence`: nullable value in [0, 1] where meaningful.
- `reason`: stable machine-readable reason code when not available.

For F0, store per-frame voicing confidence separately from F0. For vibrato, confidence belongs to each detected segment and is not defined on non-sustained/non-vibrato regions. A single descriptor-wide confidence is prohibited.

Definitions:
- `unavailable`: not computed or not supported by this analysis configuration.
- `failed`: computation was attempted and errored.
- `low_confidence`: computation completed but did not meet its documented confidence threshold.
- `available`: computation completed and met the threshold.

A successfully analysed segment with no detected vibrato is represented as an available vibrato analysis with an empty segment list, not a zero-rate vibrato estimate.

### Proposed schema

~~~json
{
  "schema_version": 1,
  "descriptor_id": "vpd_01J...",
  "source_audio_artifact_id": "sha256:...",
  "separated_vocal_artifact_id": "sha256:...",
  "separation": {
    "engine_identity": "demucs@version+config_sha256:...",
    "quality_gate": "passed",
    "review_status": "listening_reviewed",
    "quality_metrics": {}
  },
  "audio": {
    "sample_rate_hz": 44100,
    "channels": 1,
    "duration_seconds": 0.03
  },
  "analysis": {
    "engine_identity": "vocal-analyser@0.1.0+config_sha256:...",
    "algorithm_version": "f0-vibrato-rms/1",
    "frame_grid": {
      "hop_samples": 441,
      "window_samples": 1764,
      "frame_origin": "centered",
      "n_frames": 3
    },
    "f0": {
      "status": "available",
      "reason": null,
      "raw_hz": [null, 220.0, 221.2],
      "corrected_hz": [null, 220.0, 221.2],
      "voiced_mask": [false, true, true],
      "voicing_confidence": [0.0, 0.97, 0.96],
      "octave_error_flags": [false, false, false]
    },
    "onsets": {
      "status": "available",
      "reason": null,
      "times_seconds": [0.42, 0.91],
      "confidence": [0.95, 0.91]
    },
    "vibrato": {
      "status": "available",
      "reason": null,
      "minimum_sustain_seconds": 0.5,
      "analysis_window_seconds": 0.8,
      "segments": [
        {
          "start_seconds": 1.1,
          "end_seconds": 1.8,
          "rate_hz": 5.4,
          "depth_cents_peak": 32.0,
          "confidence": 0.78
        }
      ]
    },
    "rms": {
      "status": "available",
      "reason": null,
      "values": [0.0, 0.12, 0.10]
    },
    "pause_map": {
      "status": "available",
      "reason": null,
      "intervals": []
    },
    "alignment": {
      "unit": "phoneme",
      "status": "unavailable",
      "reason": "no_reference_transcript_or_aligner",
      "segments": []
    }
  },
  "created_at": "2026-11-26T10:00:00Z"
}
~~~

### Field rules and determinism

- Artifact IDs are content-addressed references. The descriptor also records separation engine/model/config identity and the separation quality-gate result.
- F0 is stored in linear Hz, not log-Hz or cents. `raw_hz` preserves estimator output; `corrected_hz` is nullable when octave correction is not run or not confident. Preserve octave-error flags; never silently overwrite raw values.
- `voiced_mask` and `voicing_confidence` each have `n_frames` entries. Unvoiced frames have null F0 and false mask. Voiced frames require finite positive F0 and a documented voicing-confidence threshold.
- `octave_error_flags` has `n_frames` entries. Boundary/transition frames may be flagged; downstream metrics must define whether flagged frames are excluded.
- Onset times are sorted, finite, within duration, and each confidence value is in [0, 1].
- Vibrato is segment-level. The analyser version pins the estimator, window, minimum sustained duration, detrending, and confidence threshold. Rate is Hz; depth is peak cents. No segment means no reliable vibrato detected, not zero vibrato.
- RMS is a linear amplitude measure, not perceptual loudness. RMS values are resampled onto the canonical frame grid. If a future metric uses perceptual loudness, it must be separately named and define its weighting standard.
- Pause intervals are sorted, non-overlapping, and within duration. Their detection threshold and minimum duration are pinned in analyser config.
- Syllable/phoneme alignment is unavailable unless a real aligner and reference transcript/ground truth are supplied. M1 may report it as unavailable; it must not fabricate a score. Alignment segments, when available, carry token, start/end, and confidence.
- Every component has its own status/reason and confidence representation. Missing, failed, and low-confidence data are not interchangeable.
- Same input bytes plus same analyser build/config must produce the same descriptor within documented floating-point tolerance. M1 includes determinism tests and stores analyser/config hashes.

### Separation quality gate — M1 precondition

Before using separated vocals to establish analyser baselines, validate separation on the fixed M1 song set. Record per-track listening review and measurable bleed/artifact indicators. If separation fails the documented gate, mark that sample invalid for analyser/backend scoring; do not interpret leakage-driven F0, vibrato, or dynamics as source-performance truth.

## 4. Evaluation harness contract

The harness compares source and converted vocal descriptors produced with the same canonical frame grid and compatible analyser configuration. It reports per-song results, aggregate distributions, metric coverage, and excluded samples with reasons. Never collapse the suite into one opaque score or use duration-weighted averages that hide a single-song failure.

### Required metrics

| Metric | Definition |
|---|---|
| F0 contour correlation | Pearson correlation of log2-Hz or cents pitch values over frames voiced in both source and converted tracks, after documented alignment. Exclude unvoiced, octave-error-flagged, and low-confidence frames; report voiced coverage. Do not encode unvoiced as zero. |
| Onset timing error | Match onsets with a documented monotonic matching rule; report median and p95 absolute error in milliseconds, plus missed/extra onset counts. Do not use mean as the headline statistic. |
| Vibrato rate delta | Absolute difference in Hz for matched source vibrato segments that meet the pinned confidence and sustain requirements; report segment coverage. |
| Vibrato depth delta | Absolute difference in peak cents for those same matched segments; report coverage. |
| RMS envelope correlation | Correlation of time-aligned linear RMS envelopes on the canonical grid, with documented silence handling. Do not label this perceptual loudness. |
| Syllable/phoneme alignment | Unavailable unless both sides have compatible reference transcript/ground-truth alignment and a pinned aligner. M1 reports `unavailable` by default until those prerequisites exist. |

Every metric result carries `available`, `unavailable`, `failed`, or `low_confidence`, a reason, sample coverage, and pinned implementation identity.

### Baselines and discrimination

M1 requires two distinct baselines:

1. **Identity baseline:** compare the source vocal with the exact same audio as the converted input. This tests metric implementation, alignment, and serialization. It should be near the metric's theoretical identity result; deviations outside numerical tolerance indicate a harness defect.
2. **Discrimination baseline:** include deliberately perturbed pairs, at minimum a controlled pitch-shift case and a controlled timing-shift case. Include a mismatched/different-singer pair when the rights-cleared dataset permits it. The harness must detect these known degradations; if a bad pair scores as well as identity, the affected metric is not accepted.

The fixed evaluation set is small, rights-cleared, documented, and pinned by content hash. Each sample records separation review and source identity. Failed separation samples are excluded with a reason.

### Threshold derivation rule for M2

Do not choose arbitrary percentage tolerances before M1 data exists.

For each metric:
1. Run repeated identity comparisons to establish its numerical/repeatability distribution.
2. Run the controlled perturbation and mismatch baselines to establish whether the metric discriminates known degradation.
3. Obtain blinded human ratings for a documented subset of candidate converted pairs, using a pre-agreed acceptable/unacceptable rubric.
4. Set a metric-specific acceptance boundary from the human-rated acceptable set while requiring separation from the bad-baseline distribution. Record the selected operating point, false-accept/false-reject trade-off, sample count, and confidence interval.
5. If acceptable and bad distributions overlap too much to support a defensible threshold, do not invent one. Expand the evaluation set or mark that metric as advisory pending more evidence.

M2 acceptance is per-song and per-metric. An aggregate pass cannot hide a catastrophic individual song failure. Listening review remains mandatory for final acceptance.

### Version pinning and stale results

Every evaluation report pins:
- Engine identity and inference config hash.
- Analyser build/version and config hash.
- Metric implementation version and config hash.
- Evaluation-set manifest hash.
- Source/converted artifact hashes.

Any change to one of these identities makes previous results stale for current comparisons. Preserve historical reports, mark them stale, and require re-evaluation; never silently compare results across versions.

## 5. Migration from existing RVC .pth imports

Existing imported RVC checkpoints map to `mode: "imported"`; checkpoints trained through the app map to `mode: "trained"`.

Migration requirements:
1. Preserve existing model files and current import/trust behavior.
2. Create a stable profile ID and content-addressed checkpoint artifact reference with SHA-256 and byte size.
3. Set legacy imported model provenance to `unknown` unless independently evidenced.
4. Set consent to `unverified`; do not infer voice ownership or rights from filename, model card, checkpoint metadata, or folder.
5. Keep the profile visible for review but block conversion, sharing, and export until trust and rights requirements are explicitly resolved.
6. Preserve existing checkpoint quarantine/preflight/trust acknowledgement. Unknown provenance does not mean safe.
7. Make migration idempotent and transactional. Re-running it must not duplicate profiles or modify model bytes.
8. Keep the legacy registry readable until migration verification succeeds; record a backup/checkpoint and rollback procedure.
9. Do not automatically downgrade. Restore the pre-migration backup if rollback is required.
10. Tombstone deleted profiles and remove artifacts only when reference counts show no remaining profile/job references and retention rules permit deletion.

## 6. M1 definition of done

M1 — Performance Contract & Analyser is complete only when:

- VoiceProfile schema tests cover immutable modes, derived-profile semantics, versioned engine identity, content-addressed artifact references, broken/missing artifact fail-closed behavior, append-only consent, structured quality records, and tombstones.
- Existing imported .pth models migrate to `mode: "imported"` with unknown provenance and unverified consent; migration is idempotent, transactional, and rollback-tested.
- The analyser runs on the fixed, rights-cleared song set whose separation has passed the documented quality gate.
- Descriptors use the canonical frame grid, per-component/per-frame confidence and status taxonomy, explicit F0 hygiene, segment-level vibrato, and version/config identity.
- Descriptor serialization round-trips and same-input determinism tests pass within documented tolerance.
- The harness reports identity and discrimination baselines, all required metrics, coverage, per-song results, aggregate distributions, and exclusions.
- Syllable/phoneme alignment is reported unavailable unless real ground truth and an aligner are provided.
- No conversion backend is selected or required to close M1.

M2 — Backend Integration & Preservation Validation consumes these contracts. It evaluates short-reference candidates against the same harness, wires RVC through trained/imported profiles, derives metric-specific thresholds using the stated calibration rule, then validates converted performance and mixing with the original instrumental.
