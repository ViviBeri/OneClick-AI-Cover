# Supabase integration

## Role in OneClick AI Cover

Supabase is the optional cloud account and metadata layer. It does not run Demucs or RVC and is not required to use the local application.

- **Auth:** user identity for future multi-device access.
- **Postgres:** profiles, project names, and processing-job metadata.
- **Realtime:** optional job-status synchronization between signed-in clients.
- **Storage:** deliberately not enabled by this foundation. Audio, stems, datasets, and voice checkpoints remain local unless a later, explicit upload feature is designed and approved.

The local Python job runner remains the source of truth for inference execution. Supabase records are a cloud history/synchronization copy, not a remote process controller.

## Database foundation

The migration at `supabase/migrations/202611130001_initial_cloud_metadata.sql` creates:

| Table | Purpose |
|---|---|
| `profiles` | User display name linked to `auth.users` |
| `projects` | User-owned project labels |
| `processing_jobs` | User-owned job history and status metadata |

All three tables have Row Level Security enabled. Policies scope rows to `auth.uid()`. The migration revokes broad table privileges before granting the specific operations required by authenticated users.

Job history stores the local job identifier, state, progress, message, and optional output filename only. It must never store an absolute local path, source audio, vocal stems, model checkpoint bytes, or authentication tokens.

## Web client

The first browser client lives in `web/` and provides email/password sign-in, project management, job-history viewing, and Realtime refreshes. It is a metadata dashboard only; it does not yet control the local processing engine.

Run it locally:

```bash
cd web
npm install
cp .env.example .env.local
# Set VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY in .env.local
npm run dev
```

Apply the database migration before signing in. The client uses the publishable key and the signed-in user session; Row Level Security remains the authorization boundary. Do not deploy the browser client with a secret/service-role key.

## Setup

1. Create a Supabase project in the Supabase dashboard.
2. Open the project's SQL/migrations workflow and apply the migration in `supabase/migrations/`.
3. Enable the sign-in providers that the product actually supports; start with email/password.
4. Keep the project URL and publishable key in client configuration only. The publishable key is not an authorization mechanism; RLS is.
5. Never place a secret key or legacy `service_role` key in the browser, desktop package, repository, or `.env.example`.
6. Verify with two separate test accounts that each user can read and change only their own profile, projects, and jobs. Also verify that anonymous requests cannot read or write these tables.
7. Verify the `processing_jobs` table is enabled for Realtime before enabling client subscriptions.

No Supabase project credentials are required to run local mode. Do not add live credentials to GitHub Actions.

## Security boundaries

- Local processing stays on the user's machine and continues to work without Supabase.
- Do not upload audio, stems, voice recordings, training datasets, or model checkpoints automatically.
- Do not store filesystem paths in cloud job records.
- Use the signed-in user's access token with the publishable key for client operations; rely on RLS for row isolation.
- Any future privileged server operation must run in a trusted backend and keep the secret/service-role key in a server-only secret store.
- The local API's per-launch bearer token is separate from Supabase user authentication. Never reuse it as a Supabase credential.
- A Supabase job record does not authorize access to a local PC. Remote device control needs a separate pairing protocol, device identity, short-lived credentials, explicit user approval, and an outbound secure connection.
- Storage buckets must be private and have their own object-level RLS policies before an upload/download feature is introduced.

## Implementation sequence

1. Apply and test this schema foundation.
2. Add a Supabase client to the future browser/PWA frontend, not to the Gradio inference process.
3. Implement sign-in and session handling.
4. Add a metadata sync adapter that mirrors local job state after the user opts in.
5. Add Realtime subscriptions scoped to the signed-in user's rows.
6. Design private Storage uploads only after explicit consent, retention, deletion, quota, and cost controls exist.
7. Add secure PC pairing for remote control; never expose the loopback API to the internet.

## References

- [Supabase architecture](https://supabase.com/docs/guides/getting-started/architecture)
- [Supabase Auth architecture](https://supabase.com/docs/guides/auth/architecture)
- [Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security)
- [Secure data](https://supabase.com/docs/guides/database/secure-data)
- [Realtime authorization](https://supabase.com/docs/guides/realtime/authorization)
