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
    devAuth: false,        // dev box: route "Connect" through the refresh-token bypass

    // ── Toast (single global action-result banner) ───────────────────────
    actionResult: null,    // { ok, message }
    _toastTimer: null,

    // ── Confirm dialog (promise-based) ───────────────────────────────────
    confirmDialog: { show: false, title: '', message: '', confirmLabel: 'Confirm', danger: true, resolve: null },

    // ── Recommendation engine (per-session, server-backed) ──────────────
    recommender: { active: null, available: [], switching: false },

    // ── Vibe mode LLM (per-session; empty `available` ⇒ vibe hidden) ─────
    vibe: { active: null, available: [] },

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
      this.loadRecommender();  // app config, not gated on auth; fine to fire after probe
      this.loadVibe();         // ditto — populates the vibe panel's LLM picker

      // Success toasts auto-dismiss; errors stay until dismissed.
      this.$watch('actionResult', (r) => {
        clearTimeout(this._toastTimer);
        if (r && r.ok && !r.sticky) this._toastTimer = setTimeout(() => { this.actionResult = null; }, 4500);
      });
    },

    async checkSession() {
      try {
        const { authenticated, dev } = await api.session();
        this.authenticated = !!authenticated;
        this.devAuth = !!dev;
        if (this.authenticated) await this.loadPlaylists();
      } catch {
        this.authenticated = false;
      }
    },

    login() {
      // Dev box: /dev/login seeds the session from DEV_REFRESH_TOKEN (no OAuth round-trip,
      // which a non-loopback http origin can't do anyway). Prod: real Spotify OAuth.
      window.location.href = this.devAuth ? '/dev/login' : '/login';
    },

    async logout() {
      try { await api.logout(); } catch { /* best effort */ }
      this.authenticated = false;
      this.playlists = [];
      this.showSettings = false;
      this._toast(true, 'Disconnected from Spotify.');
    },

    // ── Recommendation engine ───────────────────────────────────────────
    // The server decides which engines are selectable (those with credentials in
    // .env) and which is active for this session; we just render and switch.
    async loadRecommender() {
      try {
        const data = await api.recommender();
        this.recommender.active = data.active;
        this.recommender.available = data.available ?? [];
      } catch { /* non-fatal: selector/badge just stay hidden */ }
    },

    activeEngine() {
      return this.recommender.available.find((e) => e.id === this.recommender.active) || null;
    },
    engineLabel(e) {
      return e ? (e.model ? `${e.label} · ${e.model}` : e.label) : '';
    },

    async selectRecommender(id) {
      if (id === this.recommender.active || this.recommender.switching) return;
      const prev = this.recommender.active;
      this.recommender.active = id;          // optimistic
      this.recommender.switching = true;
      try {
        const data = await api.setRecommender(id);
        this.recommender.active = data.active;
        this.recommender.available = data.available ?? this.recommender.available;
        this._toast(true, `Recommendations now use ${this.engineLabel(this.activeEngine())}.`);
      } catch (e) {
        this.recommender.active = prev;      // roll back on failure
        this._handleError(e, 'Could not change the recommendation engine.');
      } finally {
        this.recommender.switching = false;
      }
    },

    // ── Vibe mode LLM ───────────────────────────────────────────────────
    // LLM-only and independent of the recommendation engine above. The picker only
    // renders when >1 LLM is available; the whole vibe panel hides when 0 are.
    async loadVibe() {
      try {
        const data = await api.vibeStatus();
        this.vibe.active = data.active;
        this.vibe.available = data.available ?? [];
      } catch { /* non-fatal: vibe panel just stays hidden */ }
    },

    // Picked locally and remembered server-side on the next generate (createVibe sends
    // it); no round-trip needed just to highlight a choice.
    selectVibeEngine(id) {
      if (this.vibe.available.some((e) => e.id === id)) this.vibe.active = id;
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
