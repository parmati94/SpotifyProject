import Alpine from 'alpinejs';
import { api } from './api.js';
import { playlistActions } from './playlistActions.js';

document.addEventListener('alpine:init', () => {
  Alpine.data('app', () => ({
    // Playlist data + mutating actions (loaders, create/extend/delete) live in
    // their own module, spread in here so the markup sees one flat component.
    ...playlistActions(),

    // ── Auth ─────────────────────────────────────────────────────────────
    checking: true,        // initial /api/session probe in flight
    authenticated: false,

    // ── Toast (single global action-result banner) ───────────────────────
    actionResult: null,    // { ok, message }
    _toastTimer: null,

    // ── Confirm dialog (promise-based) ───────────────────────────────────
    confirmDialog: { show: false, title: '', message: '', confirmLabel: 'Confirm', danger: true, resolve: null },

    // ── Theme ────────────────────────────────────────────────────────────
    showSettings: false,
    theme: 'spotify',
    themes: [
      { id: 'spotify', label: 'Spotify', swatch: '#1db954' },
      { id: 'violet', label: 'Violet', swatch: '#8b5cf6' },
      { id: 'blue', label: 'Blue', swatch: '#3b82f6' },
      { id: 'amber', label: 'Amber', swatch: '#f59e0b' },
      { id: 'rose', label: 'Rose', swatch: '#f43f5e' },
    ],

    async init() {
      this.applyTheme(localStorage.getItem('sp-theme') || 'spotify');

      // React to the OAuth round-trip (?login=success|failure), then clean the URL.
      const params = new URLSearchParams(window.location.search);
      const login = params.get('login');
      if (login === 'failure') this._toast(false, 'Spotify connection failed. Please try again.');
      if (login) window.history.replaceState({}, '', window.location.pathname);

      await this.checkSession();
      this.checking = false;

      // Success toasts auto-dismiss; errors stay until dismissed.
      this.$watch('actionResult', (r) => {
        clearTimeout(this._toastTimer);
        if (r && r.ok && !r.sticky) this._toastTimer = setTimeout(() => { this.actionResult = null; }, 4500);
      });
    },

    async checkSession() {
      try {
        const { authenticated } = await api.session();
        this.authenticated = !!authenticated;
        if (this.authenticated) await this.loadPlaylists();
      } catch {
        this.authenticated = false;
      }
    },

    login() {
      window.location.href = '/login';
    },

    async logout() {
      try { await api.logout(); } catch { /* best effort */ }
      this.authenticated = false;
      this.playlists = [];
      this.showSettings = false;
      this._toast(true, 'Disconnected from Spotify.');
    },

    // ── Theme ────────────────────────────────────────────────────────────
    applyTheme(id) {
      if (!this.themes.some((t) => t.id === id)) id = 'spotify';
      this.theme = id;
      document.documentElement.setAttribute('data-theme', id);
      localStorage.setItem('sp-theme', id);
    },

    // ── Toast helper ─────────────────────────────────────────────────────
    // ok=false stays until dismissed; ok=true auto-dismisses unless opts.sticky
    // (used for "working…" toasts that a result toast later replaces).
    _toast(ok, message, opts = {}) {
      this.actionResult = { ok, message, sticky: !!opts.sticky };
    },

    // ── Confirm dialog ───────────────────────────────────────────────────
    showConfirm({ title, message, confirmLabel = 'Confirm', danger = true }) {
      return new Promise((resolve) => {
        this.confirmDialog = { show: true, title, message, confirmLabel, danger, resolve };
      });
    },
    confirmDialogAccept() { this.confirmDialog.resolve?.(true); this.confirmDialog.show = false; },
    confirmDialogCancel() { this.confirmDialog.resolve?.(false); this.confirmDialog.show = false; },
  }));
});

Alpine.start();
