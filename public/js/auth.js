/**
 * public/js/auth.js
 *
 * Thin wrapper around supabase-js. Initialisation is async because the
 * Supabase URL + anon key come from /api/config (so we don't have to
 * hardcode them in the page).
 *
 * Exposes `window.MabuAuth`:
 *   .ready              -> Promise<SupabaseClient>   await before first use
 *   .client             -> SupabaseClient | null     populated once ready resolves
 *   .getSession()       -> Promise<Session | null>
 *   .onAuthChange(cb)   -> unsubscribe()
 *   .accessToken()      -> Promise<string | null>    JWT for Authorization: Bearer
 *   .authHeaders()      -> Promise<{Authorization?:string}>
 *   .signInWithOAuth(provider)       -> redirects to provider
 *   .signInWithPassword({email,pwd}) -> Promise
 *   .signUpWithPassword({email,pwd}) -> Promise
 *   .signOut()                       -> Promise
 *
 * The script tag for the supabase-js UMD bundle is loaded in user.html /
 * user-create.html (and any page that needs auth) — it exposes
 * `window.supabase`.
 */
(function () {
  "use strict";

  const listeners = new Set();
  let _client = null;
  let _config = null;

  async function init() {
    if (!window.supabase || !window.supabase.createClient) {
      throw new Error(
        "supabase-js not loaded. Add the <script> tag for @supabase/supabase-js."
      );
    }
    const resp = await fetch("/api/config");
    if (!resp.ok) throw new Error(`failed to fetch /api/config: ${resp.status}`);
    _config = await resp.json();

    if (!_config.supabase_url || !_config.supabase_anon_key) {
      throw new Error(
        "Supabase env vars missing on the server. " +
        "Set SUPABASE_URL and SUPABASE_ANON_KEY in your .env."
      );
    }

    _client = window.supabase.createClient(
      _config.supabase_url,
      _config.supabase_anon_key,
      {
        auth: {
          // Keep the user signed in across reloads.
          persistSession:  true,
          autoRefreshToken: true,
          // Supabase puts the token in the URL hash after OAuth — let
          // supabase-js parse + clear it for us.
          detectSessionInUrl: true,
        },
      }
    );

    // Re-broadcast auth changes to anyone who subscribed before init finished.
    _client.auth.onAuthStateChange((_event, session) => {
      listeners.forEach((cb) => {
        try { cb(session); } catch (e) { console.error("[MabuAuth] listener error:", e); }
      });
    });

    return _client;
  }

  const ready = init().catch((err) => {
    console.error("[MabuAuth] init failed:", err);
    throw err;
  });

  async function getSession() {
    await ready;
    const { data } = await _client.auth.getSession();
    return data.session || null;
  }

  function onAuthChange(cb) {
    listeners.add(cb);
    // Fire once with current state so subscribers don't have to special-case
    // "what's the state right now".
    getSession().then((s) => { try { cb(s); } catch (e) { console.error(e); } });
    return () => listeners.delete(cb);
  }

  async function accessToken() {
    const session = await getSession();
    return session ? session.access_token : null;
  }

  async function authHeaders() {
    const token = await accessToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  async function signInWithOAuth(provider) {
    await ready;
    return _client.auth.signInWithOAuth({
      provider,
      options: {
        // Come back to whatever page started the login.
        redirectTo: window.location.origin + window.location.pathname,
      },
    });
  }

  async function signInWithPassword({ email, password }) {
    await ready;
    return _client.auth.signInWithPassword({ email, password });
  }

  async function signUpWithPassword({ email, password }) {
    await ready;
    return _client.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: window.location.origin + window.location.pathname,
      },
    });
  }

  async function signOut() {
    await ready;
    return _client.auth.signOut();
  }

  window.MabuAuth = {
    ready,
    get client() { return _client; },
    getSession,
    onAuthChange,
    accessToken,
    authHeaders,
    signInWithOAuth,
    signInWithPassword,
    signUpWithPassword,
    signOut,
  };
})();
