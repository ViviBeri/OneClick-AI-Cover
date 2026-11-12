-- Supabase cloud metadata foundation for OneClick AI Cover.
-- Audio, stems, model checkpoints, and local filesystem paths are deliberately excluded.

create table if not exists public.profiles (
    id uuid primary key references auth.users (id) on delete cascade,
    display_name text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.projects (
    id uuid primary key default gen_random_uuid(),
    owner_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
    name text not null check (char_length(trim(name)) between 1 and 120),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (id, owner_id)
);

create table if not exists public.processing_jobs (
    id uuid primary key default gen_random_uuid(),
    owner_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
    project_id uuid,
    local_job_id text not null check (char_length(local_job_id) between 1 and 64),
    status text not null default 'queued'
        check (status in ('queued', 'running', 'completed', 'failed', 'cancelled')),
    progress numeric(5, 4) not null default 0
        check (progress >= 0 and progress <= 1),
    message text not null default 'Waiting to start'
        check (char_length(message) <= 500),
    output_filename text
        check (output_filename is null or char_length(output_filename) <= 255),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (owner_id, local_job_id),
    foreign key (project_id, owner_id)
        references public.projects (id, owner_id) on delete set null (project_id)
);

create index if not exists processing_jobs_owner_created_idx
    on public.processing_jobs (owner_id, created_at desc);
create index if not exists processing_jobs_project_idx
    on public.processing_jobs (project_id) where project_id is not null;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    insert into public.profiles (id, display_name)
    values (new.id, nullif(trim(new.raw_user_meta_data ->> 'name'), ''))
    on conflict (id) do nothing;
    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute procedure public.handle_new_user();

drop trigger if exists profiles_set_updated_at on public.profiles;
create trigger profiles_set_updated_at
    before update on public.profiles
    for each row execute procedure public.set_updated_at();

drop trigger if exists projects_set_updated_at on public.projects;
create trigger projects_set_updated_at
    before update on public.projects
    for each row execute procedure public.set_updated_at();

drop trigger if exists processing_jobs_set_updated_at on public.processing_jobs;
create trigger processing_jobs_set_updated_at
    before update on public.processing_jobs
    for each row execute procedure public.set_updated_at();

alter table public.profiles enable row level security;
alter table public.projects enable row level security;
alter table public.processing_jobs enable row level security;

revoke all on table public.profiles from anon, authenticated;
revoke all on table public.projects from anon, authenticated;
revoke all on table public.processing_jobs from anon, authenticated;

grant select, update (display_name) on table public.profiles to authenticated;
grant select, insert (name), update (name), delete on table public.projects to authenticated;
grant select on table public.processing_jobs to authenticated;
grant insert (project_id, local_job_id, status, progress, message, output_filename)
    on table public.processing_jobs to authenticated;
grant update (project_id, status, progress, message, output_filename)
    on table public.processing_jobs to authenticated;
grant delete on table public.processing_jobs to authenticated;

drop policy if exists "Profiles are readable by their owner" on public.profiles;
create policy "Profiles are readable by their owner"
    on public.profiles for select to authenticated
    using ((select auth.uid()) = id);

drop policy if exists "Profiles are editable by their owner" on public.profiles;
create policy "Profiles are editable by their owner"
    on public.profiles for update to authenticated
    using ((select auth.uid()) = id)
    with check ((select auth.uid()) = id);

drop policy if exists "Projects are readable by their owner" on public.projects;
create policy "Projects are readable by their owner"
    on public.projects for select to authenticated
    using ((select auth.uid()) = owner_id);

drop policy if exists "Projects can be created by their owner" on public.projects;
create policy "Projects can be created by their owner"
    on public.projects for insert to authenticated
    with check ((select auth.uid()) = owner_id);

drop policy if exists "Projects are editable by their owner" on public.projects;
create policy "Projects are editable by their owner"
    on public.projects for update to authenticated
    using ((select auth.uid()) = owner_id)
    with check ((select auth.uid()) = owner_id);

drop policy if exists "Projects can be deleted by their owner" on public.projects;
create policy "Projects can be deleted by their owner"
    on public.projects for delete to authenticated
    using ((select auth.uid()) = owner_id);

drop policy if exists "Jobs are readable by their owner" on public.processing_jobs;
create policy "Jobs are readable by their owner"
    on public.processing_jobs for select to authenticated
    using ((select auth.uid()) = owner_id);

drop policy if exists "Jobs can be created by their owner" on public.processing_jobs;
create policy "Jobs can be created by their owner"
    on public.processing_jobs for insert to authenticated
    with check ((select auth.uid()) = owner_id);

drop policy if exists "Jobs are editable by their owner" on public.processing_jobs;
create policy "Jobs are editable by their owner"
    on public.processing_jobs for update to authenticated
    using ((select auth.uid()) = owner_id)
    with check ((select auth.uid()) = owner_id);

drop policy if exists "Jobs can be deleted by their owner" on public.processing_jobs;
create policy "Jobs can be deleted by their owner"
    on public.processing_jobs for delete to authenticated
    using ((select auth.uid()) = owner_id);

-- Enable private, per-user job metadata updates over Realtime where available.
do $$
begin
    if exists (select 1 from pg_publication where pubname = 'supabase_realtime') then
        if not exists (
            select 1 from pg_publication_tables
            where pubname = 'supabase_realtime'
              and schemaname = 'public'
              and tablename = 'processing_jobs'
        ) then
            alter publication supabase_realtime add table public.processing_jobs;
        end if;
    end if;
end;
$$;
