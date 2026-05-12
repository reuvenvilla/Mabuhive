/**
 * public/js/NavBar.jsx
 * Loaded via <script type="text/babel"> — Babel standalone transforms JSX in-browser.
 * Depends on: React (global from CDN), optionally window.MabuAuth (for auth state).
 */

function NavBar({ activePage = "" }) {
  const links = [
    { href: "/",        label: "Home",    key: "home" },
    { href: "/hives",   label: "Hives",   key: "hives" },
    { href: "/quests",  label: "Quests",  key: "quests" },
    { href: "/journal", label: "Journal", key: "journal" },
    { href: "/user",    label: "Profile", key: "user" },
  ];

  // Optional auth widget — only renders if MabuAuth is loaded on this page.
  const [session, setSession] = React.useState(null);
  const [ready, setReady] = React.useState(!window.MabuAuth);

  React.useEffect(() => {
    if (!window.MabuAuth) return;
    const unsubscribe = window.MabuAuth.onAuthChange((s) => {
      setSession(s);
      setReady(true);
    });
    return unsubscribe;
  }, []);

  return (
    <header className="site-header">
      <a className="site-logo" href="/">MabuHive</a>
      <nav className="site-nav">
        {links.map(({ href, label, key }) => (
          <a
            key={key}
            href={href}
            className={`nav-link${activePage === key ? " active" : ""}`}
          >
            {label}
          </a>
        ))}
      </nav>
      {window.MabuAuth && ready && (
        <div className="site-auth">
          {session ? (
            <button
              className="auth-btn"
              onClick={async () => {
                await window.MabuAuth.signOut();
                window.location.reload();
              }}
            >
              Sign out
            </button>
          ) : (
            <span className="auth-muted">Signed out</span>
          )}
        </div>
      )}
    </header>
  );
}
