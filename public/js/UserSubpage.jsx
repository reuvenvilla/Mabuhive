/**
 * public/js/UserSubpage.jsx
 *
 * The user page renders in two modes:
 *
 *   OWNER  — the logged-in user is viewing their own record.
 *            Shows username, uid, email (reveal-toggle, censored by default),
 *            method-of-creation (OAuth provider), description (editable),
 *            and an avatar uploader.
 *
 *   VIEWER — the page is showing someone else's record.
 *            Shows only username, avatar, and description (read-only).
 *
 * Routing handled in here:
 *   /user                     -> own user (or login if signed out)
 *                                redirects to /user-create if no record yet
 *   /user/<username>          -> public view (owner view if it's you)
 */

// ── Helpers ──────────────────────────────────────────────────────────────────

function getUsernameFromPath() {
  // "/user"            -> ""
  // "/user/jdoe"       -> "jdoe"
  // "/user/jdoe/"      -> "jdoe"
  const m = window.location.pathname.match(/^\/user\/([a-zA-Z0-9_-]+)\/?$/);
  return m ? m[1] : "";
}

function censorEmail(email) {
  if (!email || !email.includes("@")) return "";
  const [local, domain] = email.split("@");
  const visible  = local.slice(0, 3);
  const censored = "*".repeat(Math.max(local.length - visible.length, 1));
  return `${visible}${censored}@${domain}`;
}

function providerLabel(provider) {
  if (!provider) return "Unknown";
  const map = {
    google:  "Google",
    discord: "Discord",
    email:   "Email & password",
    github:  "GitHub",
  };
  return map[provider] || (provider[0].toUpperCase() + provider.slice(1));
}

async function apiFetch(url, options = {}) {
  const headers = {
    ...(options.headers || {}),
    ...(await window.MabuAuth.authHeaders()),
  };
  return fetch(url, { ...options, headers });
}

// ── Login screen ─────────────────────────────────────────────────────────────

function LoginScreen() {
  const [mode, setMode] = React.useState("signin"); // "signin" | "signup"
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [msg, setMsg] = React.useState(null);

  async function oauth(provider) {
    setBusy(true); setMsg(null);
    const { error } = await window.MabuAuth.signInWithOAuth(provider);
    if (error) { setMsg({ kind: "err", text: error.message }); setBusy(false); }
    // On success the browser navigates away; no need to setBusy(false).
  }

  async function emailSubmit(e) {
    e.preventDefault();
    setBusy(true); setMsg(null);
    const fn = mode === "signin"
      ? window.MabuAuth.signInWithPassword
      : window.MabuAuth.signUpWithPassword;
    const { error } = await fn({ email, password });
    setBusy(false);
    if (error) {
      setMsg({ kind: "err", text: error.message });
    } else if (mode === "signup") {
      setMsg({ kind: "ok", text: "Check your email to confirm your account." });
    } else {
      window.location.reload();
    }
  }

  return (
    <div className="card login-card">
      <h2>Sign in to MabuHive</h2>

      <div className="oauth-row">
        <button className="oauth-btn google"  disabled={busy} onClick={() => oauth("google")}>
          Continue with Google
        </button>
        <button className="oauth-btn discord" disabled={busy} onClick={() => oauth("discord")}>
          Continue with Discord
        </button>
      </div>

      <div className="divider"><span>or</span></div>

      <form onSubmit={emailSubmit} className="email-form">
        <label>
          Email
          <input
            type="email" required value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
          />
        </label>
        <label>
          Password
          <input
            type="password" required minLength={6} value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === "signin" ? "current-password" : "new-password"}
          />
        </label>
        <button type="submit" className="primary-btn" disabled={busy}>
          {mode === "signin" ? "Sign in" : "Create account"}
        </button>
        <button
          type="button" className="link-btn"
          onClick={() => { setMsg(null); setMode(mode === "signin" ? "signup" : "signin"); }}
        >
          {mode === "signin"
            ? "Need an account? Sign up"
            : "Already have an account? Sign in"}
        </button>
      </form>

      {msg && <p className={`form-msg ${msg.kind}`}>{msg.text}</p>}
    </div>
  );
}

// ── Owner view (editable) ────────────────────────────────────────────────────

function OwnerUser({ user, onUserUpdated }) {
  const [revealEmail, setRevealEmail] = React.useState(false);
  const [username, setUsername]       = React.useState(user.username || "");
  const [description, setDescription] = React.useState(user.description || "");
  const [saving, setSaving]           = React.useState(false);
  const [saveMsg, setSaveMsg]         = React.useState(null);
  const [uploading, setUploading]     = React.useState(false);
  const fileInputRef = React.useRef(null);

  const usernameDirty    = username    !== (user.username    || "");
  const descriptionDirty = description !== (user.description || "");
  const dirty            = usernameDirty || descriptionDirty;

  async function save() {
    setSaving(true); setSaveMsg(null);
    const body = {};
    if (usernameDirty)    body.username    = username.trim();
    if (descriptionDirty) body.description = description;
    const resp = await apiFetch("/api/users/me", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(body),
    });
    setSaving(false);
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      setSaveMsg({ kind: "err", text: data.error || `Save failed (${resp.status})` });
      return;
    }
    const updated = await resp.json();
    setSaveMsg({ kind: "ok", text: "Saved." });
    onUserUpdated(updated);
    if (usernameDirty && getUsernameFromPath()) {
      window.history.replaceState(null, "", `/user/${updated.username}`);
    }
  }

  async function onPickAvatar(e) {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    setUploading(true); setSaveMsg(null);
    const form = new FormData();
    form.append("avatar", file);
    const resp = await apiFetch("/api/avatar", { method: "POST", body: form });
    setUploading(false);
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      setSaveMsg({ kind: "err", text: data.error || `Upload failed (${resp.status})` });
      return;
    }
    const { user: updated } = await resp.json();
    onUserUpdated(updated);
  }

  return (
    <div className="user-page owner">
      <div className="avatar-block">
        <div
          className="avatar"
          style={user.avatar_url ? { backgroundImage: `url(${user.avatar_url})` } : null}
        >
          {!user.avatar_url &&
            <span className="avatar-placeholder">
              {(user.username || "?")[0].toUpperCase()}
            </span>
          }
        </div>
        <input
          ref={fileInputRef} type="file" accept="image/png,image/jpeg,image/gif,image/webp"
          style={{ display: "none" }} onChange={onPickAvatar}
        />
        <button
          className="secondary-btn"
          disabled={uploading}
          onClick={() => fileInputRef.current && fileInputRef.current.click()}
        >
          {uploading ? "Uploading…" : "Change avatar"}
        </button>
      </div>

      <div className="user-fields">
        <label className="field">
          <span className="field-label">Username</span>
          <input
            className="field-input"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            minLength={3} maxLength={32}
            pattern="[a-zA-Z0-9_\-]{3,32}"
            title="3–32 characters: letters, numbers, underscore, hyphen"
          />
        </label>

        <div className="field">
          <span className="field-label">User ID</span>
          <code className="field-static mono">{user.uid}</code>
        </div>

        <div className="field">
          <span className="field-label">Email</span>
          <div className="field-row">
            <code className="field-static mono">
              {revealEmail ? (user.email || "—") : censorEmail(user.email)}
            </code>
            <button
              className="secondary-btn small"
              onClick={() => setRevealEmail((v) => !v)}
              disabled={!user.email}
              type="button"
            >
              {revealEmail ? "Hide" : "Reveal"}
            </button>
          </div>
        </div>

        <div className="field">
          <span className="field-label">Account created via</span>
          <span className="field-static">
            {providerLabel(user.provider)}
            {user.providers && user.providers.length > 1 && (
              <span className="muted">
                {"  ·  also linked: "}
                {user.providers.filter((p) => p !== user.provider).map(providerLabel).join(", ")}
              </span>
            )}
          </span>
        </div>

        <label className="field">
          <span className="field-label">Description</span>
          <textarea
            className="field-input"
            rows={4}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Tell people about yourself…"
            maxLength={500}
          />
        </label>

        <div className="actions">
          <button className="primary-btn" onClick={save} disabled={!dirty || saving}>
            {saving ? "Saving…" : "Save changes"}
          </button>
          {saveMsg && <span className={`form-msg ${saveMsg.kind}`}>{saveMsg.text}</span>}
        </div>
      </div>
    </div>
  );
}

// ── Viewer view (read-only public user) ──────────────────────────────────────

function ViewerUser({ user }) {
  return (
    <div className="user-page viewer">
      <div className="avatar-block">
        <div
          className="avatar"
          style={user.avatar_url ? { backgroundImage: `url(${user.avatar_url})` } : null}
        >
          {!user.avatar_url &&
            <span className="avatar-placeholder">
              {(user.username || "?")[0].toUpperCase()}
            </span>
          }
        </div>
      </div>
      <div className="user-fields">
        <h2 className="username">{user.username}</h2>
        <p className="description">
          {user.description || <span className="muted">No description yet.</span>}
        </p>
      </div>
    </div>
  );
}

// ── Page entry point ─────────────────────────────────────────────────────────

function UserPageContent() {
  const [session, setSession]     = React.useState(null);
  const [authReady, setAuthReady] = React.useState(false);
  const [user, setUser]           = React.useState(null);
  const [loading, setLoading]     = React.useState(true);
  const [error, setError]         = React.useState(null);

  const urlUsername = getUsernameFromPath();

  // Subscribe to auth state.
  React.useEffect(() => {
    if (!window.MabuAuth) {
      setError("Auth not loaded on this page.");
      setAuthReady(true);
      return;
    }
    return window.MabuAuth.onAuthChange((s) => {
      setSession(s);
      setAuthReady(true);
    });
  }, []);

  // Once we know who the viewer is, fetch the right record.
  React.useEffect(() => {
    if (!authReady) return;

    async function load() {
      setLoading(true); setError(null);
      try {
        if (urlUsername) {
          // /user/<username>. Sending auth headers means the server can
          // hand back the owner view if it's actually you.
          const resp = await apiFetch(`/api/users/${urlUsername}`);
          if (resp.status === 404) {
            setError(`No user with username "${urlUsername}".`);
            setUser(null);
          } else if (!resp.ok) {
            setError(`Failed to load user (${resp.status}).`);
          } else {
            setUser(await resp.json());
          }
        } else if (session) {
          // /user with no username + signed in -> own record.
          const resp = await apiFetch("/api/users/me");
          if (!resp.ok) {
            // 404 = no row yet (expected on first sign-in).
            // 502 / anything else = Supabase had an issue OR the row was
            // deleted out from under us. Either way the right next step
            // is the creation flow — it'll re-check and either bounce
            // them to their existing profile or let them create one.
            window.location.replace("/user-create");
            return;
          }
          const me = await resp.json();
          setUser(me);
          // Rewrite the URL so links are shareable.
          if (me.username) {
            window.history.replaceState(null, "", `/user/${me.username}`);
          }
        } else {
          // /user + not signed in -> login screen handles itself.
          setUser(null);
        }
      } catch (e) {
        setError(e.message || String(e));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [authReady, urlUsername, session && session.user && session.user.id]);

  // ── Render branches ──────────────────────────────────────────────────────

  if (!authReady || loading) {
    return <p className="muted">Loading…</p>;
  }

  if (error) {
    return <p className="form-msg err">{error}</p>;
  }

  // Not signed in + no username in URL -> show login screen.
  if (!session && !urlUsername) {
    return <LoginScreen />;
  }

  if (!user) {
    return <p className="muted">User not available.</p>;
  }

  const isOwner = Boolean(
    session && session.user && session.user.id === user.uid
  );

  if (isOwner) {
    return <OwnerUser user={user} onUserUpdated={setUser} />;
  }

  return (
    <React.Fragment>
      <ViewerUser user={user} />
      {!session && (
        <p className="muted small" style={{ marginTop: "1rem" }}>
          <a href="/user" className="link-btn-inline">Sign in</a> to view your own profile.
        </p>
      )}
    </React.Fragment>
  );
}
