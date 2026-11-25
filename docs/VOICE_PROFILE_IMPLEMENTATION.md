# VoiceProfile Implementation Decisions (M1)

**Status:** Architecture decisions pinned for implementation. This document specifies behavior; it does not claim that the implementation or tests already exist.

## 1. Canonical serialization and hashing

Use a conforming RFC 8785 JSON Canonicalization Scheme (JCS) implementation for every hash of a structured JSON record, including VoiceProfile snapshots, consent event payloads, manifests and canonical consent statement documents.

- Use a maintained, pinned JCS library (the initial candidate is the pure-Python `rfc8785` implementation). Pin its exact version in the project dependency manifest and include the canonicalizer/library identity and version in the relevant analyser/persistence configuration identity. Do not silently upgrade it.
- Encode canonical output as UTF-8 without a byte-order mark.
- Apply RFC 8785 property ordering and ECMAScript-compatible number serialization; do not implement a local approximation.
- Do not substitute `json.dumps(sort_keys=True)`; it is not an RFC 8785 implementation.
- Reject non-finite numbers (NaN, positive/negative infinity), invalid Unicode and values outside the JCS/I-JSON constraints.
- Hash canonical UTF-8 bytes with SHA-256. All textual SHA-256 digests used in identifiers or cross-implementation comparisons are lowercase hexadecimal, prefixed with the algorithm, for example `sha256:<lowercase-hex>`.
- Audio/model artifact hashes are different: SHA-256 is computed over the exact raw artifact bytes, not a serialized descriptor.

### Hashed-payload discipline

The following rules are schema-level requirements, not optional serializer preferences:

- **No floating-point fields for measured values.** Quality scores, confidence values, durations and other derived measurements use validated decimal strings with a documented scale/format (for example `"0.8734"`), or an explicitly specified integer/fixed-point unit. Do not accept Python float, NumPy floating scalar or Decimal interchangeably at the boundary.
- **Timestamps are integer milliseconds since Unix epoch.** Consent events, tombstones and other timestamped records use integer epoch milliseconds. Reject booleans, floats and RFC 3339/date-time strings before canonicalization. Define the timestamp field names and units in each schema.
- **Field names are canonical and exact.** Do not hash aliases. If a compatibility boundary accepts an alias, normalize it to the one canonical field name before validation and canonicalization; reject ambiguous payloads containing both names.
- **Array order is explicit.** JCS does not sort arrays. Define ordering for lineage edges, consent events and artifact references in each schema. Sort set-derived collections by a documented stable key before constructing the record; preserve order only where order is semantically meaningful.
- **No implicit normalization.** Do not silently normalize strings, Unicode, paths, timestamps or numeric values during hashing. Normalize and validate at the schema boundary, then hash the resulting canonical record.

### Canonicalization conformance tests

- Include at least one published RFC 8785/JCS conformance vector. Assert the exact canonical UTF-8 bytes against the published expected output and assert the SHA-256 digest against a fixed expected lowercase-hex value; do not calculate the expected value using the implementation under test.
- Cover representative number serialization, Unicode/property ordering, escaped strings, invalid Unicode and rejection of non-finite values.
- Assert canonical output is UTF-8 without BOM and that the digest is lowercase hexadecimal.
- Assert equivalent accepted inputs normalize to the same canonical field names and array ordering before hashing.
- Run the same vectors across supported Windows/Python environments before persisted IDs are relied upon.

## 2. Legacy artifact handling: reference in place

Legacy .pth imports are non-destructive and reference the original file in place.

- Import records the resolved path, byte size and SHA-256 observed at import.
- Every artifact resolution rechecks existence, size and hash. Missing artifacts fail closed with a distinct `ArtifactMissingError`; changed bytes fail closed with `ArtifactIntegrityError`.
- Moving or deleting the source file therefore makes the profile unavailable; the resolver must not search for a substitute.
- “Adopt into managed store” is a separate explicit user action. Adoption copies to a temporary content-addressed destination, verifies the copied hash and size, atomically publishes it, then updates the profile reference. It never deletes or moves the original file.
- Failed adoption leaves the original reference and source file untouched.

## 3. Legacy consent timing

Legacy imports are migrated non-interactively as `mode=imported`, with unknown provenance and unverified consent.

- Migration does not prompt for consent and does not block the migration UI.
- Unverified profiles remain visible but cannot be used for conversion, export or sharing.
- On the first attempted conversion, explain the rights/consent statement and collect an explicit attestation. Declining or dismissing leaves the profile blocked.
- The attestation is an append-only event tied to the canonical statement hash and version. Do not infer consent from file ownership or import location.

## 4. Store location and portability

The default managed store root on Windows is:

`%LOCALAPPDATA%\\OneClickAICover\\store\\`

- The store is pinned to its configured absolute root; profile records use logical artifact IDs, not machine-specific paths.
- The root may be changed only through an explicit application-managed relocation operation that validates all artifact hashes, writes a migration journal, atomically switches the configured root, and supports rollback.
- No automatic discovery of moved stores and no silent fallback to repository-relative paths.
- OS-level backups and external/cloud backups remain outside the application's retention guarantees, as defined in `VOICE_PROFILE_GOVERNANCE.md`.

## 5. Content-addressed store durability and reference events

The content-addressed store must not treat a successful rename as proof of durable publication.

- Create scratch files in the target artifact's store directory, as siblings of the final target. Never use the system temporary directory for publication. The scratch file and final artifact must be on the same filesystem/volume; detect and reject a cross-volume publication path.
- Write the complete artifact, flush userspace buffers and call `fsync` on the file before publication.
- Publish with a same-filesystem atomic replacement primitive whose Windows behavior and guarantees are explicitly documented and tested. Do not assume that `os.replace` alone provides crash durability on Windows.
- After publication, flush the containing directory/metadata using the supported platform-specific durability mechanism. On Windows, use a tested Win32 durability strategy (including `FlushFileBuffers` where supported) or a maintained library with documented guarantees. Do not claim POSIX directory-fsync semantics where Windows does not provide them.
- If the platform cannot provide the required durability guarantee, fail closed or report the explicitly defined weaker guarantee; never publish a valid-looking content hash reference to an unverified or partial artifact.
- Verify the final artifact's byte length and SHA-256 after publication before committing its reference.

Reference counts are derived from an **append-only artifact-reference event log**, not maintained as an independently mutable counter file.

- Record link and unlink events with stable event IDs, artifact IDs, profile IDs and integer epoch-millisecond timestamps.
- Derive current counts by deterministic folding of the validated event stream; duplicate event IDs are idempotent and invalid transitions are rejected.
- Serialize event appends across processes using a cross-platform process lock or transactional append mechanism. Append-only does not remove the need to prevent interleaved or lost writes.
- Tombstoned or otherwise ineligible profiles contribute no live references according to the defined state fold. Orphan collection operates on the folded state and is idempotent.

## 6. Schema version floor

Every persisted record has an integer `schema_version`. Decode only the minimal version probe first, validate that it is a genuine integer (not a boolean), and compare it with the reader's supported range before parsing the full record or running migrations.

- If `schema_version > CURRENT_SCHEMA_VERSION`, reject with typed `UnsupportedSchemaVersionError`.
- If `schema_version < MIN_SUPPORTED_SCHEMA_VERSION`, or the version is missing, zero, non-integer or otherwise invalid, reject with typed `UnsupportedSchemaVersionError` (or a documented typed invalid-version subtype).
- Only supported older versions may enter the explicit forward-only migration chain. Never partially load, downgrade, ignore unknown fields or rewrite an unsupported payload.

Three mandatory schema-floor tests:

1. A synthetic payload with `schema_version = CURRENT_SCHEMA_VERSION + 1` is rejected with the typed newer-version error, not a generic parse error.
2. Synthetic payloads with `schema_version = 0` and with the field missing are rejected with the typed invalid/unsupported-version error.
3. A valid payload at `CURRENT_SCHEMA_VERSION` round-trips byte-identically after canonical serialization. The original bytes remain unchanged on rejection.

## 7. Implementation order and gates

The sequence below is mandatory. Do not allow the canonicalization layer and the content-addressed store to meet until the canonicalization conformance tests pass. Do not begin legacy migration until the store's reference-event and transactional invariants pass.

1. **Canonical serialization wrapper** around the pinned JCS library, with published conformance vectors and all canonicalization tests. Nothing else depends on this until it passes.
2. **Schema and validator**, with field-level decimal-string/fixed-point decisions, integer-millisecond timestamps, exact field names and explicit array ordering.
3. **Lineage DAG, cycle rejection and deterministic deduplication.** In-memory pure logic.
4. **Append-only consent event log and deterministic state folding.** In-memory pure logic.
5. **Persistence and schema floor**, with forward-only migrations and the three schema-floor tests.
6. **Content-addressed artifact store and reference-event folding**, including same-volume Windows publication, crash durability, process-safe event appends, reference counts and orphan collection.
7. **Legacy .pth migration**, with mandatory dry-run mode. Dry-run reports planned profile records, artifact references, conflicts and blocked consent state; it performs no writes or file moves.

## 8. Required negative and invariance tests

- Published JCS conformance vector: exact canonical bytes and independently fixed expected lowercase SHA-256 digest.
- Canonical serialization round-trip and hash stability across repeated runs and supported platforms.
- Reject invalid/non-finite numeric values, invalid Unicode and unsupported I-JSON inputs.
- Reject float-valued score/confidence/duration fields and non-integer timestamp inputs before canonicalization.
- Verify canonical aliases normalize to one field name; reject ambiguous alias-plus-canonical input.
- Verify set-derived arrays are sorted by their schema-defined stable key.
- Verify UTF-8 without BOM and lowercase SHA-256 hexadecimal output.
- Reject cyclic lineage at write time, including A -> B -> A.
- Deterministic duplicate handling: identical artifact hash, engine identity and canonical consent statement resolve to one profile identity or return an explicit duplicate result; never create an accidental second profile.
- Missing artifact fails closed with `ArtifactMissingError`.
- Hash mismatch fails closed with `ArtifactIntegrityError`, distinct from missing.
- Newer schema payload fails closed with `UnsupportedSchemaVersionError`; zero and missing versions are rejected; current-version canonical round-trip is byte-identical.
- Scratch and target paths are siblings on the same volume; cross-volume publication is rejected.
- Injected write/flush/replace failures never publish a reference to a partial artifact.
- Two concurrent processes cannot interleave or lose artifact-reference events or derive corrupted counts.
- Tombstoned, consent-withdrawn or pending-deletion profiles do not hold valid artifact references.
- Orphan sweep is idempotent: a second run does not delete additional artifacts unless state changed between runs.
- Failed migration leaves the managed store byte-identical to its pre-migration state and preserves all original .pth files.
- Adoption failure preserves the source file and prior profile reference.
- Dry-run migration performs no writes and is repeatable with identical output for identical inputs.

## 9. Explicit implementation boundary

The first M1 implementation stage is backend-independent. It must not import, initialize or require RVC, Demucs, a short-reference model, CUDA or a remote service. Backend selection and conversion evaluation remain later phases.

The implementation is not complete until the applicable tests above pass in CI. Documentation approval is not evidence of runtime correctness.
