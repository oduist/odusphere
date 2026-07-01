# Website — the sphere's public face

The headless **Astro** public site for this sphere. Odoo never renders public
pages (the standard `website` module is banned, ODUSPHERE.md §5); this site is
built to static files and served by the sphere's gateway, while dynamic traffic
(`/odoo`, `/web/*`, `/api/*`, `/websocket`) is proxied to Odoo.

This is a **starter seed**: the `odusphere` CLI pulls it once when a sphere is
initialised and then leaves it alone — make it yours.

## Customize in one place

Edit [`src/site.config.ts`](src/site.config.ts) — the sphere name, tagline,
blurb, and the call-to-action all read from there. For deeper theming, tweak the
brand color tokens in [`src/styles/global.css`](src/styles/global.css) (the
`@theme` block).

## Contact form

The landing page ships a contact form that posts to **`POST /api/contact`**, a
public endpoint provided by the `odu_base` module. Submissions are stored as
`odu.contact.message` records and reviewed by administrators in the
**Settings → Contact Requests** inbox. For the form to reach Odoo, the sphere
gateway must proxy `/api/*` to the Odoo backend (the §5 convention).

## Develop & build

```bash
npm install      # install dependencies
npm run dev      # local dev server with hot reload (http://localhost:4321)
npm run build    # compile to ./dist (what the gateway serves)
npm run preview  # serve the built ./dist locally to sanity-check
```

Stack: **Astro 5** + **Tailwind CSS v4** (via the `@tailwindcss/vite` plugin),
static output. `dist/` is a build artifact and is **not** committed — the CLI (or
your own pipeline) runs `npm run build`.

> Not an `odu_` module: the documentation rules in ODUSPHERE.md §6
> (`tech_spec.md`, `user_guide.md`, change timeline) do not apply to this folder.
