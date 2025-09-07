# Product Requirements Document (PRD)
Cedar Heights Music — Public Marketing Website (v1)

Version: 0.1 (Outline)
Status: Draft Outline for Review
Date: 2025-08-11

1. Product Overview
- Purpose: Build a multi-page, public-only marketing website that strictly adheres to the provided Figma design and funnels parents to start enrollment in the protected app.
- Business Objective: Increase studio enrollment by 20% in 6 months via higher-conversion public site that hands off context to the protected enrollment flow.
- Scope (Public Site v1): 
  - Routes: /, /about, /pricing, /enroll, /contact, /privacy, /terms
  - Enrollment handoff: redirect from /enroll completion to protected app with query params
  - Week 1 data via mocks, switch to live public endpoints pre-launch
  - No authentication; no server-side PII collection

2. Information Architecture and Pages
- Global Navigation (per Figma):
  - Top Nav: Home (/), About (/about), Pricing (/pricing), Enroll (/enroll), Contact (/contact)
  - Footer: Privacy (/privacy), Terms (/terms), contact links
- Page List:
  - Home (/)
    - Hero with single primary CTA to /enroll
    - Brief value propositions (copy per Figma)
  - About (/about)
    - Studio story and values
    - Teacher bios with photos (static content v1)
  - Pricing (/pricing)
    - Single monthly price display ($125 placeholder; pulled from backend pre-launch)
    - Clear note: “Commitment: current semester”; pricing labeled “indicative” until live data
    - CTA to /enroll
  - Enroll (/enroll)
    - 2-step configurator:
      1) Instrument (mapped to instrument_id)
      2) Preferred timeslot (from mock → live /public/timeslots)
    - On completion: immediate redirect to protected app (see interface requirements)
    <!-- Updated 2025-08-28: Pricing simplification confirmed; removed billing frequency selector.
    WBS Evidence: Prior plan included frequency selector and 3rd step billing [Pricing Page](ai_docs/context/core_docs/wbs.md:128), [Enroll Modal](ai_docs/context/core_docs/wbs.md:139).
    Business Rationale: Simplify decision-making; align with semester commitment policy.
    Stakeholder Impact: Update marketing copy, UI components, and handoff parameters. -->
  - Contact (/contact)
    - Client-side contact form using Formspree (or similar), includes consent text and basic spam protection
  - Privacy (/privacy), Terms (/terms)
    - Static content pages linked in footer

3. User Personas (Public Site)
- Primary Persona: Parent/Guardian in Cedar/Nanaimo BC
  - Goals: Understand offerings, see teacher quality, estimate cost/options, start enrollment quickly
  - Constraints: Mobile-first, low tolerance for friction, clear CTA guidance
- Secondary Persona: Returning visitor checking price/options
  - Goals: Quickly reach /enroll with minimal clicks
- Non-Goals: Admin operations, authenticated parent dashboard actions (out of scope for public site)

4. Key User Journeys (Public Site)
- Journey A: Discover → Enroll
  1) Land on Home → primary CTA → /enroll
  2) Select instrument → select preferred timeslot
  3) Redirect immediately to protected app with context params
- Journey B: Research → Pricing → Enroll
  <!-- Updated 2025-08-28 -->
  1) Navigate to /pricing → view single monthly price and semester commitment
  2) CTA → /enroll
  3) Complete 2-step configurator → redirect with params
- Journey C: About → Enroll
  1) View teacher bios/studio story at /about
  2) CTA to /enroll → complete steps → redirect

5. Functional Requirements
5.1 Global
- F-GL-1: Navigation renders per Figma with routes: /, /about, /pricing, /enroll, /contact; footer includes /privacy and /terms
- F-GL-2: Mobile-first responsive layout; images optimized and lazy-loaded as per Figma and performance targets

5.2 Home (/)
- F-HO-1: Display hero section with single primary CTA linking to /enroll
- F-HO-2: Display brief value propositions (copy per Figma); optional “learn more” links to /about and /pricing

5.3 About (/about)
- F-AB-1: Render studio story and values
- F-AB-2: Render teacher bios with photos (static v1 content); maintain layout consistency with Figma cards/typography

5.4 Pricing (/pricing)
<!-- Updated 2025-08-28: Simplified pricing model
WBS Evidence: Prior plan included frequency selector [Pricing Page](ai_docs/context/core_docs/wbs.md:128).
Business Rationale: One price per month with semester commitment reduces decision friction.
Stakeholder Impact: Update Pricing UI to static price; remove selector; QA and copy changes. -->
- F-PR-1: Display a single monthly price (placeholder $125) sourced from backend pre-launch; instrument does not affect price
- F-PR-2: Show note “Commitment: current semester”; pricing labeled “indicative” until live backend value
- F-PR-3: Provide CTA to /enroll

5.5 Enroll (/enroll)
<!-- Updated 2025-08-28: Two-step flow; removed billing frequency -->
- F-EN-1: Step 1 — Instrument selection (maps to backend instrument_id)
- F-EN-2: Step 2 — Preferred timeslot selection (mock data in Week 1; switch to GET /public/timeslots pre-launch)
- F-EN-3: On completion, immediately redirect to protected app handoff URL with required query params
- F-EN-4: Enrollment summary displays “$125/month” and “Commitment: current semester”

5.6 Contact (/contact)
- F-CT-1: Client-side form using Formspree (or similar) to submit inquiries
- F-CT-2: Include consent text (privacy notice) and basic spam protection (honeypot)
- F-CT-3: Do not store PII server-side on public site

5.7 Privacy (/privacy), Terms (/terms)
- F-PL-1: Render static content pages accessible via footer and direct URLs

6. Interface Requirements and Handoff
- Handoff Target (confirmed):
  - https://app.cedarheightsmusic.com/enroll/start
- Query Parameters:
  - instrument_id: UUID for instrument chosen on /enroll
  - teacher_id: Optional; implied by selected timeslot (if available)
  - timeslot_id: UUID for chosen preferred weekly 30-min slot
  - source: public_site (fixed for attribution)
  <!-- Updated 2025-08-28: Removed billing_frequency per pricing simplification.
  WBS Evidence: Frequency selector and Step 3 billing removed [Pricing Page](ai_docs/context/core_docs/wbs.md:128), [Enroll Modal](ai_docs/context/core_docs/wbs.md:139).
  Business Rationale: Single monthly price with semester commitment; no user-selected frequency.
  Stakeholder Impact: Update handoff builder and tests to reflect parameter removal.
  Pending: Confirm if semester_id should be included in handoff or determined server-side. -->
- Behavior:
  - I-EN-1: On /enroll completion, redirect immediately (no modal) with the above parameters
  - I-EN-2: If some selections are missing, still redirect with available params; protected flow will prompt for missing details

7. Data Requirements
- Entities (public site usage only):
  - Instrument (id, name): static list per backend; used for selection
  - Teacher (id, name, photo, bio): static content v1; live via GET /public/teachers pre-launch (subset for public site)
  - Timeslot (id, teacher_id, weekday, start_time, end_time, active_flag): selection list on /enroll (live via GET /public/timeslots pre-launch)
- Data Sources:
  - Week 1: Local mock JSON for instruments/teachers/timeslots to unblock UI development
  - Pre-launch: Replace with live public endpoints:
    - GET /public/teachers
    - GET /public/timeslots?teacher_id=&weekday=&active=true
- Data Adapter:
  - D-AD-1: Implement a simple data-service layer that can switch between mock and live sources via a configuration flag

8. Non-Functional Requirements (Public Site)
- Performance:
  - NFR-P-1: Core Web Vitals targets on 75th percentile mobile: LCP <= 2.5s, CLS <= 0.1
  - NFR-P-2: Optimize images; lazy-load non-critical imagery
- Usability:
  - NFR-U-1: Strict adherence to Figma design tokens (colors, typography, spacing) and components
  - NFR-U-2: Mobile-first responsive behavior matches Figma breakpoints
- Reliability:
  - NFR-R-1: All public routes load without backend dependency failures during Week 1 (mock fallback)
- Security/Privacy:
  - NFR-S-1: No server-side PII collection; /contact form uses a third-party client-side submission (e.g., Formspree)
  - NFR-S-2: Do not include personal data in handoff URL; only UUID identifiers
  <!-- Updated 2025-08-28: Removed "frequency" due to pricing simplification and handoff param removal.
  WBS Evidence: Frequency selection removed [Enroll Modal](ai_docs/context/core_docs/wbs.md:139). -->
- SEO:
  - NFR-SEO-1: Basic metadata per page; later enhancement post-launch if needed (sitemap, etc.)
- Analytics:
  - NFR-A-1: Deferred to post-launch; add Enroll CTA event later (non-PII)

9. Constraints and Assumptions
- Constraints:
  - C-1: Timeline 2 weeks for v1; strict Figma adherence prioritized over extra features
  - C-2: Public-only site; authentication and booking occur in protected app
  - C-3: CORS and backend domain coordination required pre-launch for live public endpoints
- Assumptions:
  <!-- Updated 2025-08-28: Pricing simplification and semester commitment -->
  - A-1: Single monthly price model set via backend (use $125 placeholder on public site until live integration). Instrument choice does not affect price. Users commit to the current semester per school calendar stored in backend.
  - A-2: Preferred timeslot is non-binding on public site; actual booking/locking occurs in protected app
  - A-3: Figma defines canonical component styles and page layouts

10. Acceptance Criteria (Page-Level)
- Home (/)
  - AC-HO-1: Hero visible above the fold with a single primary CTA linking to /enroll
  - AC-HO-2: Layout matches Figma for desktop and mobile breakpoints
- About (/about)
  - AC-AB-1: Displays studio story and values content
  - AC-AB-2: Renders teacher bios with photos per Figma component styles
- Pricing (/pricing)
  <!-- Updated 2025-08-28 -->
  - AC-PR-1: Page displays single monthly price ($125 placeholder) labeled “indicative” and shows “Commitment: current semester”
  - AC-PR-2: CTA to /enroll present and functional
- Enroll (/enroll)
  <!-- Updated 2025-08-28 -->
  - AC-EN-1: 2 steps function in order: instrument → preferred timeslot
  - AC-EN-2: On completion, browser redirects to https://app.cedarheightsmusic.com/enroll/start with params instrument_id, teacher_id (if implied), timeslot_id, source=public_site
  - AC-EN-3: Enrollment summary displays “$125/month” and “Commitment: current semester”
  - AC-EN-4: Week 1 operates with mock data; pre-launch switch uses GET /public/teachers and /public/timeslots
- Contact (/contact)
  - AC-CT-1: Client-side Formspree (or similar) form submits successfully
  - AC-CT-2: Consent text and spam prevention (honeypot) are present
- Privacy (/privacy), Terms (/terms)
  - AC-PL-1: Static pages accessible from footer and direct routes
- Global
  - AC-GL-1: Performance targets met (LCP, CLS) on 75th percentile mobile
  - AC-GL-2: Figma design adherence verified across routes

11. Prioritization (MoSCoW)
- Must Have:
  - Pages: /, /about, /pricing, /enroll, /contact, /privacy, /terms
  - /enroll 2-step configurator and handoff redirect with params (no billing frequency)
  - Pricing shows single monthly price with “Commitment: current semester” and “indicative” label
  <!-- Updated 2025-08-28: Simplified pricing and enrollment flow.
  WBS Evidence: Prior WBS sections defined frequency selector and Step 3 billing [Pricing Page](ai_docs/context/core_docs/wbs.md:128) and [Enroll Modal](ai_docs/context/core_docs/wbs.md:139).
  Business Rationale: Reduce friction and align to semester commitment policy.
  Stakeholder Impact: Marketing copy, UI components, and QA scenarios updated. -->
  - Contact form via Formspree (client-side)
  - Mock → live data switch for teachers/timeslots
- Should Have:
  - Value props on Home
  - Image optimization and lazy-loading
- Could Have:
  - Minor motion/animation per Figma (if time allows)
  - Additional SEO meta polish pre-launch
- Won’t Have (v1):
  - Analytics events (post-launch)
  - Server-side form handling
  - Authenticated features

12. Risks and Mitigations
- R-1: Live public endpoints readiness/CORS delays
  - Mitigation: Mock-first build; swappable adapter; coordinate allowed origins early
- R-2: Content (teacher bios/photos) delivery timing
  - Mitigation: Use placeholders; swap content late in Week 2
- R-3: Price display mismatch
  - Mitigation: Label as “indicative”; confirm final pricing in protected flow
- R-4: Performance regressions due to heavy assets
  - Mitigation: Optimize/lazy-load images; audit bundle

13. Dependencies
- Figma design file (canonical source for components and layout)
- Backend public endpoints for teachers/timeslots (pre-launch)
- Protected app URL for handoff

14. Open Questions
- OQ-1: Confirm canonical list of instruments and IDs for public site mapping (source of truth during mock phase)
- OQ-2: Final copy for value props, teacher bios, privacy, and terms (owner and delivery dates)
<!-- Updated 2025-08-28: Pricing simplification -->
- OQ-3: Confirm public endpoint for current monthly price and semester details (effective dates, label). Should semester_id be included in handoff URL or determined server-side?

15. Appendix
- Handoff URL (final): https://app.cedarheightsmusic.com/enroll/start?instrument_id=&teacher_id=&timeslot_id=&source=public_site
<!-- Updated 2025-08-28: Removed billing_frequency. Pending confirmation: whether to include semester_id or rely on server-side "current semester".
WBS Evidence: URL builder originally included billing_frequency [WBS Enrollment Handoff Utility](ai_docs/context/core_docs/wbs.md:170).
Business Rationale: Pricing simplified to single monthly price with semester commitment; frequency selection removed; parameter no longer needed.
Stakeholder Impact: Update URL builder utility, tests, and any tracking relying on billing_frequency. -->

- Public endpoints (pre-launch):
  - GET /public/teachers
  - GET /public/timeslots?teacher_id=&weekday=&active=true
- Data Adapter Strategy:
  - Configuration flag to switch data source:
    - mock: local JSON
    - live: fetch from public endpoints