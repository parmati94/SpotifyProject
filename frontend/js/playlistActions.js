import { api } from './api.js';

/**
 * Playlist data + the mutating actions, spread into the root `app` component.
 * Kept separate from app.js (auth/theme/toast/confirm shell) so each file stays
 * focused, mirroring the satisfactory-lens app.js + feature-module split.
 */
export function playlistActions() {
  return {
    // ── State ──────────────────────────────────────────────────────────────
    playlists: [],
    playlistsLoading: false,
    playlistSearch: '',
    sourceDropdownOpen: false,  // create-from-playlist source picker
    sourceSearch: '',
    actionLoading: false, // global mutex: one mutating action at a time
    busy: '',             // which action is running ('daily' | 'weekly' | 'delete' | 'from')
    createForm: { source: '', target: '', count: 60 },

    // ── Derived ──────────────────────────────────────────────────────────────
    // Plain methods, not getters: this object is SPREAD into the Alpine root
    // (...playlistActions()), and the spread operator evaluates getters once and
    // copies their value as a static property (freezing them). Methods copy fine.
    filteredPlaylists() {
      const q = this.playlistSearch.trim().toLowerCase();
      if (!q) return this.playlists;
      return this.playlists.filter((p) => p.name.toLowerCase().includes(q));
    },
    totalTracks() {
      return this.playlists.reduce((n, p) => n + (p.total_tracks || 0), 0);
    },

    // ── Loaders ────────────────────────────────────────────────────────────
    async loadPlaylists() {
      this.playlistsLoading = true;
      try {
        const data = await api.playlists();
        this.playlists = data.playlists ?? [];
      } catch (e) {
        this._handleError(e, 'Could not load your playlists.');
      } finally {
        this.playlistsLoading = false;
      }
    },

    // ── Actions ────────────────────────────────────────────────────────────
    async createDaily() {
      await this._runAction('daily', api.createDaily, 'Building your daily mix…');
    },

    async extendWeekly() {
      await this._runAction('weekly', api.extendWeekly, 'Extending your weekly playlist…');
    },

    async deleteDaily() {
      const ok = await this.showConfirm({
        title: 'Delete daily playlists?',
        message: "Removes every playlist named after today's date from your library. This can't be undone.",
        confirmLabel: 'Delete',
        danger: true,
      });
      if (!ok) return;
      await this._runAction('delete', api.deleteDaily, 'Deleting daily playlists…');
    },

    async createFromPlaylist() {
      const source = this.createForm.source;
      const target = this.createForm.target.trim();
      if (!source) return this._toast(false, 'Pick a source playlist first.');
      if (!target) return this._toast(false, 'Give your new playlist a name.');
      await this._runAction(
        'from',
        () => api.createFromPlaylist({
          source_playlist: source,
          target_playlist: target,
          num_songs: this.createForm.count,
        }),
        'Crafting your new playlist…',
        async () => {
          this.createForm.target = '';
          await this.loadPlaylists(); // reflect the new playlist in the browser
        },
      );
    },

    // ── Source selection (shared by the dropdown and the grid) ──────────────
    // The grid and the dropdown both call this, so they stay in sync.
    selectSource(name, { scroll = false } = {}) {
      this.createForm.source = name;
      this.sourceDropdownOpen = false;
      this.sourceSearch = '';
      if (scroll) {
        this.$nextTick(() => {
          document.getElementById('create-from-playlist')
            ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
      }
    },
    selectedSourcePlaylist() {
      return this.playlists.find((p) => p.name === this.createForm.source) || null;
    },
    sourceOptions() {
      const q = this.sourceSearch.trim().toLowerCase();
      if (!q) return this.playlists;
      return this.playlists.filter((p) => p.name.toLowerCase().includes(q));
    },

    // ── Internals ──────────────────────────────────────────────────────────
    // Runs a mutating action under the global mutex with a "working" toast,
    // then a success/error toast. `onSuccess` runs after a successful call.
    async _runAction(key, fn, workingMessage, onSuccess) {
      if (this.actionLoading) return;
      this.actionLoading = true;
      this.busy = key;
      this._toast(true, workingMessage, { sticky: true });
      try {
        const data = await fn();
        this._toast(true, data?.message ?? 'Done.');
        if (onSuccess) await onSuccess();
      } catch (e) {
        this._handleError(e, 'Something went wrong.');
      } finally {
        this.actionLoading = false;
        this.busy = '';
      }
    },

    _handleError(e, fallback) {
      if (e?.status === 401) {
        this.authenticated = false;
        this._toast(false, 'Your session expired — please reconnect Spotify.');
        return;
      }
      this._toast(false, e?.message || fallback);
    },
  };
}
