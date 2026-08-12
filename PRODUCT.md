# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Homeowners and suburban plot owners in Russia handling water-management problems on
their own property, DIY, without hiring a contractor for the whole job:
- Land is waterlogged → needs a drainage system
- Foundation/basement is getting wet → needs drainage + waterproofing at the house
- A well has just been drilled → needs to go from raw borehole to running water
  (adapter or kesson, pump, hydro-accumulator, filtration)
- Roof/yard runoff needs collecting and routing → needs a stormwater (ливнёвка) system

They arrive via search with a specific question and want a direct, complete answer:
concrete numbers (depths, slopes, pipe diameters, gravel fractions), comparison
tables, and diagrams of real cross-sections — not general theory.

## Product Purpose

НАШДОМ (ursdom.ru) is a practical, author-voiced reference for these three water
problems. It exists because the author solved them on their own property and found
the available information (forums, СНиП documents, seller advice) contradictory and
scattered, so the site collects what actually worked. Success is a reader who lands
on one article, gets a complete, numeric, actionable answer to their specific
question, and can follow curated internal links into the next problem down the line.

## Positioning

Personally verified, first-hand practice, not aggregated or rewritten content: every
article comes from a project the author actually completed on their own property
(drainage, well, adapter, filtration), cross-checked against building codes (СНиП).
Diagrams are hand-drawn from real cross-sections and installation details — never
stock imagery. Article text carries no prices, since those go stale; current pricing
lives on the linked Yandex Market listings instead. This is the claim a rewritten
SEO/content-mill article, a seller's page, or a generic forum thread could not
truthfully make.

## Operating Context

- Content workflow: each article is a standalone, complete answer to one question,
  built from `_templates/page.html` (TL;DR summary, one hand-drawn inline SVG scheme,
  a "what to buy" affiliate block, an FAQ section fed into FAQPage schema, and a
  related-articles block).
- Internal linking is curated by hand via `_templates/anchors.md`, a registry of every
  anchor-text/target pair used site-wide; each anchor string is used exactly once
  anywhere on the site. Adding an article means adding its outbound anchors to that
  registry with unique phrasing, not auto-generating links.
- Revenue comes entirely from Yandex Market affiliate links in "Что купить" blocks —
  no subscriptions, no display ads, no contractor lead-gen.
- Reader's device mix is unknown/unmeasured beyond what Yandex.Metrika records; no
  stated mobile-vs-desktop skew to design around.

## Capabilities and Constraints

- Static HTML only: one shared stylesheet (`/assets/css/main.css`), no JS framework,
  no build step or bundler. Yandex.Metrika is the only third-party script running.
- `_templates/page.html` is the canonical article template; its `{{PLACEHOLDER}}`
  tokens (Russian names) mark fields a human still has to fill in per article.
- Deployed as a static site via GitHub Pages (`CNAME` → ursdom.ru, `.nojekyll`).
- Existing design tokens (CSS custom properties in `main.css`): `--bg`, `--ink`,
  `--deep`, `--deep-2`, `--earth`, `--cta`, `--cta-dark`, `--line`, `--card`, and
  `--sans` / `--serif` font stacks. Reuse these; don't introduce parallel colors.
- Single centered column layout, `max-width: 46rem`; serif body copy, sans-serif UI
  chrome (nav, headers, tables, cards) — an editorial/reference-document feel.

## Brand Commitments

- Name: НАШДОМ (ursdom.ru). Wordmark is text-based (`НАШДОМ` + accent-colored dot),
  no illustrated logo.
- Voice: first person, singular author ("I"), stating only what the author has
  personally practiced or verified against code. Every article resolves one question
  completely rather than surveying a topic.
- No stock photography anywhere; all diagrams are hand-drawn SVG from real details.
- No prices in article body copy.
- Affiliate relationship is disclosed openly (footer on every page, and in full on
  `/o-proekte/`); commission is stated to not influence which products are recommended.

## Evidence on Hand

- 20 published articles across three clusters (`/drenazh/`, `/skvazhina/`,
  `/livnevka/`) plus `/o-proekte/`, `/kontakty/`, `/politika/`.
- `/o-proekte/` states the project's own principles and monetization model in the
  author's words — treated as the source of truth for voice/positioning above.
- `_templates/anchors.md` is a real, populated registry of internal-linking anchors —
  usable as evidence of the site's existing internal-linking depth and pattern.
- No testimonials, case studies, press mentions, or third-party endorsements exist;
  do not fabricate any for future work.
- No customer/traffic data beyond what Yandex.Metrika collects; nothing quantitative
  about audience size or conversion is on hand to design against.

## Product Principles

1. Answer one question completely per page — numbers, tables, and a real diagram,
   not a survey of the topic.
2. Only state what has been personally practiced or checked against code; never pad
   with generic advice to fill space.
3. No stock imagery, ever — schemes are hand-drawn from real installation details.
4. Keep prices out of article text; point to Market for current pricing instead.
5. Grow internal linking deliberately (curated, unique anchors) rather than
   mechanically, to keep the site feeling authored rather than templated.

## Accessibility & Inclusion

No formal accessibility standard has been set as a requirement. Existing baseline in
the codebase (skip-link, visible focus outlines, semantic heading structure,
`prefers-reduced-motion` handling) should be maintained as the working floor; nothing
stricter is currently binding.
