// @ts-check
import { defineConfig } from "astro/config";
import tailwindcss from "@tailwindcss/vite";

// Static output (Astro default). The build emits website/dist, which the sphere
// gateway serves as static files. Tailwind CSS v4 is wired via its Vite plugin
// (the @astrojs/tailwind integration is deprecated in Astro 5).
export default defineConfig({
  vite: {
    plugins: [tailwindcss()],
  },
});
