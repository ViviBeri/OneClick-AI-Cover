# Voice input and performance-preserving replacement

## Product requirement

OneClick AI Cover replaces the original singer's vocal identity while retaining the original song's vocal performance as closely as the selected conversion backend allows.

The user supplies an original song and their own voice recording or a dedicated voice model they are authorized to use. The expected result is the original instrumental with a converted vocal performed in the target user's voice.

This is not simply voice cloning from a short clip and not merely separating and replacing a vocal with a newly generated melody.

## Voice-input modes

### Short voice recording

Intended for beginners. The user records or uploads a clean voice reference. The application validates the recording and sends it to a compatible reference-conditioned/few-shot conversion backend.

Validation includes supported file type and decoding, duration and usable voiced content, sample rate and channel layout, clipping, silence, noise, excessive reverb, and user confirmation of voice ownership or permission.

A short recording must not be passed to standard RVC inference as if it were a trained RVC checkpoint. If no compatible short-reference backend is installed and verified, the application must explain that a dedicated model is required.

### Dedicated personal voice model

Intended for users who want repeatable results. Users prepare a larger single-speaker dataset, train a compatible model using the current experimental RVC bridge or a future integrated trainer, and import the inference-ready checkpoint. A matching retrieval index is optional and must be associated with the correct checkpoint.

The app must retain model quarantine, checkpoint preflight, explicit trust acknowledgement, provenance, and local-only storage.

## Delivery sequence

The engine work is split into two independently scoped milestones. **M1 — Performance Contract & Analyser** defines the backend-neutral VoiceProfile and VocalPerformanceDescriptor contracts, validates source-separation quality, implements analysis and the identity-baseline harness, and migrates existing imported RVC checkpoints. **M2 — Backend Integration & Preservation Validation** evaluates short-reference backends, integrates RVC through VoiceProfile, derives acceptance thresholds from M1 results, and validates final mixing. See [ENGINE_CONTRACTS.md](ENGINE_CONTRACTS.md) for schemas and exit criteria.

Source-separation quality is a precondition: samples that fail the documented separation gate must not be used to establish F0, vibrato, or dynamics baselines.

## Performance analysis

The original vocal is the performance reference. Extract, where technically reliable:
- Fundamental-frequency contour and note transitions.
- Note onsets, offsets, durations, and phrase boundaries.
- Vibrato rate and depth, plus amplitude-modulation (tremolo) rate and depth where measurable.
- Pitch bends and slides.
- Loudness/dynamics envelope.
- Pauses, syllable timing, and lyric alignment where supported.

Use the analysis as guidance for conversion and measurable quality-control data. Report confidence and backend limitations. Do not claim perfect preservation if the selected model cannot condition on or reproduce a particular attribute.

## Processing sequence

1. Validate and decode the original song.
2. Separate original vocal and instrumental.
3. Analyse the original vocal performance.
4. Resolve and validate the target voice from either supported input mode.
5. Convert the source vocal into the target voice using a compatible backend.
6. Align and quality-check the converted vocal against the source performance.
7. Mix the converted vocal with the untouched original instrumental.
8. Preview and export WAV or MP3.

Keep the original separated vocal as a non-destructive reference. Never overwrite it with the converted output.

## Quality checks

At minimum, validate output duration and phrase timing, pitch contour and note-transition consistency, vibrato and amplitude-modulation rate/depth where measurable, loudness and dynamics, clipping, silence, discontinuities, conversion artefacts, and sample-rate/channel compatibility before mixing.

Automated metrics must be supplemented by listening tests. A high similarity score alone is not proof of a natural-sounding result.

## Acceptance tests

- A short-reference recording is accepted only by a backend explicitly supporting that input mode.
- A dedicated voice checkpoint passes format, compatibility, provenance, and trust checks before inference.
- Both modes submit jobs through the same target-voice contract.
- The source vocal and instrumental are retained separately.
- The output vocal follows the source performance's timing and pitch contour within documented backend tolerances.
- Vibrato and dynamics are measured and reported where supported.
- The final mix uses the original instrumental and converted vocal.
- WAV and MP3 exports are playable and have plausible duration.
- No source song, voice sample, checkpoint, or generated audio is uploaded in local mode.
- Tests and documentation do not claim exact performance preservation without real inference and listening evidence.

## Safety and rights

Use only voices and source audio the user owns or has explicit permission to use. Do not facilitate deceptive impersonation or non-consensual voice cloning. Keep all recordings and models local by default, and require explicit consent before any future remote processing.
