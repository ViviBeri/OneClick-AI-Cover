import { useEffect, useMemo, useState } from "react";
import { createClient, type Session, type SupabaseClient } from "@supabase/supabase-js";
import "./styles.css";

type Project = {
  id: string;
  name: string;
  created_at: string;
};

type ProcessingJob = {
  id: string;
  project_id: string | null;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  progress: number;
  message: string;
  output_filename: string | null;
  created_at: string;
};

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL?.trim();
const supabaseKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY?.trim();
const supabase: SupabaseClient | null =
  supabaseUrl && supabaseKey ? createClient(supabaseUrl, supabaseKey) : null;

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(Boolean(supabase));
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authMode, setAuthMode] = useState<"signin" | "signup">("signin");
  const [projectName, setProjectName] = useState("");
  const [projects, setProjects] = useState<Project[]>([]);
  const [jobs, setJobs] = useState<ProcessingJob[]>([]);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const clientReady = useMemo(() => Boolean(supabase), []);

  useEffect(() => {
    if (!supabase) return;
    let active = true;

    supabase.auth.getSession().then(({ data, error: sessionError }) => {
      if (!active) return;
      if (sessionError) setError(sessionError.message);
      setSession(data.session);
      setLoading(false);
    });

    const { data } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
    });

    return () => {
      active = false;
      data.subscription.unsubscribe();
    };
  }, []);

  useEffect(() => {
    if (!supabase || !session?.user.id) {
      setProjects([]);
      setJobs([]);
      return;
    }

    let active = true;
    const userId = session.user.id;

    async function loadDashboard() {
      const [projectResult, jobResult] = await Promise.all([
        supabase!.from("projects").select("id,name,created_at").order("created_at", { ascending: false }),
        supabase!.from("processing_jobs")
          .select("id,project_id,status,progress,message,output_filename,created_at")
          .order("created_at", { ascending: false })
          .limit(30),
      ]);

      if (!active) return;
      if (projectResult.error) setError(projectResult.error.message);
      else setProjects(projectResult.data ?? []);
      if (jobResult.error) setError(jobResult.error.message);
      else setJobs(jobResult.data ?? []);
    }

    void loadDashboard();

    const channel = supabase
      .channel(`job-history-${userId}`)
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "processing_jobs", filter: `owner_id=eq.${userId}` },
        () => void loadDashboard(),
      )
      .subscribe();

    return () => {
      active = false;
      void supabase!.removeChannel(channel);
    };
  }, [session?.user.id]);

  async function handleAuth(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!supabase) return;
    setBusy(true);
    setError("");
    setNotice("");

    const result = authMode === "signup"
      ? await supabase.auth.signUp({ email, password })
      : await supabase.auth.signInWithPassword({ email, password });

    setBusy(false);
    if (result.error) {
      setError(result.error.message);
    } else if (authMode === "signup" && !result.data.session) {
      setNotice("Check your email to confirm your account, then sign in.");
    }
  }

  async function createProject(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!supabase || !projectName.trim()) return;
    setBusy(true);
    setError("");
    setNotice("");

    const { data, error: insertError } = await supabase
      .from("projects")
      .insert({ name: projectName.trim() })
      .select("id,name,created_at")
      .single();

    setBusy(false);
    if (insertError) {
      setError(insertError.message);
      return;
    }
    setProjects((current) => [data, ...current]);
    setProjectName("");
    setNotice("Project created.");
  }

  async function deleteProject(projectId: string) {
    if (!supabase) return;
    setError("");
    setNotice("");
    const { error: deleteError } = await supabase.from("projects").delete().eq("id", projectId);
    if (deleteError) {
      setError(deleteError.message);
      return;
    }
    setProjects((current) => current.filter((project) => project.id !== projectId));
    setNotice("Project deleted.");
  }

  async function signOut() {
    if (!supabase) return;
    const { error: signOutError } = await supabase.auth.signOut();
    if (signOutError) setError(signOutError.message);
  }

  if (!clientReady) {
    return (
      <main className="shell">
        <header className="brand"><span className="brand-mark">OC</span><span>ONECLICK <b>AI COVER</b></span></header>
        <section className="setup-panel">
          <p className="eyebrow">CLOUD ACCOUNT · OPTIONAL</p>
          <h1>Connect your Supabase project</h1>
          <p className="muted">The web dashboard needs a Supabase project URL and publishable key. Local audio generation remains available without this cloud account.</p>
          <div className="setup-code">
            <code>VITE_SUPABASE_URL=https://your-project.supabase.co</code>
            <code>VITE_SUPABASE_PUBLISHABLE_KEY=your-publishable-key</code>
          </div>
          <p className="small muted">Create <code>web/.env.local</code> using <code>web/.env.example</code>. Never use a secret or service-role key here.</p>
        </section>
        <footer>LOCAL PROCESSING FIRST <span>·</span> CLOUD SYNC OPTIONAL</footer>
      </main>
    );
  }

  if (loading) {
    return <main className="shell loading-state" aria-live="polite">Loading your studio…</main>;
  }

  if (!session) {
    return (
      <main className="shell auth-shell">
        <header className="brand"><span className="brand-mark">OC</span><span>ONECLICK <b>AI COVER</b></span></header>
        <section className="auth-panel">
          <p className="eyebrow">YOUR CREATIVE WORKSPACE</p>
          <h1>{authMode === "signin" ? "Welcome back." : "Create your account."}</h1>
          <p className="muted">Sync project names and processing history across your signed-in devices. Audio stays on your PC.</p>
          <form onSubmit={handleAuth} className="form-stack">
            <label htmlFor="email">Email</label>
            <input id="email" type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
            <label htmlFor="password">Password</label>
            <input id="password" type="password" autoComplete={authMode === "signin" ? "current-password" : "new-password"} minLength={8} required value={password} onChange={(event) => setPassword(event.target.value)} />
            <button className="primary-button" type="submit" disabled={busy}>{busy ? "Please wait…" : authMode === "signin" ? "Sign in" : "Create account"}</button>
          </form>
          <button className="text-button" onClick={() => setAuthMode(authMode === "signin" ? "signup" : "signin")}>
            {authMode === "signin" ? "New here? Create an account" : "Already registered? Sign in"}
          </button>
          <p className="small muted">By signing in, you enable cloud metadata sync. This does not upload songs, voice recordings, or model files.</p>
        </section>
        <Feedback error={error} notice={notice} />
        <footer>LOCAL PROCESSING FIRST <span>·</span> CLOUD SYNC OPTIONAL</footer>
      </main>
    );
  }

  return (
    <main className="shell dashboard-shell">
      <header className="topbar">
        <div className="brand"><span className="brand-mark">OC</span><span>ONECLICK <b>AI COVER</b></span></div>
        <div className="account"><span className="account-email">{session.user.email}</span><button className="quiet-button" onClick={signOut}>Sign out</button></div>
      </header>

      <section className="welcome">
        <div><p className="eyebrow">YOUR STUDIO</p><h1>Good to see you.</h1><p className="muted">Your projects and local processing history, in one place.</p></div>
        <span className="local-chip"><span /> LOCAL ENGINE REQUIRED</span>
      </section>

      <Feedback error={error} notice={notice} />

      <section className="section-block">
        <div className="section-heading"><div><p className="eyebrow">WORKSPACE</p><h2>Projects</h2></div><span className="count">{projects.length} PROJECTS</span></div>
        <form className="project-form" onSubmit={createProject}>
          <label className="visually-hidden" htmlFor="project-name">Project name</label>
          <input id="project-name" maxLength={120} placeholder="Name a new project…" value={projectName} onChange={(event) => setProjectName(event.target.value)} />
          <button className="primary-button" type="submit" disabled={busy || !projectName.trim()}>Create project</button>
        </form>
        {projects.length === 0 ? (
          <div className="empty-state"><strong>No projects yet</strong><span>Create a project to organize your cover work.</span></div>
        ) : (
          <div className="project-grid">
            {projects.map((project) => (
              <article className="project-card" key={project.id}>
                <span className="project-icon">♪</span>
                <div className="project-copy"><h3>{project.name}</h3><p>Created {formatDate(project.created_at)}</p></div>
                <button className="icon-button" aria-label={`Delete ${project.name}`} onClick={() => void deleteProject(project.id)}>×</button>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="section-block">
        <div className="section-heading"><div><p className="eyebrow">ACTIVITY</p><h2>Processing history</h2></div><span className="count">LATEST 30</span></div>
        {jobs.length === 0 ? (
          <div className="empty-state"><strong>No synced jobs</strong><span>Jobs will appear here when the local desktop app sync integration is connected.</span></div>
        ) : (
          <div className="job-list">
            {jobs.map((job) => (
              <article className="job-row" key={job.id}>
                <div className="job-main"><span className={`status-dot status-${job.status}`} /><div><strong>{job.output_filename ?? `Cover job · ${job.id.slice(0, 8)}`}</strong><p>{job.message} · {formatDate(job.created_at)}</p></div></div>
                <div className="job-progress"><span>{job.status.toUpperCase()}</span><div className="progress-track"><i style={{ width: `${Math.round(Number(job.progress) * 100)}%` }} /></div></div>
              </article>
            ))}
          </div>
        )}
      </section>

      <footer>YOUR AUDIO AND VOICE MODELS STAY ON YOUR LOCAL DEVICE</footer>
    </main>
  );
}

function Feedback({ error, notice }: { error: string; notice: string }) {
  if (!error && !notice) return null;
  return <div className={error ? "feedback error" : "feedback success"} role="status">{error || notice}</div>;
}

export default App;
