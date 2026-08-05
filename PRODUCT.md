# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Russian-speaking owners of загородные участки (country/suburban plots) who solve water problems on their own land themselves, with their own hands and budget, rather than hiring a contractor and accepting the result.

They arrive from search mid-problem, not browsing: the plot is standing in water, the foundation and цоколь are getting wet, the well has just been drilled and they don't know what comes next, or they are standing in front of a materials choice (which щебень fraction, which pipe, geotextile or not). Often reading on a phone at the site or comparing options before a purchase.

## Product Purpose

НАШДОМ (ursdom.ru) is a single-author practical reference on water at a country plot: дренаж (drainage), скважина (water well), and ливнёвка (storm drainage).

It exists because the available sources contradict each other — forums, СНиПы, and sellers' advice each say something different, and roughly half of it is wrong. The site collects what actually worked, verified in practice or checked against norms.

Success is organic search reach plus reading depth: readers who find the page and finish it. Affiliate income covers hosting and time; it is not the measure of the project and does not outrank the reading experience.

## Positioning

A first-person account from someone who completed the full cycle personally — wet plot, DIY drainage, drilling, fit-out with a скважинный адаптер, filters — rather than a compilation of other people's articles.

What a neighboring site could not truthfully copy: every schematic is drawn by the author from real sections and joints (no stock imagery, stated as a principle), and every article carries concrete numbers — depths, slopes, diameters, densities — with comparison tables. Prices are deliberately absent because they go stale within a month.

## Operating Context

- Reader is pre-project or mid-project, deciding or buying. Frequently on a phone, outdoors, at the plot.
- Every article opens with a TL;DR block so the answer is visible in about ten seconds, and closes with the questions people most often ask in search.
- Articles are cross-linked along construction logic, not alphabetically: the laying instruction leads to the pipe article, the pipe article leads to the gravel article.
- Product recommendations appear as «Что купить» blocks linking to Яндекс Маркет. The affiliate relationship is disclosed in the footer of every page and explained on /o-proekte/.

## Capabilities and Constraints

- Hand-written static HTML, one directory per page with an `index.html`. No framework, no build step, no runtime dependencies, no package manifest.
- A single stylesheet, `assets/css/main.css`, with no external CSS or font requests. Typography relies on system fonts (Georgia stack for body, system-ui sans for headings).
- Served by GitHub Pages from the repository root: `.nojekyll` present, `CNAME` → `ursdom.ru`.
- `_templates/page.html` and `_templates/anchors.md` are the authoring templates new pages are copied from; changes to page structure belong there too.
- `sitemap.xml` and the per-page JSON-LD graphs (WebSite/Organization, AboutPage, BreadcrumbList, Article/FAQ) are maintained by hand and must be updated whenever pages are added or changed.
- Yandex Metrika (counter 110405092, with webvisor and clickmap) is inlined at the bottom of every page. Yandex and Google site-verification files sit at the repository root and must not be moved or renamed.
- Language is Russian throughout: `lang="ru"`, `og:locale` `ru_RU`. No localization is planned.
- Content grows within the three existing top-level sections (drenazh, skvazhina, livnevka). No new top-level sections are planned; navigation does not need to absorb new categories.
- **Undecided:** a feedback form on /kontakty/ is stated as planned, with no timing committed. There is no support channel and none is intended — the page says so deliberately.

## Brand Commitments

- Name: **НАШДОМ**, set as a wordmark with a colored dot after it. Domain ursdom.ru.
- Voice: first person, plain, practical. No marketing register, no hedging, no filler.
- **The author stays anonymous.** No name, no photo, no byline, no credentials, no bio. This is a deliberate choice, not a missing asset. Future work must not invent an author identity or add a personal-authority block.
- Schematics are drawn by the author only. Stock photography is explicitly rejected.
- No prices in articles.
- Affiliate links are disclosed openly and the disclosure stays visible; recommendations are made on the same criteria the author would use for himself.

## Evidence on Hand

Real and available:

- 21 published pages: home, three section hubs, fourteen articles, plus /o-proekte/, /kontakty/, /politika/, and a 404.
- 9 hand-drawn inline SVG schematics inside `figure.scheme` elements across the articles.
- `img/og-cover.png` (1200×630) used as the Open Graph image site-wide.
- `favicon.svg`.
- «Что купить» affiliate blocks pointing at Яндекс Маркет.
- Live analytics via Yandex Metrika.

Explicitly absent — future work must not fabricate any of it:

- No testimonials, reviews, customer names, case studies, or press mentions.
- No traffic numbers, benchmarks, ratings, or awards.
- No author photo, name, or biography (deliberate — see Brand Commitments).
- No pricing data, no product inventory of its own, no commercial services offered.
- No social media presence, newsletter, or community.

## Product Principles

1. **Answer one question to the end.** A page resolves a single reader problem completely — numbers, table, schematic — instead of surveying the topic and pointing elsewhere.
2. **Credibility is the asset; revenue rents space inside it.** Affiliate blocks live within the reference and never override, interrupt, or color its judgments.
3. **Ten seconds to the answer, then the depth.** A reader arriving from search gets the verdict up front; the reasoning follows for those who want it.
4. **Only what was verified.** Practice or norms — nothing repeated from sellers or forums without checking, and nothing stated more confidently than it was verified.
5. **Deepen, don't broaden.** New material makes drainage, wells, and storm drainage more complete rather than adding adjacent topics.

## Accessibility & Inclusion

No formal standard has been committed to. The existing implementation already treats accessibility as deliberate, and that behavior is the floor future work must not fall below:

- Skip link to `#content` on every page.
- Visible `:focus-visible` outline in the CTA color with offset.
- `prefers-reduced-motion` honored globally.
- ARIA-labelled site navigation and breadcrumbs, semantic heading order, native `<details>` for FAQ.
- Tables wrapped in horizontally scrollable containers so they survive narrow screens.
- Single-column measure capped at 46rem, sized for phone reading first.
