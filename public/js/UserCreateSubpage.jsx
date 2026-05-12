/**
 * public/js/UserCreateSubpage.jsx
 *
 * One-time onboarding form shown after a Supabase sign-in when the user
 * has no record in our /api/users collection. Asks them to pick a
 * username and (optionally) a description + avatar.
 *
 * Routing rules:
 *   - Not signed in → bounce back to /user (which shows the login screen).
 *   - Already has a record → bounce to /user/<their-username>.
 *   - Signed in, no record → render the form.
 *
 * Submit flow:
 *   1. POST /api/users/me with { username, description }
 *      → server creates the row, mirroring the JWT's email/provider.
 *   2. If an avatar was picked, POST /api/avatar (multipart)
 *      → server stores the file and patches the new avatar_url.
 *   3. Navigate to /user/<username>.
 */

const USERNAME_PATTERN = /^[a-zA-Z0-9_-]{3,32}$/;
const RESERVED_USERNAMES = new Set([
  "me", "create", "new", "edit", "admin", "root", "system",
]);

function deriveUsernameSeed(session) {
  // Pre-fill the username from the email local-part, if we have one.
  if (!session || !session.user) return "";
  const email = session.user.email || "";
  const local = email.includes("@") ? email.split("@", 1)[0] : "";
  const clean = local.replace(/[^a-zA-Z0-9_-]/g, "");
  return clean.length >= 3 ? clean.slice(0, 32) : "";
}

async function apiFetchAuthed(url, options = {}) {
  const headers = {
    ...(options.headers || {}),
    ...(await window.MabuAuth.authHeaders()),
  };
  return fetch(url, { ...options, headers });
}

function CreateUserPageContent() {
  const [session, setSession]     = React.useState(null);
  const [authReady, setAuthReady] = React.useState(false);

  const [username, setUsername]       = React.useState("");
  const [description, setDescription] = React.useState("");
  const [avatarFile, setAvatarFile]   = React.useState(null);
  const [avatarPreview, setAvatarPreview] = React.useState("");
  const [submitting, setSubmitting]   = React.useState(false);
  const [msg, setMsg]                 = React.useState(null);

  const fileInputRef = React.useRef(null);

  // Subscribe to auth state.
  React.useEffect(() => {
    if (!window.MabuAuth) {
      setMsg({ kind: "err", text: "Auth not loaded on this page." });
      setAuthReady(true);
      return;
    }
    return window.MabuAuth.onAuthChange((s) => {
      setSession(s);
      setAuthReady(true);
    });
  }, []);

  // Route gate: kick them out if they shouldn't be on this page.
  React.useEffect(() => {
    if (!authReady) return;

    if (!session) {
      window.location.replace("/user");
      return;
    }

    // Pre-fill the username straight away so the form is usable even if
    // the existence check fails (e.g. transient 502).
    setUsername(deriveUsernameSeed(session));

    // If they already have a record, send them to their profile.
    // Anything else (404, 502, network blip…) leaves them on the form.
    (async () => {
      const resp = await apiFetchAuthed("/api/users/me");
      if (resp.ok) {
        const me = await resp.json();
        window.location.replace(`/user/${me.username}`);
        return;
      }
      if (resp.status !== 404) {
        const data = await resp.json().catch(() => ({}));
        setMsg({
          kind: "err",
          text:
            (data.error || `Couldn't check existing record (${resp.status}).`) +
            " You can still try creating below.",
        });
      }
    })();
  }, [authReady, session && session.user && session.user.id]);

  function onPickAvatar(e) {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    setAvatarFile(file);
    setAvatarPreview(URL.createObjectURL(file));
  }

  function validate() {
    const name = username.trim();
    if (!USERNAME_PATTERN.test(name)) {
      return "Username must be 3–32 characters: letters, numbers, underscore, hyphen.";
    }
    if (RESERVED_USERNAMES.has(name.toLowerCase())) {
      return `"${name}" is reserved — pick another username.`;
    }
    return null;
  }

  async function submit(e) {
    e.preventDefault();
    const validationErr = validate();
    if (validationErr) { setMsg({ kind: "err", text: validationErr }); return; }

    setSubmitting(true); setMsg(null);

    // 1. Create the user record.
    const createResp = await apiFetchAuthed("/api/users/me", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({
        username: username.trim(),
        description: description.trim(),
      }),
    });

    if (!createResp.ok) {
      const data = await createResp.json().catch(() => ({}));
      // 409 + "already exists" means our SELECT earlier was wrong (e.g. an
      // RLS-denied or transient 502) but the row actually exists. Send
      // them to /user so they can see it.
      if (
        createResp.status === 409 &&
        /already exists/i.test(data.error || "")
      ) {
        window.location.replace("/user");
        return;
      }
      setMsg({ kind: "err", text: data.error || `Create failed (${createResp.status})` });
      setSubmitting(false);
      return;
    }

    const created = await createResp.json();

    // 2. Upload avatar if one was chosen. Failure here is non-fatal — the
    //    record exists, the user can re-try from the profile page.
    if (avatarFile) {
      const form = new FormData();
      form.append("avatar", avatarFile);
      const upResp = await apiFetchAuthed("/api/avatar", { method: "POST", body: form });
      if (!upResp.ok) {
        const data = await upResp.json().catch(() => ({}));
        setMsg({
          kind: "err",
          text: `Account created, but avatar failed: ${data.error || upResp.status}. You can upload it from your profile.`,
        });
        setSubmitting(false);
        setTimeout(() => { window.location.assign(`/user/${created.username}`); }, 2500);
        return;
      }
    }

    // 3. Done.
    window.location.assign(`/user/${created.username}`);
  }

  if (!authReady) {
    return <p className="muted">Loading…</p>;
  }

  const initial = (username || "?").trim()[0];

  return (
    <div className="card create-card">
      <h2>Welcome — finish setting up your account</h2>
      <p className="helptext">
        You're signed in as <code className="mono">{session && session.user && session.user.email ? session.user.email : "—"}</code>.
        Pick a username (and anything else you'd like) to create your profile.
      </p>

      <form onSubmit={submit} className="email-form" autoComplete="off">
        <div className="create-avatar-row">
          <div
            className="avatar"
            style={avatarPreview ? { backgroundImage: `url(${avatarPreview})` } : null}
          >
            {!avatarPreview && (
              <span className="avatar-placeholder">
                {initial ? initial.toUpperCase() : "?"}
              </span>
            )}
          </div>
          <input
            ref={fileInputRef} type="file"
            accept="image/png,image/jpeg,image/gif,image/webp"
            style={{ display: "none" }} onChange={onPickAvatar}
          />
          <button
            type="button" className="secondary-btn"
            onClick={() => fileInputRef.current && fileInputRef.current.click()}
            disabled={submitting}
          >
            {avatarFile ? "Replace avatar" : "Pick avatar"}
          </button>
        </div>

        <label>
          Username
          <input
            type="text"
            required
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            minLength={3} maxLength={32}
            pattern="[a-zA-Z0-9_\-]{3,32}"
            title="3–32 characters: letters, numbers, underscore, hyphen"
            autoFocus
          />
        </label>

        <label>
          Description <span className="muted small">(optional)</span>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Tell people about yourself…"
            maxLength={500}
            rows={3}
            className="field-input"
          />
        </label>

        <div className="actions">
          <button type="submit" className="primary-btn" disabled={submitting}>
            {submitting ? "Creating…" : "Create my profile"}
          </button>
          <button
            type="button" className="link-btn"
            onClick={async () => {
              await window.MabuAuth.signOut();
              window.location.assign("/user");
            }}
            disabled={submitting}
          >
            Sign out
          </button>
        </div>
      </form>

      {msg && <p className={`form-msg ${msg.kind}`}>{msg.text}</p>}
    </div>
  );
}
