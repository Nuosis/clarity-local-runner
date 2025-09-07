# Cedar Heights Music — Public Website Project Charter

Executive Summary
- Build a multi-page public marketing website that strictly adheres to the provided Figma design while migrating from a single long page to a clear, enrollment-focused IA.
- Primary business outcome: increase studio enrollment by 20% in 6 months by driving users to start enrollment from the public site and hand off to the protected app with prefilled query parameters.
- v1 timeline: 2 weeks, minimal budget, with a phased integration plan (mock data in Week 1, switch to live backend public endpoints pre-launch).

Project Vision and Purpose
- Purpose: Provide a high-conversion, trustworthy public presence that guides parents of K–12 students in Cedar/Nanaimo BC to start enrollment quickly.
- Vision: A simple, fast, and visually consistent site that showcases teachers and options, surfaces availability, and funnels to an “Enroll Now” action that hands off seamlessly to the protected system.

Business Objectives and Success Metrics
- Primary Objective: Increase studio enrollment by 20% in 6 months.
- Conversion Goal: 15 completed enrollments per month attributed to public site traffic.
- Supporting Objectives:
  - Strict Figma design adherence for brand trust.
  - Clear IA with enrollment-focused CTAs.
  - Fast pages and mobile-first UX to minimize drop-off.
- Success KPIs:
  - Enrollments: ≥15/month completed via protected app flow initiated from public site.
  - Click-through to enroll: uplift month-over-month.
  - Page performance benchmarks (Core Web Vitals): LCP < 2.5s on 75th percentile mobile; CLS < 0.1.

Scope and Out-of-Scope
- In Scope (Public Site v1):
  - Multi-page IA: Home, Teachers, Pricing/Options, Enroll Now, Contact.
  - “Enroll Now” CTA with query-param handoff to protected system.
  - Pricing/Options page with a simple configurator (instrument → 30-min duration [fixed] → preferred available timeslot → billing frequency).
  - Footer links for Privacy Policy and Terms.
  - Mock data for configurator (Week 1), switch to live public endpoints before launch.
- Out of Scope (Public Site v1):
  - Auth-protected features (admin/parent dashboards, payments).
  - Direct booking or payment on the public site.
  - Analytics implementation (deferred to post-launch).
  - Complex CMS; manual/static content acceptable for v1.

Stakeholders
- Owner/Teacher (primary business stakeholder).
- Parents of K–12 students in Cedar/Nanaimo BC (primary audience).
- Future admins/parents (served by protected system; not in v1 public site scope).

Target Audience and Positioning
- Primary Audience: Parents of K–12 students in Cedar/Nanaimo BC.
- Key Differentiators to Communicate:
  - Teacher skill/persona and match quality.
  - Availability and location relevance.
  - Convenient weekly 30-minute lessons.

Information Architecture (Figma-Aligned)
- Top-level navigation:
  - Home: Hero, value proposition, featured teachers/programs, primary “Enroll Now” CTA.
  - Teachers: Profiles with skill/persona, high-level availability signals; CTAs map to enrollment flow.
  - Pricing/Options: Simple configurator (instrument → fixed 30-min → preferred timeslot → billing frequency).
  - Enroll Now: Generic start with selections (if any) carried into URL.
  - Contact: Simple form and contact details.
- Footer: Privacy Policy, Terms, contact links.

Backend Alignment and Integration Contract
- Backend guide alignment (API-first MVP):
  - Public (no auth):
    - GET /public/teachers
    - GET /public/timeslots?teacher_id=&weekday=&active=true
  - Parent/protected operations (JWT required) — out of scope for public site.
- Handoff URL (confirmed):
  - https://app.cedarheightsmusic.com/enroll/start?instrument_id=&teacher_id=&timeslot_id=&billing_frequency=&source=public_site
- Query Parameters:
  - instrument_id: instrument selected in configurator.
  - teacher_id: preferred teacher if selected.
  - timeslot_id: preferred fixed weekly 30-min slot if selected.
  - billing_frequency: monthly | yearly | semester.
  - source: public_site (fixed for attribution).
- Fallbacks and Behaviors:
  - If any param is missing at CTA time, still hand off; protected flow will prompt for missing selections.
  - Preferred timeslot selection on public site is non-binding and for convenience; actual locking/booking occurs in protected system.

Pricing/Options UX Decision
- Simple configurator on public site:
  - Instrument selection (mapped to backend instrument_id).
  - Lesson length fixed at 30 minutes.
  - Preferred available timeslot selection (sourced from /public/timeslots once live).
  - Billing frequency: monthly | yearly | semester.
  - Computed indicative price (business rules per backend; for v1 mocked pricing allowed).
  - “Enroll Now” button builds the confirmed handoff URL with the selected query params.

Technical Constraints and Delivery Plan
- Timeline: 2 weeks for v1 public site.
- Budget: Minimal; prioritize Figma adherence and enrollment flow over animations/extra content.
- Data Integration Phasing:
  - Week 1: Use mock JSON for teachers/instruments/timeslots to unblock UI build and Figma polish.
  - Before Launch: Switch to live endpoints:
    - GET /public/teachers
    - GET /public/timeslots
- Performance/Hosting:
  - Lightweight static delivery (Vite already present).
  - Optimize images (web-friendly formats) and lazy-load heavier assets.
- Analytics:
  - Deferred to post-launch (Google Analytics/Meta Pixel event on “Enroll Now” with non-PII metadata).
- Compliance/Policies:
  - Display Privacy Policy and Terms links in footer.
  - Do not collect PII on public site in v1 beyond query param handoff.

Dependencies and Content Plan
- Content/Assets:
  - Partial content availability in Week 1; placeholders allowed.
  - Teacher bios/photos to arrive in Week 1; replace placeholders before launch.
- Brand:
  - Adhere strictly to Figma for typography, colors, spacing, and components.
  - Use supplied imagery; where missing, use neutral placeholders to preserve layout.

Risks and Mitigations
- Risk: 2-week deadline is tight with content arriving during Week 1.
  - Mitigation: Use placeholders; content swap late in Week 2; mock data allows parallelization.
- Risk: Live endpoint readiness and CORS configuration delays.
  - Mitigation: Phase with mocks; coordinate allowed origins for the deployed domain; simple adapter to switch data source.
- Risk: Price display mismatches backend rules.
  - Mitigation: Label pricing on public site as indicative; final pricing confirmed in protected flow.
- Risk: SEO and performance regressions due to heavy assets.
  - Mitigation: Optimize images, minimize render-blocking resources; QA Core Web Vitals targets.
- Risk: Loss of tracking visibility for v1 (analytics deferred).
  - Mitigation: Short post-launch iteration to add analytics; in the interim, use server logs/referrer analysis on protected app.

Regulatory and Compliance Considerations
- Privacy:
  - No PII stored on public site v1; links to Privacy Policy and Terms in footer.
  - Query params contain non-PII identifiers (UUIDs) and frequency; avoid personal data in URLs.
- Security:
  - Only public endpoints consumed.
  - Protected flows gated by backend JWT; public site does not manage auth.

Milestones and Timeline
- Week 1:
  - Implement multi-page scaffolding aligned to Figma (Home, Teachers, Pricing/Options, Enroll Now, Contact).
  - Build configurator with mock data and indicative pricing.
  - Wire “Enroll Now” CTA to confirmed handoff URL with mock selections.
  - Insert Privacy Policy and Terms links in footer.
- Week 2:
  - Replace mock data with live endpoints for teachers/timeslots.
  - Content swap for teacher bios/photos; polish styles and responsiveness.
  - Final QA for handoff parameters and cross-browser testing.
  - Launch to production.
- Post-Launch:
  - Add analytics events for “Enroll Now.”
  - SEO polish pass (metadata, sitemap, structured data if appropriate).
  - Iterate on conversion optimization if needed.

Roles and Responsibilities
- Project Initialization Consultant: drive requirements capture, alignment with backend contracts, and define conversion-focused IA.
- Developer/Owner: implement pages per Figma, integrate public endpoints, ensure correct handoff behavior, and manage deployment.

Acceptance Criteria
- Navigation includes Home, Teachers, Pricing/Options, Enroll Now, Contact per Figma.
- “Enroll Now” CTA constructs URL:
  - https://app.cedarheightsmusic.com/enroll/start?instrument_id=&teacher_id=&timeslot_id=&billing_frequency=&source=public_site
- Configurator functions on public site:
  - Week 1 with mocks; pre-launch with live data.
- Footer includes Privacy Policy and Terms links.
- Performance targets met on key pages at 75th percentile mobile devices.
- Content placeholders replaced with provided bios/photos prior to launch.

Next Steps and Immediate Actions
- Implement IA and core pages per Figma with placeholder content.
- Build Pricing/Options configurator with mock data and indicative pricing calculations.
- Wire “Enroll Now” button to confirmed URL with params.
- Prepare data adapters to swap from mocks to GET /public/teachers and GET /public/timeslots.
- Add footer links for Privacy and Terms.
- Coordinate with backend for allowed origins and confirm public endpoint stability.