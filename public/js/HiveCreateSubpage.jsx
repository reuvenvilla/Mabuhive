/**
 * public/js/HiveCreateSubpage.jsx
 *
 * The /hives/create page. Form fields:
 *   - logo  (image/*, required)
 *   - name  (text, required, <=64 chars)
 *   - description (text, optional, <=1000 chars)
 *
 * Submit flow:
 *   1. POST the logo to /api/hive-logo → returns a public URL in
 *      Supabase Storage's hive_logos bucket.
 *   2. POST {name, description, img_url} to /api/hives → server
 *      inserts the hive AND adds the caller to hive_members with
 *      role='admin' (so the creator both owns and joins it).
 *   3. Navigate to /hives/<new_id>.
 *
 * If the user isn't signed in, we bounce them to /user so they can
 * authenticate first.
 */

const HIVE_NAME_MAX = 64;
const HIVE_DESC_MAX = 1000;

async function apiFetchAuthed(url, options = {}) {
  const headers = {
    ...(options.headers || {}),
    ...(await window.MabuAuth.authHeaders()),
  };
  return fetch(url, { ...options, headers });
}

function CreateHivePageContent() {
  const [session, setSession]     = React.useState(null);
  const [authReady, setAuthReady] = React.useState(false);

  const [logoFile, setLogoFile]       = React.useState(null);
  const [logoPreview, setLogoPreview] = React.useState("");
  const [name, setName]               = React.useState("");
  const [description, setDescription] = React.useState("");
  const [submitting, setSubmitting]   = React.useState(false);
  const [msg, setMsg]                 = React.useState(null);

  const fileInputRef = React.useRef(null);

  // Auth subscription.
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

  // Gate: must be signed in. Bounce to /user (which shows the login screen).
  React.useEffect(() => {
    if (authReady && !session) {
      window.location.replace("/user");
    }
  }, [authReady, session]);

  function onPickLogo(e) {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    setLogoFile(file);
    setLogoPreview(URL.createObjectURL(file));
  }

  function validate() {
    const trimmedName = name.trim();
    if (!trimmedName) return "Hive name is required.";
    if (trimmedName.length > HIVE_NAME_MAX) {
      return `Name must be ${HIVE_NAME_MAX} characters or fewer.`;
    }
    if (description.length > HIVE_DESC_MAX) {
      return `Description must be ${HIVE_DESC_MAX} characters or fewer.`;
    }
    if (!logoFile) return "A hive logo is required.";
    return null;
  }

  async function submit(e) {
    e.preventDefault();
    const vmsg = validate();
    if (vmsg) { setMsg({ kind: "err", text: vmsg }); return; }

    setSubmitting(true); setMsg(null);

    // 1. Upload the logo.
    const form = new FormData();
    form.append("logo", logoFile);
    const upResp = await apiFetchAuthed("/api/hive-logo", {
      method: "POST",
      body:   form,
    });
    if (!upResp.ok) {
      const data = await upResp.json().catch(() => ({}));
      setMsg({
        kind: "err",
        text: `Logo upload failed: ${data.error || upResp.status}`,
      });
      setSubmitting(false);
      return;
    }
    const { img_url } = await upResp.json();

    // 2. Create the hive — server inserts hive + hive_members(role=admin).
    const createResp = await apiFetchAuthed("/api/hives", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({
        name:        name.trim(),
        description: description.trim(),
        img_url,
      }),
    });
    if (!createResp.ok) {
      const data = await createResp.json().catch(() => ({}));
      setMsg({
        kind: "err",
        text: data.error || `Create failed (${createResp.status})`,
      });
      setSubmitting(false);
      return;
    }

    const created = await createResp.json();
    if (!created.id) {
      setMsg({ kind: "err", text: "Server didn't return a hive id." });
      setSubmitting(false);
      return;
    }

    // 3. Off to the new hive's page.
    window.location.assign(`/hives/${created.id}`);
  }

  if (!authReady) return <p className="muted">Loading…</p>;
  if (!session)   return <p className="muted">Redirecting…</p>;

  const initial = (name || "?").trim()[0];

  return (
    <div className="card create-card">
      <h2>Create a new hive</h2>
      <p className="helptext">
        You'll be added as an admin and joined to the hive automatically.
      </p>

      <form onSubmit={submit} className="email-form" autoComplete="off">
        <div className="create-avatar-row">
          <div
            className="avatar"
            style={logoPreview ? { backgroundImage: `url(${logoPreview})` } : null}
          >
            {!logoPreview && (
              <span className="avatar-placeholder">
                {initial ? initial.toUpperCase() : "?"}
              </span>
            )}
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/png,image/jpeg,image/gif,image/webp"
            style={{ display: "none" }}
            onChange={onPickLogo}
          />
          <button
            type="button"
            className="secondary-btn"
            onClick={() => fileInputRef.current && fileInputRef.current.click()}
            disabled={submitting}
          >
            {logoFile ? "Replace logo" : "Pick logo"}
          </button>
        </div>

        <label>
          Hive name
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={HIVE_NAME_MAX}
            placeholder="e.g. Daily 5km Runners"
            autoFocus
          />
        </label>

        <label>
          Description <span className="muted small">(optional)</span>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What's this hive about?"
            maxLength={HIVE_DESC_MAX}
            rows={4}
            className="field-input"
          />
        </label>

        <div className="actions">
          <button type="submit" className="primary-btn" disabled={submitting}>
            {submitting ? "Creating…" : "Create hive"}
          </button>
          <a href="/hives" className="link-btn">Cancel</a>
        </div>
      </form>

      {msg && <p className={`form-msg ${msg.kind}`}>{msg.text}</p>}
    </div>
  );
}
