# website/ — OduSphere Astro site root

This is the root of the OduSphere headless frontend. By OduSphere's architecture the
public site and client portals are built with **Astro**, while Odoo acts only as the
backend (data is fetched through REST/JSON controllers in the `odu_*` modules). The
standard Odoo `website` module is not used.

## Current state

This is a **skeleton**: directories and placeholder files are in place, but
dependencies are **not installed yet** (`node_modules/` is absent and Astro has not
actually been initialized). `package.json` and `astro.config.mjs` are stubs that mark
this folder as the build root.

## Initialize and build

```bash
cd website
npm install          # installs astro (and, if desired, Tailwind as a separate step)
npm run build        # builds the site into website/dist
npm run dev          # local Astro dev server
```

The build output goes into **`website/dist`**. That is the folder Caddy serves as
static content (see the root `docker-compose.yml` and `Caddyfile`). For now `dist/`
holds a temporary `index.html` that the first `astro build` will overwrite.

## Structure

```
website/
├── astro.config.mjs   # build config (outDir → ./dist)
├── package.json       # dependencies and scripts (stub)
├── public/            # static assets (copied to dist as-is)
├── src/
│   ├── components/    # reusable .astro components
│   ├── layouts/       # page layouts
│   └── pages/         # site routes (index.astro, etc.)
└── dist/              # build output (served by Caddy)
```

## Adding Tailwind (next step)

```bash
cd website
npx astro add tailwind
```
