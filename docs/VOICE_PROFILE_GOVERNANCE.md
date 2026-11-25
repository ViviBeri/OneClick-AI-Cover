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

1. Write the profile tombstone and deletion event immediately when `consent_withdrawn` is accepted. Block new conversions and exports immediately; lock app-managed existing outputs immediately.
2. Physically delete eligible app-managed artifacts only when their valid-reference count is zero, the 7-calendar-day grace period has elapsed, and no legal/audit hold applies.

The grace period is a distinct clock: `grace_period_days = 7`. It is an undo window before physical deletion, not a backup-retention or audit-retention period. A scheduled orphan sweep must find artifacts with zero valid references and delete eligible artifacts after this grace period. Both tombstoning and physical deletion must be safe to retry.

If profile B derives from profile A and A is erased, A's deletion must not be blocked. Preserve the lineage edge in the audit record as `ancestor_deleted`, including A's profile ID and deletion-event reference. Do not retain A's erased voice payload.

## Retention clocks

These are three independent policies. Never reuse one duration for another.

| Clock | Current policy | Meaning |
|---|---|---|
| Grace period | 7 calendar days | Delay between tombstoning and physical deletion of eligible app-managed artifacts |
| App-managed backup retention | 0 days; `not_applicable` | The current repository has no identified application-managed backup/rotation subsystem. The app makes no backup-retention guarantee because it does not manage these backups. |
| Minimum audit metadata retention | Indefinite until explicit purge | Retain only the closed minimum audit set below; this metadata is exempt from `consent_withdrawn` artifact erasure and is not a backup copy of voice data |

**Backup implementation gate:** A future app-managed backup feature must specify backup scope, encryption, rotation schedule, deletion propagation and a hard maximum retention bound before it can advertise a retention window. If introduced and verified, the backup-retention setting may be changed from `0 / not_applicable` to a bounded value. A 30-calendar-day ceiling is a candidate only after rotation enforces it; it is not the current policy.

OS-level backups, filesystem snapshots, device images and external/cloud backup products are outside the application's control and retention guarantee. The UI and contract must say this plainly.

## User-facing erasure statement

On `consent_withdrawn`, the application must state:

> New conversions and exports from this profile are blocked immediately, and app-managed existing outputs are locked immediately. Eligible app-managed audio and model artifacts are physically removed after the 7-day grace period, provided no other valid profile references them and no legal/audit hold applies. The application does not manage OS-level or external backups, so it cannot promise deletion from those copies. Files previously exported or copied outside the application cannot be revoked or erased by this app.

Do not describe this as instant erasure. If an artifact remains because another valid profile references it or a legal/audit hold applies, disclose that status rather than claiming deletion is complete.

## Enforcement boundary

Enforce consent and profile state in the service layer immediately before conversion and export. UI state alone is not an authorization boundary. Every state transition, tombstone, deletion attempt and orphan-sweep operation must be auditable and idempotent.
