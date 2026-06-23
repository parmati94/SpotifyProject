import { defineConfig } from 'vite';
import handlebars from 'vite-plugin-handlebars';
import { resolve } from 'path';

// Build-only config. The frontend is compiled to a static dist/ that nginx serves
// (and reverse-proxies /api, /login, /callback to uvicorn). Partials live in partials/
// and are pulled in with {{> name }}. There is no Vite dev server — this app runs via
// Docker; for a dev loop see docker-compose.dev.yml.
export default defineConfig({
  root: './',
  publicDir: 'public',
  plugins: [
    handlebars({
      partialDirectory: resolve(__dirname, 'partials'),
    }),
  ],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    minify: 'esbuild',
    sourcemap: false,
  },
});
