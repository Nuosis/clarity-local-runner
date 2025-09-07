# System Architecture Outline — Draft (Do Not Finalize)

Status: Outline-only draft capturing explicitly approved decisions. No unapproved assumptions are included.

Purpose
- Provide a concise, authoritative outline of the frontend architecture and integration approach for the public website MVP.
- Record decisions agreed in this consultation and list open questions to resolve before producing the final ARCHITECTURE.md.
- Align with the existing Frontend Integration Guide while reflecting the website’s no end-user auth requirement.

Approved Decisions

1) Frontend Stack
- Language: TypeScript
- Framework/Build: React + Vite
- Routing: react-router-dom
- Server State: TanStack Query (for caching, retries, and optional polling)
- Styling: Tailwind CSS
- UI Scope (MVP): Public website integrating only:
  - GET /public/teachers
  - GET /public/timeslots?teacher_id=&weekday=&active=true

2) Authentication and Access Model (Website)
- No end-user auth on the website.
Approved Updates — Resolved Open Questions 1–3

A) MVP Route Map (from PRD) — CONFIRMED
- /            Home
- /about       About the academy, teacher bios (static v1)
- /pricing     Billing frequency selection; indicative pricing only
- /enroll      3-step configurator (instrument → preferred timeslot → billing frequency); mock → live public endpoints pre-launch
- /contact     Client-side form via Formspree (or similar)
- /privacy     Static policy page
- /terms       Static policy page

B) API Domain and Networking — CONFIRMED
- Production API base URL: https://api.cedarheightsmusic.com
- Frontend calls API domain directly (no website proxy path) for MVP public-only endpoints.
- Note (future protected calls): If any protected reads/writes are added later, they must go through a Vercel server/edge proxy that injects the shared-secret M2M Authorization header (secret kept in server/edge env, never exposed to the browser).

C) Freshness Policy — CONFIRMED
- Edge caching: stale-while-revalidate (SWR) with TTL = 120 seconds and background revalidation for:
  - GET /public/teachers
  - GET /public/timeslots
- Frontend TanStack Query alignment:
  - Set staleTime = 120_000 ms for queries that fetch these endpoints to match edge caching behavior.
- Machine-to-Machine (M2M) shared secret pattern is approved for any protected calls (not used for MVP public-only endpoints).
- Secret storage and use:
  - Use a server/edge proxy (e.g., Vercel Serverless/Edge Function) that reads the secret from environment variables and injects Authorization: Bearer <M2M_SECRET> when calling FastAPI.
  - The browser never receives the secret; the proxy exposes only safe routes to the client.
- Public endpoints remain unauthenticated for fastest TTFB and simpler caching.

3) Caching Strategy for Public Endpoints
- Enable edge CDN caching with stale-while-revalidate (SWR).
- TTL: 120 seconds, background revalidation enabled.
- Applies to:
  - GET /public/teachers
  - GET /public/timeslots
- Goal: improve performance while keeping data reasonably fresh.

4) Deployment and Configuration
- Frontend Hosting: Vercel
- Environment-specific API base URL: configured via environment variables for dev/staging/prod.
- Edge/Server proxy (for any future protected calls) will also be hosted on Vercel and configured via env vars.

Integration Surfaces — MVP Website

- Read-only public discovery flows:
  - Teachers: GET /public/teachers
  - Timeslots: GET /public/timeslots?teacher_id=&weekday=&active=true
- Client behavior:
  - Use TanStack Query for fetching and caching; set query options to align with SWR TTL if appropriate.
  - Route organization via react-router-dom; define public pages in accordance with design and information architecture.
- No protected calls in MVP:
  - If future pages require protected reads/writes, they must route through the server/edge proxy that injects the M2M Authorization header.

Security Posture — MVP Website

- Secrets are not exposed to the client; all secrets confined to server/edge runtime.
- Public endpoints are intentionally unauthenticated; ensure backend CORS and rate limits are appropriate for public access.
- For future protected calls via proxy:
  - Limit proxy routes to minimum necessary paths.
  - Enforce input validation and response size/time limits.
  - Add basic abuse protections on the proxy (e.g., IP-based throttling if needed).

Observability and Monitoring — MVP Website

- Minimal baseline:
  - Basic client error logging (console in dev).
  - Consider adding a frontend error tracker (e.g., Sentry) later; correlate with backend logs if tracing IDs are exposed in responses.
- Edge/Server proxy:
  - Log request metadata (method, path, duration, status) without PII.
  - Emit structured logs in production.

Figma Adherence

- The website must adhere strictly to the provided Figma design for structure and styling.
- Tailwind CSS will be configured to match design tokens (colors, spacing, typography) as defined by Figma. The exact token mapping will be captured during implementation and then documented in the final architecture once confirmed.

Open Questions (Require Decisions Before Final Document)

1) Public Information Architecture
- Exact route map and page breakdown derived from Figma (e.g., /, /teachers, /lessons, /contact). Confirm the initial set of routes and their data needs.

2) API Domain and Networking
- What is the production FastAPI base URL?
- Will a custom domain/subdomain be used for the API (e.g., api.cedarheightsmusic.com), and should the Vercel proxy live under the website domain (e.g., www.cedar…/api/*) for same-origin benefits?

3) Data Freshness Controls
- Beyond SWR TTL=120 seconds, do we require admin-triggered cache revalidation (on publish) for critical updates? If yes, what’s the trigger mechanism (webhook, CLI, manual dashboard action)?

4) Edge/Server Proxy Scope (Future)
- Which specific protected endpoints, if any, are expected next after MVP public-only scope? Define read-only vs write needs to shape authorization and rate limiting policies.

5) Analytics and Metrics
- What analytics platform (if any) will be used (e.g., Plausible, GA4)? Any privacy constraints or consent banners required?

6) Accessibility and Internationalization
- Accessibility baseline targets (e.g., WCAG 2.1 AA)? Any i18n needs post-MVP (the guide notes English-only for now)?

7) Error UX for Public Fetches
- Confirm the user-facing copy/behavior when public endpoints fail (e.g., fallback content, retry button) and whether to surface a “last updated” timestamp when serving from cache.

8) Tailwind Design Tokens
- Confirm token values (colors, typography scale, spacing). Should we extract a shared tailwind.config.js aligned to Figma tokens right away?

Non-Goals (MVP)
- Parent SPA with self-booking, status polling, and payment flows (this is deferred; the current website is public-only).
- Admin UI (CRUD, attendance, dashboards) — deferred.

References
- Frontend Integration Guide: ai_docs/guides/FRONTEND_INTEGRATION_GUIDE.md
- Project Charter and PRD (for broader context):
  - ai_docs/context/core_docs/project_charter.md
  - ai_docs/context/core_docs/prd.md

Next Steps
- Resolve Open Questions 1–3 to finalize routes, API domain, and freshness policy.
- After resolution, proceed to generate the full ARCHITECTURE.md with finalized details and remove the “draft” status.
