// ─────────────────────────────────────────────────────────────────────────────
// SPHERE BRANDING — edit this file to make the starter site yours.
//
// This is the ONE place to change the public face: the header, the hero, the
// footer and the page <title> all read from here. Replace the placeholder values
// below with your sphere's name and copy.
// ─────────────────────────────────────────────────────────────────────────────

export interface SiteConfig {
  /** Brand / sphere name — shown in the header, hero, footer and <title>. */
  name: string;
  /** One-line tagline under the hero heading. */
  tagline: string;
  /** Short paragraph describing the business / the "living ERP". */
  blurb: string;
  /** Primary call-to-action. Defaults point at the Odoo workspace login. */
  cta: { label: string; href: string };
  /** Small note shown in the footer. */
  footerNote: string;
}

export const site: SiteConfig = {
  name: "OduSphere",
  tagline: "The Living ERP — grown around your business, not the other way around.",
  blurb:
    "This is a sphere: an isolated digital world powered by OduSphere. " +
    "Zero bloat, no legacy boxes — just the exact workflows your operation needs, " +
    "built from scratch and evolving on demand.",
  cta: { label: "Open the workspace", href: "/odoo" },
  footerNote: "Powered by OduSphere.",
};
