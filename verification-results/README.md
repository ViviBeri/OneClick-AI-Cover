# Verification results index

Use this index to find completed clean-machine and end-to-end verification runs. Only add a row when a tester has actually performed the checks and attached the report. Keep pending or planned runs in the GitHub issues, not in this results table.

| Date (UTC) | Tester | Windows edition/version/build | Architecture | Scope | Result | Report / evidence |
|---|---|---|---|---|---|---|
| — | — | — | — | No completed manual verification reports recorded yet | PENDING | [Verification plan](../docs/verification.md) |

## Recording a result

1. Copy [`TEMPLATE.md`](TEMPLATE.md) to a new report filename that includes the date and test scope.
2. Fill in every applicable field; use PASS, FAIL, BLOCKED, or NOT TESTED consistently.
3. Record the exact tested artifact's SHA-256. If no official checksum is published, say so; the local hash identifies the artifact but does not prove publisher authenticity.
4. Link sanitized evidence only. Never commit copyrighted audio, voice recordings, private voice models, generated media, credentials, or private paths.
5. Add the completed report to the table above and link it from the related GitHub issue.

A maintainer self-test must be labeled as such. Do not describe it as independent testing. See the [verified issue closure criteria](../docs/verification.md#verified-issue-closure-record).
