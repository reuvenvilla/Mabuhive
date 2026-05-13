/**
 * public/js/QuestsSubpage.jsx
 *
 * The /quests page. Three tabs, all sourced from /api/quests:
 *   - Joined     — every quest the user has joined (regardless of status)
 *   - Completed  — quests the user has marked completed
 *   - My Quests  — quests the user created (pencil button → edit modal)
 *
 * Each card links to /quests/<id> (handled in the next round). Cards on
 * the "My Quests" tab also surface a pencil button that opens an edit
 * modal for description + image. Tab/card/modal styles come from
 * hive.css so the look matches /hives/:id.
 */

// ── Helpers ──────────────────────────────────────────────────────────────────

async function apiFetch(url, options = {}) {
  const headers = {
    ...(options.headers || {}),
    ...((window.MabuAuth && (await window.MabuAuth.authHeaders())) || {}),
  };
  return fetch(url, { ...options, headers });
}

function bgImage(url) {
  return url ? { backgroundImage: `url(${url})` } : null;
}

// ── Quest card (shared across tabs) ─────────────────────────────────────────

function QuestCard({ quest, showPencil, onEdit }) {
  return (
    <div className="quest-card">
      <div className="quest-card__head">
        <a href={`/quests/${quest.id}`} className="quest-card__title">
          {quest.title}
        </a>
        {showPencil && (
          <button
            type="button"
            className="icon-btn"
            title="Edit description / image"
            onClick={() => onEdit && onEdit(quest)}
          >
            ✎
          </button>
        )}
      </div>
      <div className="quest-card__creator">
        by {quest.creator_username || "—"}
        {quest.hive_name && <span className="quest-card__hive">{quest.hive_name}</span>}
      </div>
      {quest.description && (
        <div className="quest-card__desc">{quest.description}</div>
      )}
    </div>
  );
}

// ── Quest edit modal (My Quests pencil) ─────────────────────────────────────

function EditQuestModal({ quest, onClose, onSaved }) {
  const [description, setDescription]   = React.useState(quest.description || "");
  const [imageFile, setImageFile]       = React.useState(null);
  const [imagePreview, setImagePreview] = React.useState(quest.img_url || "");
  const [keepImage, setKeepImage]       = React.useState(true);
  const [busy, setBusy] = React.useState(false);
  const [msg, setMsg]   = React.useState(null);

  function onPickImage(e) {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    setImageFile(file);
    setKeepImage(false);
    setImagePreview(URL.createObjectURL(file));
  }

  async function submit(e) {
    e.preventDefault();
    setBusy(true); setMsg(null);

    let img_url = keepImage ? (quest.img_url || "") : "";
    if (imageFile) {
      const form = new FormData();
      form.append("image", imageFile);
      const upResp = await apiFetch("/api/quest-image", { method: "POST", body: form });
      if (!upResp.ok) {
        const data = await upResp.json().catch(() => ({}));
        setMsg({ kind: "err", text: `Image upload failed: ${data.error || upResp.status}` });
        setBusy(false);
        return;
      }
      ({ img_url } = await upResp.json());
    }

    const resp = await apiFetch(`/api/quests/${quest.id}`, {
      method:  "PUT",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ description: description.trim(), img_url }),
    });
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      setMsg({ kind: "err", text: data.error || `Save failed (${resp.status})` });
      setBusy(false);
      return;
    }
    onSaved && onSaved(await resp.json());
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="modal__close" onClick={onClose} aria-label="Close">×</button>
        <h3>Edit quest</h3>
        <form onSubmit={submit} className="email-form" autoComplete="off">
          <label>
            Description
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3} maxLength={1000}
              className="field-input"
            />
          </label>
          <label>
            Replace image <span className="muted small">(optional)</span>
            <input
              type="file"
              accept="image/png,image/jpeg,image/gif,image/webp"
              onChange={onPickImage}
            />
          </label>
          {imagePreview && (
            <img
              src={imagePreview} alt=""
              style={{ maxWidth: "100%", borderRadius: "var(--radius)" }}
            />
          )}
          <div className="actions">
            <button type="submit" className="primary-btn" disabled={busy}>
              {busy ? "Saving…" : "Save changes"}
            </button>
            <button type="button" className="link-btn" onClick={onClose} disabled={busy}>
              Cancel
            </button>
          </div>
          {msg && <p className={`form-msg ${msg.kind}`}>{msg.text}</p>}
        </form>
      </div>
    </div>
  );
}

// ── One tab's data (fetch + pagination + render) ────────────────────────────

function QuestsTabBody({ kind, session }) {
  const [items, setItems]     = React.useState([]);
  const [page, setPage]       = React.useState(1);
  const [hasMore, setHasMore] = React.useState(false);
  const [loading, setLoading] = React.useState(false);
  const [error, setError]     = React.useState(null);
  const [editing, setEditing] = React.useState(null);

  const PAGE_SIZE = 10;

  // Reset to page 1 when the tab changes.
  React.useEffect(() => { setPage(1); }, [kind]);

  React.useEffect(() => {
    if (!session) {
      setItems([]); setError(null); setLoading(false);
      return;
    }
    setLoading(true); setError(null);
    let cancelled = false;
    const url = new URL("/api/quests", window.location.origin);
    url.searchParams.set("type", kind);
    url.searchParams.set("page", String(page));
    url.searchParams.set("size", String(PAGE_SIZE));

    apiFetch(url.toString())
      .then(async (resp) => {
        if (cancelled) return;
        if (!resp.ok) {
          const data = await resp.json().catch(() => ({}));
          setError(data.error || `Failed (${resp.status})`);
          setItems([]); setHasMore(false);
        } else {
          const data = await resp.json();
          setItems(data.items || []);
          setHasMore(Boolean(data.has_more));
        }
      })
      .catch((e) => { if (!cancelled) setError(String(e)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [kind, page, session && session.user && session.user.id]);

  const emptyText = (
    kind === "completed" ? "No completed quests yet."
    : kind === "mine"    ? "You haven't created any quests yet."
                          : "You haven't joined any quests yet."
  );

  return (
    <div className="tab-body">
      <div className="tab-list">
        {!session && (
          <p className="muted">Sign in to see your quests.</p>
        )}
        {session && loading && <p className="muted">Loading…</p>}
        {session && error   && <p className="form-msg err">{error}</p>}
        {session && !loading && !error && items.length === 0 && (
          <p className="muted">{emptyText}</p>
        )}
        {items.map((q) => (
          <QuestCard
            key={q.id}
            quest={q}
            showPencil={kind === "mine"}
            onEdit={(quest) => setEditing(quest)}
          />
        ))}
      </div>
      <footer className="tab-pager">
        <button
          type="button"
          className="secondary-btn small"
          disabled={page <= 1 || loading}
          onClick={() => setPage((p) => Math.max(1, p - 1))}
        >
          ‹ Back
        </button>
        <span className="muted small">Page {page}</span>
        <button
          type="button"
          className="secondary-btn small"
          disabled={!hasMore || loading}
          onClick={() => setPage((p) => p + 1)}
        >
          Forward ›
        </button>
      </footer>
      {editing && (
        <EditQuestModal
          quest={editing}
          onClose={() => setEditing(null)}
          onSaved={(updated) => {
            setItems((curr) =>
              curr.map((q) => (q.id === updated.id ? { ...q, ...updated } : q))
            );
            setEditing(null);
          }}
        />
      )}
    </div>
  );
}

// ── Page entry point ─────────────────────────────────────────────────────────

function QuestsPageContent() {
  const [session, setSession]     = React.useState(null);
  const [authReady, setAuthReady] = React.useState(false);
  const [tab, setTab]             = React.useState("joined");

  React.useEffect(() => {
    if (!window.MabuAuth) { setAuthReady(true); return; }
    return window.MabuAuth.onAuthChange((s) => {
      setSession(s);
      setAuthReady(true);
    });
  }, []);

  if (!authReady) return <p className="muted">Loading…</p>;

  return (
    <div className="quests-page">
      <div className="tabs">
        <button
          type="button"
          className={`tab-btn${tab === "joined" ? " tab-btn--active" : ""}`}
          onClick={() => setTab("joined")}
        >Joined</button>
        <button
          type="button"
          className={`tab-btn${tab === "completed" ? " tab-btn--active" : ""}`}
          onClick={() => setTab("completed")}
        >Completed</button>
        <button
          type="button"
          className={`tab-btn${tab === "mine" ? " tab-btn--active" : ""}`}
          onClick={() => setTab("mine")}
        >My Quests</button>
      </div>

      <QuestsTabBody kind={tab} session={session} />
    </div>
  );
}
