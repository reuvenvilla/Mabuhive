/**
 * frontend/static/js/utils.js
 * Plain JS utilities. Loaded on every page before any React/JSX.
 * Available as globals: apiFetch, formatDate, el
 */

"use strict";

/**
 * Fetch wrapper — parses JSON and throws on non-2xx with the server error message.
 */
async function apiFetch(url, options = {}) {
  const res  = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

/**
 * Format an ISO timestamp into a readable local date/time string.
 */
function formatDate(iso) {
  try {
    return new Date(iso).toLocaleString(undefined, {
      year: "numeric", month: "short", day: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

/**
 * Get element by ID — throws immediately if missing so bugs surface fast.
 */
function el(id) {
  const node = document.getElementById(id);
  if (!node) throw new Error(`#${id} not found in DOM`);
  return node;
}
