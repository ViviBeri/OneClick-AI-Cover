# Voice Profile Revocation and Erasure Policy

**Status:** M1 contract decision — approved semantics; backup-retention duration remains a release decision.

## Revocation events

Events are append-only. Current profile state is derived by folding the complete event log in timestamp/order sequence; prior events are never overwritten.

| Event | Blocks new conversions | Blocks new exports from profile | Locks app-managed existing outputs | Starts erasure |
|---|---:|---:|---:|---:|
| `use_revoked` | Yes | Yes | No | No |
| `consent_withdrawn` | Yes | Yes | Yes | Yes |

The UI's default action for the voice owner withdrawing consent is `consent_withdrawn`. Offer `use_revoked` separately as the narrower “stop using this profile for new work” action.

Revocation is local-first self-governance: it protects the voice owner from future use by the application. It is not enforcement against a hostile user or external party.

## Closed minimum audit record after erasure

Retain exactly:

- For each deleted artifact: `profile_id`, `artifact_sha256`, and byte size.
- The complete consent, revocation and deletion event log for the profile: event type, timestamp, actor and reason code.
- Consent statement hash and canonical statement document version. Do not retain freeform statement text.
- Lineage edges, including `ancestor_deleted` markers.
- Tombstone record and deletion timestamp.

Do not retain audio, embeddings, voice features, model weights or consent audio recordings. The audit record must not become a recoverable copy of erased voice data. No additional profile payload is retained after erasure.

## Artifact references and deletion

A **valid reference** is a reference held by a profile that is not tombstoned, not consent-withdrawn and not itself pending deletion. Tombstoned profiles do not count as references.

Deletion is two-stage and idempotent:

1. Write the profile tombstone and deletion event.
2. Physically delete an artifact only when its valid-reference count is zero, the configured grace period has elapsed, and no legal/audit hold applies.

A scheduled orphan sweep must find artifacts with zero valid references and delete eligible artifacts after the grace period. Both tombstoning and physical deletion must be safe to retry.

If profile B derives from profile A and A is erased, A's deletion must not be blocked. Preserve the lineage edge in the audit record as `ancestor_deleted`, including A's profile ID and deletion-event reference. Do not retain A's erased voice payload.

## Backups and external exports

Backup retention must be an explicit, versioned product configuration. Erasure from backups cannot be promised before that retention window expires; the UI and contract must disclose the actual configured duration. **Release gate:** choose and publish the retention duration before shipping erasure functionality. Proposed default for review: 30 calendar days.

External copies are out of scope. The application can lock app-managed outputs, but cannot revoke or erase a WAV that a user has already exported and copied elsewhere. State this limitation in both the consent matrix and UI.

## Enforcement boundary

Enforce consent and profile state in the service layer immediately before conversion and export. UI state alone is not an authorization boundary. Every state transition, tombstone, deletion attempt and orphan-sweep operation must be auditable and idempotent.
