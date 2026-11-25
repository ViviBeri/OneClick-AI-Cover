# VoiceProfile Implementation Decisions (M1 Step 1)

**Status:** Architecture decisions pinned for implementation. This document specifies behavior; it does not claim that the implementation or tests already exist.

## 1. Canonical serialization and hashing

Use RFC 8785 JSON Canonicalization Scheme (JCS) for every hash of a structured JSON record, including VoiceProfile snapshots, consent event payloads, manifests and canonical consent statement documents.

- Encode canonical output as UTF-8 without a byte-order mark.
- Apply RFC 8785 property ordering and ECMAScript-compatible number serialization; do not implement a local approximation.
- Reject non-finite numbers (NaN, positive/negative infinity), invalid Unicode and values outside the JCS/I-JSON constraints.
- Identity-bearing schemas must avoid floating-point values where an integer, decimal string or fixed-point representation is suitable.
- Hash the exact canonical UTF-8 bytes with SHA-256 and prefix identifiers with the algorithm, for example sha256:<lowercase-hex>.
- Audio/model artifact hashes are different: SHA-256 is computed over the exact raw artifact bytes, not a serialized descriptor.

Canonicalization and hash test vectors must be committed and verified across supported Windows/Python environments before persisted IDs are relied upon.

## 2. Legacy artifact handling: reference in place

Legacy .pth imports are non-destructive and reference the original file in place.

- Import records the resolved path, byte size and SHA-256 observed at import.
- Every artifact resolution rechecks existence, size and hash. Missing artifacts fail closed with a distinct ArtifactMissingError; changed bytes fail closed with ArtifactIntegrityError.
- Moving or deleting the source file therefore makes the profile unavailable; the resolver must not search for a substitute.
- “Adopt into managed store” is a separate explicit user action. Adoption copies to a temporary content-addressed destination, verifies the copied hash and size, atomically publishes it, then updates the profile reference. It never deletes or moves the original file.
- Failed adoption leaves the original reference and source file untouched.

## 3. Legacy consent timing

Legacy imports are migrated non-interactively as mode=imported, with unknown provenance and unverified consent.

- Migration does not prompt for consent and does not block the migration UI.
- Unverified profiles remain visible but cannot be used for conversion, export or sharing.
- On the first attempted conversion, explain the rights/consent statement and collect an explicit attestation. Declining or dismissing leaves the profile blocked.
- The attestation is an append-only event tied to the canonical statement hash and version. Do not infer consent from file ownership or import location.

## 4. Store location and portability

The default managed store root on Windows is:

%LOCALAPPDATA%\\OneClickAICover\\store\\

- The store is pinned to its configured absolute root; profile records use logical artifact IDs, not machine-specific paths.
- The root may be changed only through an explicit application-managed relocation operation that validates all artifact hashes, writes a migration journal, atomically switches the configured root, and supports rollback.
- No automatic discovery of moved stores and no silent fallback to repository-relative paths.
- OS-level backups and external/cloud backups remain outside the application's retention guarantees, as defined in VOICE_PROFILE_GOVERNANCE.md.

## 5. Schema version floor

Every persisted record has an integer schema_version. A reader supports a declared version range and must reject any payload whose version is newer than its maximum supported version with a typed UnsupportedSchemaVersionError. It must not partially load, downgrade, ignore unknown fields or rewrite the payload.

A mandatory test constructs a valid synthetic payload with schema_version = CURRENT_SCHEMA_VERSION + 1 and asserts that the current reader rejects it with the typed error and leaves the original bytes unchanged.

## 6. Implementation order and gates

Do not start persistence or legacy migration until the preceding pure-logic layer's tests pass.

1. Schema, validator and canonical serialization. No persistence.
2. Lineage DAG, cycle rejection and deterministic deduplication. In-memory only.
3. Append-only consent event log and deterministic state folding. Pure logic.
4. Content-addressed artifact store and reference counting. Must pass tombstone/reference and concurrency tests.
5. Persistence and forward-only transactional migrations, including rollback.
6. Legacy .pth migration with mandatory dry-run mode. Dry-run reports planned profile records, artifact references, conflicts and blocked consent state; it performs no writes or file moves.

## 7. Required negative and invariance tests

- Canonical serialization round-trip and hash stability across repeated runs and supported platforms, using shared RFC 8785 test vectors.
- Reject invalid/non-finite numeric values and unsupported Unicode inputs.
- Reject cyclic lineage at write time, including A -> B -> A.
- Deterministic duplicate handling: identical artifact hash, engine identity and canonical consent statement resolve to one profile identity or return an explicit duplicate result; never create an accidental second profile.
- Missing artifact fails closed with ArtifactMissingError.
- Hash mismatch fails closed with ArtifactIntegrityError, distinct from missing.
- Newer schema payload fails closed with UnsupportedSchemaVersionError.
- Two concurrent processes cannot corrupt artifact reference counts or publish partial artifacts; use process-safe locking or transactional database constraints.
- Tombstoned, consent-withdrawn or pending-deletion profiles do not hold valid artifact references.
- Orphan sweep is idempotent: a second run does not delete additional artifacts unless state changed between runs.
- Failed migration leaves the managed store byte-identical to its pre-migration state and preserves all original .pth files.
- Adoption failure preserves the source file and prior profile reference.
- Dry-run migration performs no writes and is repeatable with identical output for identical inputs.

## 8. Explicit implementation boundary

M1 Step 1 is backend-independent. It must not import, initialize or require RVC, Demucs, a short-reference model, CUDA or a remote service. Backend selection and conversion evaluation remain later phases.

The migration and persistence implementation is not complete until the tests above pass in CI. Documentation approval is not evidence of runtime correctness.
