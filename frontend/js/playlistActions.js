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
    playlistTab: 'library',     // 'library' (user's own) | 'app' (made by this app)
    sourceDropdownOpen: false,  // create-from-playlist source picker
    sourceSearch: '',
    actionLoading: false, // global mutex: one mutating action at a time
    busy: '',             // which action is running ('daily'|'weekly'|'delete'|'from'|'vibe')
    createMode: 'playlist', // 'playlist' (seed from existing) | 'vibe' (free-text)
    createForm: { source: '', target: '', count: 60 },
    vibeForm: { description: '', count: 40, nameIt: true },

    // ── Derived ──────────────────────────────────────────────────────────────
    // Plain methods, not getters: this object is SPREAD into the Alpine root
    // (...playlistActions()), and the spread operator evaluates getters once and
    // copies their value as a static property (freezing them). Methods copy fine.
    // Playlists in the active tab (library = the user's own; app = made by this app),
    // then narrowed by the search box.
    filteredPlaylists() {
      const q = this.playlistSearch.trim().toLowerCase();
      return this.playlistsInTab(this.playlistTab).filter(
        (p) => !q || p.name.toLowerCase().includes(q),
      );
    },
    playlistsInTab(tab) {
      return this.playlists.filter((p) => (tab === 'app' ? p.created_by_app : !p.created_by_app));
    },
    tabCount(tab) {
      return this.playlistsInTab(tab).length;
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
      await this._runAction('daily', api.createDaily, 'Building your daily mix…',
        (data) => this._refreshAfterMutation(data));  // reflect the new playlist in the browser
    },

    async extendWeekly() {
      await this._runAction('weekly', api.extendWeekly, 'Extending your weekly playlist…',
        (data) => this._refreshAfterMutation(data));  // weekly may have just been created
    },

    async deleteDaily() {
      const ok = await this.showConfirm({
        title: 'Delete daily playlists?',
        message: "Removes every playlist named after today's date from your library. This can't be undone.",
        confirmLabel: 'Delete',
        danger: true,
      });
      if (!ok) return;
      await this._runAction('delete', api.deleteDaily, 'Deleting daily playlists…',
        () => this.loadPlaylists());  // drop the deleted playlists from the browser
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
        async (data) => {
          this.createForm.target = '';
          await this._refreshAfterMutation(data); // reflect the new playlist in the browser
        },
      );
    },

    async createVibe() {
      const description = this.vibeForm.description.trim();
      if (!description) return this._toast(false, 'Describe the vibe you want first.');
      await this._runAction(
        'vibe',
        () => api.createVibe({
          description,
          num_songs: this.vibeForm.count,
          name_it: this.vibeForm.nameIt,
          engine: this.vibe.active,       // remembered server-side for next time
          model: this.vibe.activeModel,   // ditto — the specific model within that engine
        }),
        'Conjuring your vibe…',
        async (data) => {
          this.vibeForm.description = '';
          await this._refreshAfterMutation(data); // reflect the new playlist in the browser
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
    // Reload the browser, then patch the affected playlist's count from the create
    // response. Spotify's playlist-list endpoint reports a stale 0 tracks for a few
    // seconds after creation, so without this the new card flashes "0 tracks" until a
    // later refresh. We only ever bump the count up, so a correct reload isn't clobbered.
    async _refreshAfterMutation(data) {
      await this.loadPlaylists();
      if (data?.total_tracks == null) return;
      // Match by id (names aren't unique — e.g. two dailies the same day); fall back to name.
      const p = data.id
        ? this.playlists.find((pl) => pl.id === data.id)
        : this.playlists.find((pl) => pl.name === data.name);
      if (p && (p.total_tracks || 0) < data.total_tracks) p.total_tracks = data.total_tracks;
    },

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
        if (onSuccess) await onSuccess(data);
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
