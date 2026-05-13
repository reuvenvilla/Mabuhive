/**
 * public/js/HivesSubpage.jsx
 *
 * The /hives page. Three regions:
 *   - top: search bar (filters both panels by hive name) + "+ Create" button
 *   - left/upper: "My Hives" — all hives the signed-in user belongs to,
 *     vertically scrolling, scrolling constrained to the panel
 *   - right/lower: "Discovery" — paginated, page size auto-fitted to the
 *     panel's vertical space; < Back / Forward > buttons fetch new batches
 *
 * Search behaviour: blank string = default (everything for me, page 1 for
 * discovery). Non-blank = case-insensitive substring match on hive name.
 *
 * All cards link out to /hives/<id> with a plain <a href>.
 */

// ── Helpers ──────────────────────────────────────────────────────────────────

async function apiFetch(url, options = {}) {
  const headers = {
    ...(options.headers || {}),
    ...((window.MabuAuth && (await window.MabuAuth.authHeaders())) || {}),
  };
  return fetch(url, { ...options, headers });
}

function useDebouncedValue(value, ms = 250) {
  const [debounced, setDebounced] = React.useState(value);
  React.useEffect(() => {
    const id = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(id);
  }, [value, ms]);
  return debounced;
}

// ── Hive card ────────────────────────────────────────────────────────────────

function HiveCard({ hive }) {
  const initial = (hive.name || "?")[0].toUpperCase();
  return (
    <a href={`/hives/${hive.id}`} className="hive-card">
      <div
        className="hive-card__logo"
        style={hive.img_url ? { backgroundImage: `url(${hive.img_url})` } : null}
      >
        {!hive.img_url && (
          <span className="hive-card__logo-fallback">{initial}</span>
        )}
      </div>
      <div className="hive-card__body">
        <div className="hive-card__name">{hive.name}</div>
        <div className="hive-card__meta">
          {hive.member_count} member{hive.member_count === 1 ? "" : "s"}
          {hive.my_role === "admin" && <span className="badge badge--admin">admin</span>}
        </div>
        <div className="hive-card__desc">{hive.description}</div>
      </div>
    </a>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

function HivesPageContent() {
  const [session, setSession]     = React.useState(null);
  const [authReady, setAuthReady] = React.useState(false);

  const [search, setSearch] = React.useState("");
  const debouncedSearch = useDebouncedValue(search, 250);

  // ── My Hives ──────────────────────────────────────────────────────────
  const [myHives, setMyHives]     = React.useState([]);
  const [myLoading, setMyLoading] = React.useState(false);
  const [myError, setMyError]     = React.useState(null);

  // ── Discovery ─────────────────────────────────────────────────────────
  const [discovery, setDiscovery]               = React.useState([]);
  const [discoveryPage, setDiscoveryPage]       = React.useState(1);
  const [discoveryHasMore, setDiscoveryHasMore] = React.useState(false);
  const [discoveryLoading, setDiscoveryLoading] = React.useState(false);
  const [discoveryError, setDiscoveryError]     = React.useState(null);

  const discoveryRef = React.useRef(null);
  const [discoverySize, setDiscoverySize] = React.useState(5);

  // ── Auth subscription ────────────────────────────────────────────────
  React.useEffect(() => {
    if (!window.MabuAuth) { setAuthReady(true); return; }
    return window.MabuAuth.onAuthChange((s) => {
      setSession(s);
      setAuthReady(true);
    });
  }, []);

  // ── Auto-fit Discovery page size to its panel ────────────────────────
  React.useEffect(() => {
    if (!discoveryRef.current || typeof ResizeObserver === "undefined") return;
    const CARD_HEIGHT = 96;   // approx hive card height in px
    const RESERVED    = 80;   // header + pager + padding allowance
    const update = (height) => {
      setDiscoverySize(Math.max(1, Math.floor((height - RESERVED) / CARD_HEIGHT)));
    };
    update(discoveryRef.current.clientHeight);
    const ro = new ResizeObserver(([entry]) => update(entry.contentRect.height));
    ro.observe(discoveryRef.current);
    return () => ro.disconnect();
  }, [authReady]);

  // Reset to page 1 whenever the search query changes. NOT keyed on
  // discoverySize: ResizeObserver can fire late (scrollbar appearing
  // after a fresh batch loads, grid reflow, etc.) and re-including it
  // here caused Forward to bounce back to page 1.
  React.useEffect(() => {
    setDiscoveryPage(1);
  }, [debouncedSearch]);

  // ── Fetch My Hives ───────────────────────────────────────────────────
  React.useEffect(() => {
    if (!authReady) return;
    if (!session) { setMyHives([]); setMyError(null); return; }

    setMyLoading(true); setMyError(null);
    const url = new URL("/api/hives/me", window.location.origin);
    if (debouncedSearch) url.searchParams.set("q", debouncedSearch);

    let cancelled = false;
    apiFetch(url.toString())
      .then(async (resp) => {
        if (cancelled) return;
        if (!resp.ok) {
          const data = await resp.json().catch(() => ({}));
          setMyError(data.error || `Failed (${resp.status})`);
          setMyHives([]);
        } else {
          const data = await resp.json();
          setMyHives(data.items || []);
        }
      })
      .catch((e) => { if (!cancelled) setMyError(String(e)); })
      .finally(() => { if (!cancelled) setMyLoading(false); });

    return () => { cancelled = true; };
  }, [authReady, session && session.user && session.user.id, debouncedSearch]);

  // ── Fetch Discovery ──────────────────────────────────────────────────
  React.useEffect(() => {
    if (!authReady) return;

    setDiscoveryLoading(true); setDiscoveryError(null);
    const url = new URL("/api/hives", window.location.origin);
    url.searchParams.set("page", String(discoveryPage));
    url.searchParams.set("size", String(discoverySize));
    if (debouncedSearch) url.searchParams.set("q", debouncedSearch);

    let cancelled = false;
    apiFetch(url.toString())
      .then(async (resp) => {
        if (cancelled) return;
        if (!resp.ok) {
          const data = await resp.json().catch(() => ({}));
          setDiscoveryError(data.error || `Failed (${resp.status})`);
          setDiscovery([]); setDiscoveryHasMore(false);
        } else {
          const data = await resp.json();
          setDiscovery(data.items || []);
          setDiscoveryHasMore(Boolean(data.has_more));
        }
      })
      .catch((e) => { if (!cancelled) setDiscoveryError(String(e)); })
      .finally(() => { if (!cancelled) setDiscoveryLoading(false); });

    return () => { cancelled = true; };
  }, [authReady, debouncedSearch, discoveryPage, discoverySize]);

  // ── Render ───────────────────────────────────────────────────────────
  return (
    <div className="hives-layout">
      {/* Top: search + create */}
      <div className="hives-search">
        <input
          type="search"
          className="hives-search__input"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search hives by name…"
          aria-label="Search hives"
        />
        <a href="/hives/create" className="primary-btn">+ Create hive</a>
      </div>

      {/* Left/upper: My Hives */}
      <section className="hives-panel hives-panel--mine">
        <header className="hives-panel__title">My Hives</header>
        <div className="hives-panel__body hives-panel__body--scroll">
          {!session && (
            <p className="muted">Sign in to see hives you've joined.</p>
          )}
          {session && myLoading && <p className="muted">Loading…</p>}
          {session && myError && <p className="form-msg err">{myError}</p>}
          {session && !myLoading && !myError && myHives.length === 0 && (
            <p className="muted">
              {debouncedSearch
                ? "No hives match that search."
                : "You haven't joined any hives yet."}
            </p>
          )}
          {myHives.map((h) => <HiveCard key={h.id} hive={h} />)}
        </div>
      </section>

      {/* Right/lower: Discovery */}
      <section className="hives-panel hives-panel--discovery" ref={discoveryRef}>
        <header className="hives-panel__title">Discovery</header>
        <div className="hives-panel__body">
          {discoveryLoading && <p className="muted">Loading…</p>}
          {discoveryError && <p className="form-msg err">{discoveryError}</p>}
          {!discoveryLoading && !discoveryError && discovery.length === 0 && (
            <p className="muted">
              {debouncedSearch ? "No hives match that search." : "No hives yet."}
            </p>
          )}
          {discovery.map((h) => <HiveCard key={h.id} hive={h} />)}
        </div>
        <footer className="hives-panel__pager">
          <button
            type="button"
            className="secondary-btn small"
            disabled={discoveryPage <= 1 || discoveryLoading}
            onClick={() => setDiscoveryPage((p) => Math.max(1, p - 1))}
          >
            ‹ Back
          </button>
          <span className="muted small">Page {discoveryPage}</span>
          <button
            type="button"
            className="secondary-btn small"
            disabled={!discoveryHasMore || discoveryLoading}
            onClick={() => setDiscoveryPage((p) => p + 1)}
          >
            Forward ›
          </button>
        </footer>
      </section>
    </div>
  );
}
