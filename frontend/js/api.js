/**
 * Generic fetch wrapper for the SpotifyProject API.
 * Throws on non-2xx with the server's `detail`; the thrown Error carries `.status`
 * so callers can react to 401 (session expired) specifically.
 */
async function apiFetch(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    credentials: 'same-origin',
    ...options,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });
  let data = null;
  try { data = await res.json(); } catch { /* some responses may be empty */ }
  if (!res.ok) {
    const detail = data?.detail;
    const message = typeof detail === 'string'
      ? detail
      : Array.isArray(detail) ? (detail[0]?.msg ?? 'Invalid request')
      : `Request failed (${res.status})`;
    const err = new Error(message);
    err.status = res.status;
    throw err;
  }
  return data;
}

export const api = {
  session: () => apiFetch('/api/session'),
  logout: () => apiFetch('/api/logout', { method: 'POST' }),
  playlists: () => apiFetch('/api/playlists'),
  createDaily: () => apiFetch('/api/playlists/daily', { method: 'POST' }),
  deleteDaily: () => apiFetch('/api/playlists/daily', { method: 'DELETE' }),
  extendWeekly: () => apiFetch('/api/playlists/weekly', { method: 'POST' }),
  createFromPlaylist: (body) =>
    apiFetch('/api/playlists/from-playlist', { method: 'POST', body }),
};
