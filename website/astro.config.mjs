// @ts-check
import { defineConfig } from 'astro/config';

// Build root of the OduSphere headless site.
// The output is built into ./dist and served by Caddy as static content
// (see the root Caddyfile).
export default defineConfig({
  outDir: './dist',
  // Dynamic data is fetched from Odoo through Caddy under the /api, /web, etc.
  // prefixes (see the proxy rules in the Caddyfile).
});
