/**
 * frontend/static/js/components/NavBar.jsx
 * Loaded via <script type="text/babel"> — Babel standalone transforms JSX in-browser.
 * Depends on: React (global from CDN)
 */

function NavBar({ activePage = "" }) {
  const links = [
    { href: "/",       label: "Home",    key: "home" },
    { href: "/hives",  label: "Hives",   key: "hives" },
    { href: "/quests", label: "Quests",  key: "quests" },
    { href: "/journal", label: "Journal", key: "journal" },
    { href: "/profile", label: "Profile", key: "profile" },
  ];

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
    </header>
  );
}
