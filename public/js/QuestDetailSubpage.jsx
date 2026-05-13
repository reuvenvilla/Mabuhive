/**
 * public/js/QuestDetailSubpage.jsx
 *
 * The /quests/<id> page.
 *
 * Top panel:
 *   - Title + creator + (optional) parent-hive pill
 *   - Description (full text)
 *   - Optional image
 *   - Creator only: pencil-edit (description + image) and an image-scale
 *     slider that resizes the image in their local view
 *
 * Bottom panel — two tabs:
 *   - Replies — chronological (oldest first). Reply cards turn green when
 *     fulfills_quest = true. Creator sees a checkbox on each reply that
 *     toggles fulfills_quest (and mirrors completed_at on the reply
 *     author's quest_participants row).
 *   - List    — quest_participants joined to users, sorted with completed
 *     users first (oldest completed_at first), then non-completed users
 *     (oldest joined_at first). Completed rows turn green.
 *
 * FAB at the bottom-right of the tabs panel opens the reply pop-up:
 * description + image file → POST /api/quest-replies.
 *
 * The image-scale slider is creator-local (kept in component state, no
 * server-side persistence — schema doesn't have a column for it).
 */

// ── Helpers ──────────────────────────────────────────────────────────────────

function getQuestIdFromPath() {
  const m = window.location.pathname.match(/^\/quests\/([a-zA-Z0-9_-]+)\/?$/);
  return m ? m[1] : "";
}

async function apiFetch(url, options = {}) {
  const headers = {
    ...(options.headers || {}),
    ...((window.MabuAuth && (await window.MabuAuth.authHeaders())) || {}),
  };
  return fetch(url, { ...options, headers });
}

function bgImage(url) { return url ? { backgroundImage: `url(${url})` } : null; }
function initialOf(s) { return ((s || "?")[0] || "?").toUpperCase(); }
function teamPillStyle(color) {
  const style = {
    color,
    borderColor: color,
    backgroundColor: color,
    opacity: 0.16,
  };
  if (/^#[0-9A-Fa-f]{6}$/.test(color)) {
    style.backgroundColor = `${color}22`;
    style.opacity = 1;
  }
  return style;
}

function formatWhen(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
    });
  } catch (e) { return iso; }
}

// ── Reply card ──────────────────────────────────────────────────────────────

function ReplyCard({ reply, canFulfill, onToggleFulfill, busy }) {
  return (
    <div className={`reply-card${reply.fulfills_quest ? " reply-card--fulfilled" : ""}`}>
      <div className="reply-card__head">
        <a
          href={reply.author_username ? `/user/${reply.author_username}` : "#"}
          className="reply-card__avatar"
          style={bgImage(reply.author_avatar_url)}
        >
          {!reply.author_avatar_url && initialOf(reply.author_username)}
        </a>
        <span className="reply-card__author">{reply.author_username || "—"}</span>
        <span className="reply-card__when">· {formatWhen(reply.created_at)}</span>
        {canFulfill && (
          <label className="fulfill-toggle" title="Toggle fulfills quest">
            <input
              type="checkbox"
              checked={reply.fulfills_quest}
              disabled={busy}
              onChange={(e) => onToggleFulfill && onToggleFulfill(reply, e.target.checked)}
            />
            <span>Fulfilled</span>
          </label>
        )}
      </div>
      {reply.author_teams && reply.author_teams.length > 0 && (
        <div className="reply-card__teams">
          {reply.author_teams.map((team) => (
            <span
              key={team.id}
              className="reply-card__team-pill"
              style={teamPillStyle(team.color || "#888")}
            >
              {team.name}
            </span>
          ))}
        </div>
      )}
      {reply.description && <div className="reply-card__text">{reply.description}</div>}
      {reply.img_url && (
        <img className="reply-card__img" src={reply.img_url} alt="" />
      )}
    </div>
  );
}

// ── Reply create modal ──────────────────────────────────────────────────────

function ReplyModal({ questId, onClose, onCreated }) {
  const [description, setDescription] = React.useState("");
  const [imageFile, setImageFile]     = React.useState(null);
  const [imagePreview, setImagePreview] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [msg, setMsg]   = React.useState(null);

  function onPickImage(e) {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    setImageFile(file);
    setImagePreview(URL.createObjectURL(file));
  }

  async function submit(e) {
    e.preventDefault();
    if (!description.trim() && !imageFile) {
      setMsg({ kind: "err", text: "Add a description, an image, or both." });
      return;
    }
    setBusy(true); setMsg(null);

    let img_url = "";
    if (imageFile) {
      const form = new FormData();
      form.append("image", imageFile);
      const upResp = await apiFetch("/api/reply-image", { method: "POST", body: form });
      if (!upResp.ok) {
        const data = await upResp.json().catch(() => ({}));
        setMsg({ kind: "err", text: `Image upload failed: ${data.error || upResp.status}` });
        setBusy(false);
        return;
      }
      ({ img_url } = await upResp.json());
    }

    const resp = await apiFetch("/api/quest-replies", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({
        quest_id:    questId,
        description: description.trim(),
        img_url,
      }),
    });
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      setMsg({ kind: "err", text: data.error || `Failed (${resp.status})` });
      setBusy(false);
      return;
    }
    onCreated && onCreated(await resp.json());
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="modal__close" onClick={onClose} aria-label="Close">×</button>
        <h3>Reply to this quest</h3>
        <form onSubmit={submit} className="email-form" autoComplete="off">
          <label>
            Description <span className="muted small">(or just attach an image)</span>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3} maxLength={1000}
              className="field-input"
              autoFocus
            />
          </label>
          <label>
            Image <span className="muted small">(optional)</span>
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
              {busy ? "Posting…" : "Post reply"}
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

// ── Edit quest modal (creator only) ─────────────────────────────────────────

function EditQuestModal({ quest, onClose, onSaved }) {
  const [description, setDescription] = React.useState(quest.description || "");
  const [imageFile, setImageFile]     = React.useState(null);
  const [imagePreview, setImagePreview] = React.useState(quest.img_url || "");
  const [keepImage, setKeepImage]     = React.useState(true);
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
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body:   JSON.stringify({ description: description.trim(), img_url }),
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
              rows={4} maxLength={1000}
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
            <img src={imagePreview} alt=""
                 style={{ maxWidth: "100%", borderRadius: "var(--radius)" }} />
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

// ── Replies tab body ────────────────────────────────────────────────────────

function RepliesTab({ questId, isCreator }) {
  const [replies, setReplies] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError]     = React.useState(null);
  const [busyId, setBusyId]   = React.useState(null);
  const [refresh, setRefresh] = React.useState(0);
  const [open, setOpen]       = React.useState(false);

  React.useEffect(() => {
    if (!questId) return;
    setLoading(true); setError(null);
    let cancelled = false;
    apiFetch(`/api/quests/${questId}/replies`)
      .then(async (resp) => {
        if (cancelled) return;
        if (!resp.ok) {
          const d = await resp.json().catch(() => ({}));
          setError(d.error || `Failed (${resp.status})`);
        } else {
          const d = await resp.json();
          setReplies(d.items || []);
        }
      })
      .catch((e) => { if (!cancelled) setError(String(e)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [questId, refresh]);

  async function toggleFulfill(reply, next) {
    setBusyId(reply.id);
    const resp = await apiFetch(`/api/quest-replies/${reply.id}`, {
      method:  "PUT",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ fulfills_quest: next }),
    });
    setBusyId(null);
    if (!resp.ok) {
      const d = await resp.json().catch(() => ({}));
      alert(d.error || `Failed (${resp.status})`);
      return;
    }
    const updated = await resp.json();
    setReplies((curr) => curr.map((r) => (r.id === updated.id ? updated : r)));
  }

  return (
    <div className="tab-body">
      <div className="tab-list">
        {loading && <p className="muted">Loading…</p>}
        {error && <p className="form-msg err">{error}</p>}
        {!loading && !error && replies.length === 0 && (
          <p className="muted">No replies yet. Be the first.</p>
        )}
        {replies.map((r) => (
          <ReplyCard
            key={r.id}
            reply={r}
            canFulfill={isCreator}
            busy={busyId === r.id}
            onToggleFulfill={toggleFulfill}
          />
        ))}
      </div>
      <button type="button" className="fab" onClick={() => setOpen(true)}>
        + Reply
      </button>
      {open && (
        <ReplyModal
          questId={questId}
          onClose={() => setOpen(false)}
          onCreated={() => {
            setOpen(false);
            setRefresh((n) => n + 1);
          }}
        />
      )}
    </div>
  );
}

// ── List tab body (participants) ────────────────────────────────────────────

function ParticipantsTab({ questId }) {
  const [items, setItems]     = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError]     = React.useState(null);

  React.useEffect(() => {
    if (!questId) return;
    setLoading(true); setError(null);
    let cancelled = false;
    apiFetch(`/api/quests/${questId}/participants`)
      .then(async (resp) => {
        if (cancelled) return;
        if (!resp.ok) {
          const d = await resp.json().catch(() => ({}));
          setError(d.error || `Failed (${resp.status})`);
        } else {
          const d = await resp.json();
          setItems(d.items || []);
        }
      })
      .catch((e) => { if (!cancelled) setError(String(e)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [questId]);

  return (
    <div className="tab-body">
      <div className="tab-list">
        {loading && <p className="muted">Loading…</p>}
        {error && <p className="form-msg err">{error}</p>}
        {!loading && !error && items.length === 0 && (
          <p className="muted">No one has joined yet.</p>
        )}
        {items.map((p) => (
          <div
            key={p.user_id}
            className={`participant-row${p.completed_at ? " participant-row--completed" : ""}`}
          >
            <a
              href={p.username ? `/user/${p.username}` : "#"}
              className="participant-row__avatar"
              style={bgImage(p.avatar_url)}
            >
              {!p.avatar_url && initialOf(p.username)}
            </a>
            <span className="participant-row__name">
              {p.username || <span className="muted">unknown</span>}
            </span>
            <span className="participant-row__when">
              {p.completed_at
                ? `completed ${formatWhen(p.completed_at)}`
                : `joined ${formatWhen(p.joined_at)}`}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Page entry point ─────────────────────────────────────────────────────────

function QuestDetailPageContent() {
  const questId = getQuestIdFromPath();

  const [session, setSession]     = React.useState(null);
  const [authReady, setAuthReady] = React.useState(false);

  const [quest, setQuest]         = React.useState(null);
  const [error, setError]         = React.useState(null);
  const [tab, setTab]             = React.useState("replies");
  const [editOpen, setEditOpen]   = React.useState(false);
  const [imageScale, setImageScale] = React.useState(100);

  React.useEffect(() => {
    if (!window.MabuAuth) { setAuthReady(true); return; }
    return window.MabuAuth.onAuthChange((s) => {
      setSession(s);
      setAuthReady(true);
    });
  }, []);

  const fetchQuest = React.useCallback(() => {
    if (!questId) { setError("Missing quest id in URL."); return Promise.resolve(); }
    return apiFetch(`/api/quests/${questId}`)
      .then(async (resp) => {
        if (!resp.ok) {
          const d = await resp.json().catch(() => ({}));
          setError(d.error || `Failed (${resp.status})`);
        } else {
          setQuest(await resp.json());
          setError(null);
        }
      })
      .catch((e) => setError(String(e)));
  }, [questId]);

  React.useEffect(() => { fetchQuest(); }, [fetchQuest]);

  if (!questId) return <p className="form-msg err">Missing quest id in URL.</p>;
  if (error)    return <p className="form-msg err">{error}</p>;
  if (!quest)   return <p className="muted">Loading…</p>;

  const isCreator = Boolean(
    session && session.user && session.user.id === quest.created_by
  );

  return (
    <div className="quest-page">
      {/* ── Top: quest info ─────────────────────────────────────────────── */}
      <section className="quest-info">
        <div className="quest-info__head">
          <h1 className="quest-info__title">{quest.title}</h1>
          {isCreator && (
            <button
              type="button"
              className="icon-btn"
              title="Edit description / image"
              onClick={() => setEditOpen(true)}
            >
              ✎
            </button>
          )}
        </div>
        <div className="quest-info__creator">
          by {quest.creator_username || "—"}
          {quest.hive_name && <span className="quest-info__hive-pill">{quest.hive_name}</span>}
          <span> · {formatWhen(quest.created_at)}</span>
        </div>
        {quest.description && (
          <div className="quest-info__desc">{quest.description}</div>
        )}
        {quest.img_url && (
          <>
            <div className="quest-info__image-wrap">
              <img
                className="quest-info__image"
                src={quest.img_url}
                alt=""
                style={{ width: `${imageScale}%`, maxWidth: `${imageScale}%` }}
              />
            </div>
            {isCreator && (
              <div className="image-scale-row" title="Resize the quest image (local view)">
                <span>Image size</span>
                <input
                  type="range"
                  min="20" max="100" step="5"
                  value={imageScale}
                  onChange={(e) => setImageScale(Number(e.target.value))}
                />
                <span className="mono">{imageScale}%</span>
              </div>
            )}
          </>
        )}
      </section>

      {/* ── Bottom: tabs ────────────────────────────────────────────────── */}
      <section className="quest-tabs-panel">
        <div className="tabs">
          <button
            type="button"
            className={`tab-btn${tab === "replies" ? " tab-btn--active" : ""}`}
            onClick={() => setTab("replies")}
          >Replies</button>
          <button
            type="button"
            className={`tab-btn${tab === "list" ? " tab-btn--active" : ""}`}
            onClick={() => setTab("list")}
          >List</button>
        </div>
        {tab === "replies"
          ? <RepliesTab questId={questId} isCreator={isCreator} />
          : <ParticipantsTab questId={questId} />}
      </section>

      {editOpen && (
        <EditQuestModal
          quest={quest}
          onClose={() => setEditOpen(false)}
          onSaved={(updated) => {
            setQuest((curr) => ({ ...(curr || {}), ...updated }));
            setEditOpen(false);
          }}
        />
      )}
    </div>
  );
}
