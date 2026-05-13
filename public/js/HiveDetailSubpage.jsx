/**
 * public/js/HiveDetailSubpage.jsx
 *
 * The /hives/<id> page.
 *
 * Layout (wide):
 *   ┌── main ─────────────────────────┐ ┌─ side ─┐
 *   │ [Explore][My Quests][Teams]     │ │ Hive   │
 *   │ ┌ quest cards / teams list ┐    │ │ People │
 *   │ │ ...                      │    │ │ <card> │
 *   │ └  + Create floating btn   ┘    │ └────────┘
 *   └────────────────────────────────┘
 * Narrow: main on top, side panel below.
 *
 * The side panel toggles between two modes: Hive (info card with logo
 * + count + name + description) and People (members list, admins first,
 * then alphabetical).
 *
 * Main tabs:
 *   - Explore   — joinable quests (paginated, FAB opens quest modal)
 *   - My Quests — quests I joined but haven't completed (FAB opens quest modal)
 *   - Teams     — team cards in their assigned color, expandable to show
 *                 members. FAB opens team modal.
 *
 * Pencil button on each quest card I created lets me edit description +
 * image (the same upload endpoint that quest creation uses).
 */

// ── Helpers ──────────────────────────────────────────────────────────────────

function getHiveIdFromPath() {
  const m = window.location.pathname.match(/^\/hives\/([a-zA-Z0-9_-]+)\/?$/);
  return m ? m[1] : "";
}

async function apiFetch(url, options = {}) {
  const headers = {
    ...(options.headers || {}),
    ...((window.MabuAuth && (await window.MabuAuth.authHeaders())) || {}),
  };
  return fetch(url, { ...options, headers });
}

function initialOf(s) {
  return ((s || "?")[0] || "?").toUpperCase();
}

function bgImage(url) {
  return url ? { backgroundImage: `url(${url})` } : null;
}

// ── Hive info card + members list (side panel content) ──────────────────────

function HiveInfoCard({ hive, session, onEdit, onMembershipChanged }) {
  const [busy, setBusy] = React.useState(false);
  const [msg, setMsg]   = React.useState(null);

  if (!hive) return <p className="muted">Loading…</p>;

  const isAdmin     = hive.my_role === "admin";
  const isMember    = Boolean(hive.my_role);
  const signedIn    = Boolean(session && session.user);

  async function joinOrLeave() {
    setBusy(true); setMsg(null);
    const endpoint = isMember
      ? `/api/hives/${hive.id}/leave`
      : `/api/hives/${hive.id}/join`;
    const resp = await apiFetch(endpoint, { method: "POST" });
    setBusy(false);
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      setMsg({ kind: "err", text: data.error || `Failed (${resp.status})` });
      return;
    }
    onMembershipChanged && onMembershipChanged();
  }

  return (
    <div className="hive-info">
      <div className="hive-info__head">
        <div className="hive-info__logo" style={bgImage(hive.img_url)}>
          {!hive.img_url && (
            <span className="hive-info__logo-fallback">{initialOf(hive.name)}</span>
          )}
        </div>
        <div className="hive-info__count">
          {hive.member_count} member{hive.member_count === 1 ? "" : "s"}
        </div>
        {isAdmin && (
          <button
            type="button"
            className="icon-btn"
            title="Edit hive description / logo"
            style={{ marginLeft: "auto" }}
            onClick={() => onEdit && onEdit()}
          >
            ✎
          </button>
        )}
      </div>

      {/* Join / Leave sits right under the member-count badge. */}
      {signedIn && (
        <div className="membership-row">
          <button
            type="button"
            className={`${isMember ? "secondary-btn" : "primary-btn"} membership-btn`}
            onClick={joinOrLeave}
            disabled={busy}
          >
            {busy
              ? (isMember ? "Leaving…" : "Joining…")
              : (isMember ? "Leave hive" : "Join hive")}
          </button>
          {msg && <p className={`form-msg ${msg.kind}`}>{msg.text}</p>}
        </div>
      )}

      <div className="hive-info__name">{hive.name}</div>
      <div className="hive-info__desc">
        {hive.description || <span className="muted">No description.</span>}
      </div>
    </div>
  );
}

function MembersList({ hiveId }) {
  const [members, setMembers] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError]     = React.useState(null);

  React.useEffect(() => {
    if (!hiveId) return;
    setLoading(true); setError(null);
    let cancelled = false;
    apiFetch(`/api/hives/${hiveId}/members`)
      .then(async (resp) => {
        if (cancelled) return;
        if (!resp.ok) {
          const data = await resp.json().catch(() => ({}));
          setError(data.error || `Failed (${resp.status})`);
        } else {
          const data = await resp.json();
          setMembers(data.items || []);
        }
      })
      .catch((e) => { if (!cancelled) setError(String(e)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [hiveId]);

  if (loading) return <p className="muted">Loading…</p>;
  if (error)   return <p className="form-msg err">{error}</p>;
  if (!members.length) return <p className="muted">No members yet.</p>;

  return (
    <div className="members-list">
      {members.map((m) => (
        <a
          key={m.user_id}
          href={m.username ? `/user/${m.username}` : "#"}
          className="member-row"
          style={{ textDecoration: "none", color: "inherit" }}
        >
          <div className="member-row__avatar" style={bgImage(m.avatar_url)}>
            {!m.avatar_url && initialOf(m.username)}
          </div>
          <span className="member-row__name">
            {m.username || <span className="muted">unknown</span>}
          </span>
          {m.role === "admin" && <span className="badge badge--admin">admin</span>}
        </a>
      ))}
    </div>
  );
}

// ── Quest card (used in Explore, My Quests) ─────────────────────────────────

function QuestCard({ quest, session, onJoin, onEdit }) {
  const mine = session && session.user && session.user.id === quest.created_by;
  return (
    <div className="quest-card">
      <div className="quest-card__head">
        <a href={`/quests/${quest.id}`} className="quest-card__title">
          {quest.title}
        </a>
        {mine && (
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
      </div>
      {quest.description && (
        <div className="quest-card__desc">{quest.description}</div>
      )}
      {onJoin && (
        <div className="quest-card__actions">
          <button
            type="button"
            className="primary-btn"
            onClick={() => onJoin(quest)}
          >
            Join
          </button>
        </div>
      )}
    </div>
  );
}

// ── Quests tab (Explore + My Quests share this) ─────────────────────────────

function QuestsTab({ hiveId, kind, session, onCreateClick, refreshKey }) {
  const [items, setItems]       = React.useState([]);
  const [page, setPage]         = React.useState(1);
  const [hasMore, setHasMore]   = React.useState(false);
  const [loading, setLoading]   = React.useState(false);
  const [error, setError]       = React.useState(null);
  const [editing, setEditing]   = React.useState(null);
  const containerRef = React.useRef(null);
  const [pageSize, setPageSize] = React.useState(7);

  // Auto-fit page size (cap at 7).
  React.useEffect(() => {
    if (!containerRef.current || typeof ResizeObserver === "undefined") return;
    const CARD = 110;
    const RESERVED = 70;
    const update = (h) => {
      setPageSize(Math.max(1, Math.min(7, Math.floor((h - RESERVED) / CARD))));
    };
    update(containerRef.current.clientHeight);
    const ro = new ResizeObserver(([e]) => update(e.contentRect.height));
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  React.useEffect(() => { setPage(1); }, [kind, pageSize, refreshKey]);

  // Fetch the list whenever the inputs change.
  React.useEffect(() => {
    if (!hiveId) return;
    setLoading(true); setError(null);
    let cancelled = false;
    const url = new URL(`/api/hives/${hiveId}/quests`, window.location.origin);
    url.searchParams.set("type", kind);
    url.searchParams.set("page", String(page));
    url.searchParams.set("size", String(pageSize));
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
  }, [hiveId, kind, page, pageSize, refreshKey]);

  async function joinQuest(quest) {
    const resp = await apiFetch(`/api/quests/${quest.id}/join`, { method: "POST" });
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      alert(data.error || `Join failed (${resp.status})`);
      return;
    }
    // Remove from current page (it's no longer "joinable").
    setItems((curr) => curr.filter((q) => q.id !== quest.id));
  }

  return (
    <div className="tab-body" ref={containerRef}>
      <div className="tab-list">
        {loading && <p className="muted">Loading…</p>}
        {error && <p className="form-msg err">{error}</p>}
        {!loading && !error && items.length === 0 && (
          <p className="muted">
            {kind === "joined"
              ? "No active quests you've joined here."
              : "No quests to show."}
          </p>
        )}
        {items.map((q) => (
          <QuestCard
            key={q.id}
            quest={q}
            session={session}
            onJoin={kind === "joinable" ? joinQuest : null}
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
      <button type="button" className="fab" onClick={onCreateClick}>
        + Create quest
      </button>
      {editing && (
        <EditQuestModal
          quest={editing}
          onClose={() => setEditing(null)}
          onSaved={(updated) => {
            setItems((curr) => curr.map((q) => (q.id === updated.id ? { ...q, ...updated } : q)));
            setEditing(null);
          }}
        />
      )}
    </div>
  );
}

// ── Teams tab ────────────────────────────────────────────────────────────────

function TeamCard({ team }) {
  const [open, setOpen] = React.useState(false);
  return (
    <div
      className="team-card"
      style={{ background: team.color || "#333333" }}
      onClick={() => setOpen((v) => !v)}
    >
      <div className="team-card__head">
        <span className="team-card__name">{team.name}</span>
        <span className="team-card__count">
          {team.member_count} member{team.member_count === 1 ? "" : "s"}
        </span>
      </div>
      {open && (
        <div className="team-card__members" onClick={(e) => e.stopPropagation()}>
          {team.members && team.members.length > 0 ? (
            team.members.map((m) => (
              <div key={m.user_id} className="team-member">
                <div className="team-member__avatar" style={bgImage(m.avatar_url)}>
                  {!m.avatar_url && initialOf(m.username)}
                </div>
                <span>{m.username || "—"}</span>
              </div>
            ))
          ) : (
            <div className="muted" style={{ color: "rgba(255,255,255,0.85)" }}>
              No members yet.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function TeamsTab({ hiveId, onCreateClick, refreshKey }) {
  const [teams, setTeams]     = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError]     = React.useState(null);

  React.useEffect(() => {
    if (!hiveId) return;
    setLoading(true); setError(null);
    let cancelled = false;
    apiFetch(`/api/hives/${hiveId}/teams`)
      .then(async (resp) => {
        if (cancelled) return;
        if (!resp.ok) {
          const data = await resp.json().catch(() => ({}));
          setError(data.error || `Failed (${resp.status})`);
        } else {
          const data = await resp.json();
          setTeams(data.items || []);
        }
      })
      .catch((e) => { if (!cancelled) setError(String(e)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [hiveId, refreshKey]);

  return (
    <div className="tab-body">
      <div className="tab-list">
        {loading && <p className="muted">Loading…</p>}
        {error && <p className="form-msg err">{error}</p>}
        {!loading && !error && teams.length === 0 && (
          <p className="muted">No teams yet. Be the first to create one.</p>
        )}
        {teams.map((t) => <TeamCard key={t.id} team={t} />)}
      </div>
      <button type="button" className="fab" onClick={onCreateClick}>
        + Create team
      </button>
    </div>
  );
}

// ── Quest creation modal ────────────────────────────────────────────────────

function CreateQuestModal({ hiveId, onClose, onCreated }) {
  const [title, setTitle]             = React.useState("");
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
    if (!title.trim()) { setMsg({ kind: "err", text: "Title is required." }); return; }
    setBusy(true); setMsg(null);

    let img_url = "";
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

    const resp = await apiFetch("/api/quests", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({
        hive_id:     hiveId,
        title:       title.trim(),
        description: description.trim(),
        img_url,
      }),
    });
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      setMsg({ kind: "err", text: data.error || `Create failed (${resp.status})` });
      setBusy(false);
      return;
    }
    const created = await resp.json();
    onCreated && onCreated(created);
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="modal__close" onClick={onClose} aria-label="Close">×</button>
        <h3>Create a quest</h3>
        <form onSubmit={submit} className="email-form" autoComplete="off">
          <label>
            Title
            <input
              type="text" required value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={128} autoFocus
            />
          </label>
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
              {busy ? "Creating…" : "Create quest"}
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

// ── Quest edit modal (pencil on own quest) ──────────────────────────────────

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

    let img_url = keepImage ? quest.img_url : "";
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
    const updated = await resp.json();
    onSaved && onSaved(updated);
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

// ── Hive edit modal (admin-only, /hives/:id only) ───────────────────────────

function EditHiveModal({ hive, onClose, onSaved }) {
  const [description, setDescription]   = React.useState(hive.description || "");
  const [logoFile, setLogoFile]         = React.useState(null);
  const [logoPreview, setLogoPreview]   = React.useState(hive.img_url || "");
  const [keepLogo, setKeepLogo]         = React.useState(true);
  const [busy, setBusy] = React.useState(false);
  const [msg, setMsg]   = React.useState(null);
  const fileInputRef = React.useRef(null);

  function onPickLogo(e) {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    setLogoFile(file);
    setKeepLogo(false);
    setLogoPreview(URL.createObjectURL(file));
  }

  async function submit(e) {
    e.preventDefault();
    setBusy(true); setMsg(null);

    let img_url = keepLogo ? (hive.img_url || "") : "";
    if (logoFile) {
      const form = new FormData();
      form.append("logo", logoFile);
      const upResp = await apiFetch("/api/hive-logo", { method: "POST", body: form });
      if (!upResp.ok) {
        const data = await upResp.json().catch(() => ({}));
        setMsg({ kind: "err", text: `Logo upload failed: ${data.error || upResp.status}` });
        setBusy(false);
        return;
      }
      ({ img_url } = await upResp.json());
    }

    const resp = await apiFetch(`/api/hives/${hive.id}`, {
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
        <h3>Edit hive</h3>
        <form onSubmit={submit} className="email-form" autoComplete="off">
          <div className="create-avatar-row">
            <div
              className="avatar"
              style={logoPreview ? { backgroundImage: `url(${logoPreview})` } : null}
            >
              {!logoPreview && (
                <span className="avatar-placeholder">{initialOf(hive.name)}</span>
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
              disabled={busy}
            >
              {logoFile ? "Replace logo" : "Pick new logo"}
            </button>
          </div>

          <label>
            Description
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={4} maxLength={1000}
              className="field-input"
            />
          </label>

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

// ── Team creation modal ─────────────────────────────────────────────────────

function CreateTeamModal({ hiveId, onClose, onCreated }) {
  const [name, setName]   = React.useState("");
  const [color, setColor] = React.useState("#3b82f6");
  const [busy, setBusy]   = React.useState(false);
  const [msg, setMsg]     = React.useState(null);
  const colorRef = React.useRef(null);

  async function submit(e) {
    e.preventDefault();
    if (!name.trim()) { setMsg({ kind: "err", text: "Team name is required." }); return; }
    setBusy(true); setMsg(null);

    const resp = await apiFetch("/api/teams", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ hive_id: hiveId, name: name.trim(), color }),
    });
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      setMsg({ kind: "err", text: data.error || `Create failed (${resp.status})` });
      setBusy(false);
      return;
    }
    const created = await resp.json();
    onCreated && onCreated(created);
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="modal__close" onClick={onClose} aria-label="Close">×</button>
        <h3>Create a team</h3>
        <form onSubmit={submit} className="email-form" autoComplete="off">
          <label>
            Team name
            <input
              type="text" required value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={64} autoFocus
            />
          </label>
          <div className="color-row">
            <div className="color-swatch" style={{ background: color }} />
            <input
              ref={colorRef}
              type="color"
              value={color}
              onChange={(e) => setColor(e.target.value)}
              className="color-input"
            />
            <button
              type="button"
              className="secondary-btn"
              onClick={() => colorRef.current && colorRef.current.click()}
            >
              Pick a color!
            </button>
            <span className="muted small mono">{color}</span>
          </div>
          <div className="actions">
            <button type="submit" className="primary-btn" disabled={busy}>
              {busy ? "Creating…" : "Create team"}
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

// ── Page entry point ─────────────────────────────────────────────────────────

function HiveDetailPageContent() {
  const hiveId = getHiveIdFromPath();

  const [session, setSession]     = React.useState(null);
  const [authReady, setAuthReady] = React.useState(false);

  const [hive, setHive]           = React.useState(null);
  const [hiveError, setHiveError] = React.useState(null);

  const [sideTab, setSideTab] = React.useState("hive");      // "hive" | "people"
  const [mainTab, setMainTab] = React.useState("explore");    // "explore" | "joined" | "teams"

  const [questModalOpen, setQuestModalOpen] = React.useState(false);
  const [teamModalOpen, setTeamModalOpen]   = React.useState(false);
  const [hiveEditOpen, setHiveEditOpen]     = React.useState(false);

  // Forces a tab refetch after a create/join.
  const [questsRefresh, setQuestsRefresh] = React.useState(0);
  const [teamsRefresh, setTeamsRefresh]   = React.useState(0);

  React.useEffect(() => {
    if (!window.MabuAuth) { setAuthReady(true); return; }
    return window.MabuAuth.onAuthChange((s) => {
      setSession(s);
      setAuthReady(true);
    });
  }, []);

  const fetchHive = React.useCallback(() => {
    if (!hiveId) { setHiveError("Missing hive id in URL."); return Promise.resolve(); }
    return apiFetch(`/api/hives/${hiveId}`)
      .then(async (resp) => {
        if (!resp.ok) {
          const data = await resp.json().catch(() => ({}));
          setHiveError(data.error || `Failed (${resp.status})`);
        } else {
          setHive(await resp.json());
          setHiveError(null);
        }
      })
      .catch((e) => setHiveError(String(e)));
  }, [hiveId]);

  // Initial fetch (and refetch whenever session changes so my_role is fresh).
  React.useEffect(() => {
    fetchHive();
  }, [fetchHive, session && session.user && session.user.id]);

  if (!hiveId)   return <p className="form-msg err">Missing hive id in URL.</p>;
  if (hiveError) return <p className="form-msg err">{hiveError}</p>;

  return (
    <div className="hive-page">
      <div className="main-col">
        <div className="tabs">
          <button
            type="button"
            className={`tab-btn${mainTab === "explore" ? " tab-btn--active" : ""}`}
            onClick={() => setMainTab("explore")}
          >Explore</button>
          <button
            type="button"
            className={`tab-btn${mainTab === "joined" ? " tab-btn--active" : ""}`}
            onClick={() => setMainTab("joined")}
          >My Quests</button>
          <button
            type="button"
            className={`tab-btn${mainTab === "teams" ? " tab-btn--active" : ""}`}
            onClick={() => setMainTab("teams")}
          >Teams</button>
        </div>

        {mainTab === "explore" && (
          <QuestsTab
            hiveId={hiveId}
            kind="joinable"
            session={session}
            refreshKey={questsRefresh}
            onCreateClick={() => setQuestModalOpen(true)}
          />
        )}
        {mainTab === "joined" && (
          <QuestsTab
            hiveId={hiveId}
            kind="joined"
            session={session}
            refreshKey={questsRefresh}
            onCreateClick={() => setQuestModalOpen(true)}
          />
        )}
        {mainTab === "teams" && (
          <TeamsTab
            hiveId={hiveId}
            refreshKey={teamsRefresh}
            onCreateClick={() => setTeamModalOpen(true)}
          />
        )}
      </div>

      <aside className="side-col">
        <div className="side-toggle">
          <button
            type="button"
            className={`side-toggle__btn${sideTab === "hive" ? " side-toggle__btn--active" : ""}`}
            onClick={() => setSideTab("hive")}
          >Hive</button>
          <button
            type="button"
            className={`side-toggle__btn${sideTab === "people" ? " side-toggle__btn--active" : ""}`}
            onClick={() => setSideTab("people")}
          >People</button>
        </div>
        <section className="side-panel">
          <div className="side-panel__body">
            {sideTab === "hive"   && (
              <HiveInfoCard
                hive={hive}
                session={session}
                onEdit={() => setHiveEditOpen(true)}
                onMembershipChanged={fetchHive}
              />
            )}
            {sideTab === "people" && <MembersList hiveId={hiveId} key={hive ? hive.member_count : 0} />}
          </div>
        </section>
      </aside>

      {questModalOpen && (
        <CreateQuestModal
          hiveId={hiveId}
          onClose={() => setQuestModalOpen(false)}
          onCreated={() => {
            setQuestModalOpen(false);
            setQuestsRefresh((n) => n + 1);
          }}
        />
      )}
      {teamModalOpen && (
        <CreateTeamModal
          hiveId={hiveId}
          onClose={() => setTeamModalOpen(false)}
          onCreated={() => {
            setTeamModalOpen(false);
            setTeamsRefresh((n) => n + 1);
          }}
        />
      )}
      {hiveEditOpen && hive && (
        <EditHiveModal
          hive={hive}
          onClose={() => setHiveEditOpen(false)}
          onSaved={(updated) => {
            setHive((curr) => ({ ...(curr || {}), ...updated }));
            setHiveEditOpen(false);
          }}
        />
      )}
    </div>
  );
}
