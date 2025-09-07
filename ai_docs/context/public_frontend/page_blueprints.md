# Cedar Heights Music Academy — Public Website Page Blueprints (v1)

Authoritative alignment:
- Primary sources: [design_brief.md](ai_docs/context/core_docs/design_brief.md), [information_architecture.md](ai_docs/context/core_docs/information_architecture.md), [prd.md](ai_docs/context/core_docs/prd.md), [wbs.md](ai_docs/context/core_docs/wbs.md)
- Visual intent only (brand strings in these exports are placeholders): [html_home.html](ai_docs/context/design_elements/html_home.html), [html_about.html](ai_docs/context/design_elements/html_about.html), plus assets [navigation.png](ai_docs/context/design_elements/navigation.png), [hero.png](ai_docs/context/design_elements/hero.png), [about_hero.png](ai_docs/context/design_elements/about_hero.png), [about_secondary_section.png](ai_docs/context/design_elements/about_secondary_section.png), [secondary_section.png](ai_docs/context/design_elements/secondary_section.png), [image_cluster.png](ai_docs/context/design_elements/image_cluster.png), [scheduling.png](ai_docs/context/design_elements/scheduling.png), [Button.png](ai_docs/context/design_elements/Button.png)

Purpose: Define a minimal, conversion-focused plan for a single-teacher studio (fewer than 10 students) that adheres to the Design Brief and IA.

Confirmed v1 routes
- Home (/)
- About (/about)
- Pricing (/pricing)
- Enroll (/enroll)
- Contact (/contact)
- Privacy (/privacy)
- Terms (/terms)

Global layout, brand, and tone
- Canvas: 1300px content width on desktop with 50–80px horizontal padding; warm off-white backgrounds with occasional accent bands.
- Typography: Display accent for the wordmark; DM Sans (or equivalent per tokens) for headings/body.
- Palette: Primary green (#99E39E) from provided assets; dark text #000510; warm yellow accents.
- Spacing: Vertical rhythm ~80–120px between sections.
- Imagery: Rounded photos, small collage clusters; avoid “large team” visuals (single teacher).
- Components: Buttons, simple cards, small inline accordion; minimal stat chips; no large counters.

Shared global elements
- Header/Nav (sticky)
  - Left: Wordmark “Cedar Heights Music Academy”. **DO NOT FUCKING CHANGE** 
  - Right: Nav items: Home, About, Pricing, Enroll, Contact. Active state indicated per design system.
  - Behavior: Sticky on scroll; mobile hamburger to slide-out drawer.
- Footer
  - Columns: Brand + short description; Links (About, Pricing, Enroll, Contact); Legal (Privacy, Terms); Social row.
  - Bottom bar: Copyright line “Cedar Heights Music Academy © 2025. All rights reserved.”
- Primary CTAs
  - Enroll Now (primary)
  - Contact (secondary)

Page blueprints

Home (/)
Purpose: Quickly orient parents and funnel to Enroll while establishing trust for a single-teacher studio.
Sections in order:
1) Hero
- Position: Above the fold; centered stack within content width; header sits above hero (sticky).
- Canvas: 1300px wide section, centered content group within ~856px max width (aligns with the centered content block used in the export).
- Stack order (z-index top to bottom):
  1) Foreground content group (tagline → headline → CTAs)
  2) Decorative accent layer (soft glows, small shapes; low opacity)
  3) Full-width seasonal background band (optimized image)
- Background image band:
  - Source: Seasonal hero (replace BeatWave visuals with Cedar Heights photo/illustration).
  - Scaling: Cover; focal point center for desktop, top-center for mobile to keep faces/instruments visible.
  - Contrast: If background is busy, add a very soft radial or linear gradient behind the text group (not a heavy overlay) so headline/CTA meet AA.
- Elements (foreground):
  - Tagline (small, above headline)
    - Copy: "Personal, one-on-one music lessons in Cedar & Nanaimo"
    - Type scale: ~16px desktop (line-height ≈ 22.4px), ~14px mobile (line-height ≈ 20px)
    - Weight: Regular (400–500); Color: #000510 at 80–100% opacity
    - Alignment: Center desktop/tablet; center mobile
  - Headline (primary hero H1)
    - Copy: "Your music journey starts in Cedar."
    - Type scale target: ~56–64px desktop (line-height ≈ 1.15–1.2), ~34–40px mobile (line-height ≈ 1.2)
    - Weight: Medium/Semibold; Use brand display accent sparingly (optional emphasis on 1–2 words only if it reads naturally for Cedar Heights brand)
    - Max width: ~800–860px for readable centering; alignment: center
  - CTAs (inline-flex with 8–12px gap)
    - Primary CTA: "Enroll Now" → /enroll (triggers modal)
      - Style: Green pill (background #99E39E), 12px radius, horizontal padding ≈ 24px, vertical ≈ 13px
      - Text: #000510; weight 600; optional right-arrow icon (20×20) with 8px gap
      - States: hover (slightly darker green or subtle elevation), focus-visible ring, active press state
    - Secondary CTA: "Contact" → /contact
      - Style: Outline or neutral-fill pill; maintain at least 44×44px tap target on mobile
- Decorative accents (restore subtle depth, not busyness):
  - Small soft glows/shape chips lightly behind the content group (e.g., faint circles/ellipses)
  - Keep opacity low (≈10–20%) and avoid overlapping the headline's core letterforms
  - Do NOT introduce multi-person "team" imagery (single-teacher studio constraint)
  - Foreground figure (Boy+Guitar) placement
    - Asset: [boy+guitar.png](public/boy+guitar.png)
    - Desktop placement:
      - Anchor to the hero foreground region (not the viewport), bottom-left so it sits left of the centered text stack
      - Horizontal offset: ~120–180px from the section's left edge (tune to avoid touching copy)
      - Vertical offset: intentional overflow below the hero by −48 to −72px so the figure extends beneath the hero background band into the next section
      - Z-order: background band (base) < figure (middle) < text/CTAs (top). CTAs must remain fully tappable/focusable above the figure
      - Container: hero wrapper allows overflow: visible; the next section adds top padding equal to the overlap (≈48–72px) to prevent collision
      - Clear zones: keep ≥24px from the headline bounding box and ≥16–24px from CTAs
    - Tablet (768–1199px):
      - Scale width to ~220–260px; reduce overflow to −24 to −40px; keep to the left of the centered stack without shifting the headline off-center
    - Mobile (<768px):
      - Option A: center near bottom behind content at 10–15% opacity (no overflow)
      - Option B: hide if it competes with readability; hero copy/CTAs take priority
    - Accessibility: decorative only (empty alt or role="presentation"); must not obscure focus rings or tap targets
    - Performance: provide WebP/AVIF variant and @2x; avoid layout shift by loading with the hero if visible on mobile
- Header and nav relationship:
  - Sticky header sits above hero and should not overlap text on small screens
  - Use the nav item set defined in IA: Home, About, Pricing, Enroll, Contact (active state styles per design system)
  - Ensure brand lockup at left (Cedar Heights Music Academy, not BeatWave)
- Spacing rhythm (desktop → mobile):
  - Top offset below sticky header: ~80–120px → ~56–80px
  - Tagline to headline gap: ~8–12px → ~6–10px
  - Headline to CTAs gap: ~16–24px → ~12–16px
  - Section bottom to next section: ~80–120px → ~56–80px
- Accessibility:
  - H1 must be the semantic page heading for the hero
  - Ensure headline and CTA text meet WCAG AA contrast against the background (with the soft gradient if needed)
  - Buttons must have visible focus styles; ensure 44×44px minimum tap targets
- Responsive behavior:
  - Tablet (768–1199px): Headline ~44–52px; keep center alignment; maintain pill size with slightly reduced H padding if needed
  - Mobile (<768px): Headline ~34–40px; tagline ~14px; CTAs may stack vertically with 8–12px gap; ensure safe areas
  - Background crops must preserve the visible subject (use art-directioned sources if necessary)
- Performance:
  - Optimize the hero image: serve desktop/tablet/mobile variants; lazy-load any non-critical decorative images; preconnect/preload fonts responsibly

2) Value Props (3 compact cards) (3 compact cards)
- Position: Below hero; three cards in equal-width columns.
- Example copy (adjust per Design Brief):
  - “Patient, professional instruction”
  - “Flexible scheduling”
  - “Beginner-friendly studio”
- Functions: Optional “Learn more” text links route to /about.

3) About teaser
- Position: Two-column band; left text, right small image collage
- Left elements:
  - Eyebrow: “About the studio”
  - Heading: “Personalized lessons from your dedicated teacher”
  - Paragraph: Short intro aligned with Design Brief narrative.
  - Inline link: “Meet your teacher” → /about#teacher
- Right elements:
  - Rounded image collage; minimal accents. `girl+guitar.png`

4) Simple availability snippet (optional if data ready)
- Title: "Open slots this week"
- Up to 6 small "slot" chips (e.g., Mon 4:00 PM, Wed 5:30 PM, Thu 6:00 PM). Visual reference: [scheduling.png](ai_docs/context/design_elements/scheduling.png)
- Slot chip design specifications:
  - Layout: Rectangular cards arranged in a 3×2 grid (desktop) or stacked vertically (mobile)
  - Dimensions: Approximately 200×80px per chip with 12px border radius
  - Typography:
    - Day label: Bold, ~14px, positioned at top-left (e.g., "Monday")
    - Time range: Two-tone display with start time in green (#4CAF50) and end time in red/orange (#FF5722), separated by a bullet point, ~12px font size
    - Format: "9:30 PM • 10:00 PM"
  - Visual states:
    - Default: Light gray/off-white background (#F5F5F5) with subtle border
    - Selected/highlighted: Warm yellow/orange background (#FFB74D) to indicate preferred or featured slots
    - Hover: Slight elevation shadow and background color shift
  - Spacing: 12px gaps between chips both horizontally and vertically
  - Accessibility: Each chip functions as a clickable button with proper focus states and ARIA labels
- Primary button "Enroll Now" → /enroll
- Data: Mock-first; pre-launch switch to live per [prd.md](ai_docs/context/core_docs/prd.md).

5) Micro-FAQ (inline)
- Position: Single-row accordion with 2–3 common Q&A (e.g., age range, lesson length, cancellation basics).
- No standalone FAQ page in v1.

6) Footer
- Global footer as specified.

About (/about)
Purpose: Build trust via studio story and single teacher introduction.
Sections in order:
1) Hero
- Visual reference: [about_hero.png](ai_docs/context/design_elements/about_hero.png)
- Layout structure:
  - Eyebrow text: Small, centered tagline above main headline (e.g., "Stream, discover, and connect" - adapt for Cedar Heights)
  - Main headline: Large, bold, centered typography (e.g., "Meet the Masters Behind the Music" - adapt to "Teaching music with heart and patience")
  - Typography hierarchy: Eyebrow ~16px, headline ~48-56px desktop, responsive scaling for mobile
- Background composition:
  - Base: Warm off-white/cream background (#FCF4E2 or similar ripe wheat tone)
  - Central element: `Group 255.png` positioned as large circular/organic background shape, centered, occupying ~60% width
  - Layering: Background shape behind character, character in foreground
- Character illustration:
  - Asset: `girl+guitar.png` positioned in right-center of the background shape
  - Style: Friendly, approachable illustration showing person with guitar in relaxed, seated position
  - Positioning: Character sits within/on the background shape, creating integrated composition
  - Scale: Character sized to feel welcoming and personal, not overwhelming
- Decorative elements:
  - Musical accents: Small music notes, treble clefs scattered around the composition at low opacity
  - Organic shapes: Soft, rounded background elements in warm yellow/gold tones
  - Visual depth: Subtle layering with drop shadows and overlapping elements
- Call-to-action:
  - Primary CTA: Green button with arrow (e.g., "Explore more →" - adapt to "Enroll Now")
  - Positioning: Centered below headline, integrated into the background shape design
  - Secondary CTA: "Contact" positioned as secondary button or link
- Responsive behavior:
  - Mobile: Stack elements vertically, reduce character size, maintain warm background treatment
  - Tablet: Scale proportionally while preserving centered composition
- Overall tone: Warm, inviting, and personal - emphasizing the human connection in music education

2) Studio Story
- Two-column layout aligned to [about_secondary_section.png](ai_docs/context/design_elements/about_secondary_section.png).
- Left column content:
  - Eyebrow: "About us" (small, uppercase, positioned above main heading)
  - Main heading: Large, bold typography (e.g., "Master Music from the Core and Achieve Excellence" - adapt for Cedar Heights)
  - Body content: 1–2 short paragraphs about values and community in readable paragraph format
  - Feature highlights: Two small icon-text pairs below paragraphs:
    - "Private Lessons" with checkmark icon
    - "Kids, Teens & Adults Groups" with checkmark icon (adapt to single-teacher model)
- Right column: Image cluster arrangement per [image_cluster.png](ai_docs/context/design_elements/image_cluster.png)
  - Layout: Asymmetrical grid with 4 rounded-corner photographs
  - Primary image (large): Top-left position, showing teacher-student interaction (guitar lesson scene)
  - Secondary images (smaller):
    - Top-right: Individual lesson or practice scene
    - Bottom-left: Small intimate lesson setting
    - Bottom-right: Close-up of hands on instrument (piano/guitar)
  - Spacing: 12-16px gaps between images with subtle drop shadows
  - Image treatment: All photos have consistent rounded corners (~8-12px radius) and warm, natural lighting
  - Content focus: Authentic teaching moments, instrument close-ups, and student engagement
- Background elements: Subtle decorative musical icons (treble clef, music notes) positioned as light accent elements
- Overall tone: Warm, professional, and community-focused with emphasis on personal instruction

3) Teacher Card (single)
- Photo (120×120 rounded), name, instruments taught, short bio (3–4 lines).
- Optional small “Typically evenings” or “Open Wed/Thu” chips instead of big stats.

4) Compact CTA band
- Short line “Ready to start?” + button “Enroll Now” → /enroll

5) Footer
- Global footer.

Pricing (/pricing)
Purpose: Communicate simple, indicative pricing and route to Enroll.
Sections in order:
1) Hero
- Layout structure:
  - Eyebrow text: "Transparent pricing" (small, centered, positioned above main headline)
  - Main headline: "Quality music education that fits your family"
  - Subcopy: "Clear, straightforward pricing with flexible payment options. No hidden fees, no surprises—just honest pricing for exceptional music instruction."
  - Typography hierarchy: Eyebrow ~16px, headline ~48-56px desktop, subcopy ~18px with comfortable line spacing
- Background composition:
  - Base: Warm off-white/cream background consistent with brand palette
  - Optional seasonal background element (subtle, non-distracting)
  - Clean, professional layout emphasizing transparency and trust
- Visual elements:
  - Minimal decorative accents to maintain focus on pricing information
  - Optional small musical note icons as subtle background elements
  - Emphasis on clean, readable typography over heavy graphics
- Content focus:
  - Value proposition: Quality education at fair prices
  - Trust building: Transparency and no hidden costs
  - Family-friendly: Pricing that works for family budgets
  - Flexibility: Multiple payment options to suit different needs
- Call-to-action preparation:
  - Sets expectation that final pricing is confirmed during enrollment
  - Builds confidence in the transparent, family-focused approach
  - Leads naturally into billing frequency selector below
- Tone: Professional yet warm, emphasizing value and transparency over cost

2) Billing Frequency Selector
- Options: Monthly | Yearly | Semester (per [prd.md](ai_docs/context/core_docs/prd.md)).
- Shows indicative price mapping per selection; clearly labeled “indicative”.
- Note: “Final pricing confirmed during enrollment.”

3) CTA Block
- Primary: “Enroll Now” → /enroll
- Secondary: “Contact” → /contact

4) Footer
- Global footer.

Enroll Modal (triggered from any page)
Purpose: 3-step modal configurator that passes context to the protected app.
Modal specifications:
1) Modal Layout
- Trigger: "Enroll Now" buttons throughout the site
- Display: Full-screen on mobile, centered overlay (max-width 600px) on desktop
- Background: Semi-transparent dark overlay with warm accent
- Close options: X button, ESC key, click outside (with confirmation if partially completed)

2) Modal Header
- Title: "Start Your Musical Journey"
- Subtitle: "Just 3 quick steps to get started"
- Progress indicator: Visual step counter (Step 1 of 3, 2 of 3, 3 of 3)

3) Stepper (3 modal screens)
- Step 1: Instrument selection
  - Title: "Choose Your Instrument"
  - Options: Piano, Guitar, Violin, etc. (with icons)
  - Note: "30-minute lessons" displayed as standard
- Step 2: Preferred timeslot
  - Title: "Pick Your Perfect Time"
  - Data source: Mock week 1 → Pre-launch live GET /public/timeslots
  - Display: Available slots in easy-to-scan format
- Step 3: Billing frequency
  - Title: "Choose Your Payment Plan"
  - Options: Monthly | Yearly | Semester with pricing preview
  - Note: "Final pricing confirmed during enrollment"

4) Navigation
- Back/Next buttons with clear labeling
- "Save & Continue Later" option on each step
- Final step: "Complete Enrollment" button

5) Completion behavior
- Success message: "Almost there! Redirecting you to complete enrollment..."
- Redirect to https://app.cedarheightsmusic.com/enroll/start with params:
  - instrument_id, teacher_id (optional if implied by timeslot), timeslot_id, billing_frequency, source=public_site
- Behavior and URL contracts per [prd.md](ai_docs/context/core_docs/prd.md).

6) Modal UX Features
- Auto-save progress in localStorage
- Smooth transitions between steps
- Mobile-optimized touch interactions
- Accessible keyboard navigation
- Loading states for API calls

Contact (/contact)
Purpose: Provide a simple way for parents to reach out.
Sections in order:
1) Hero
- Layout structure:
  - Eyebrow text: "Get in touch" (small, centered, positioned above main headline)
  - Main headline: "We're here to help with your musical journey"
  - Subcopy: "Questions about lessons? Want to discuss your child's musical goals? We'd love to hear from you and help you get started."
  - Typography hierarchy: Eyebrow ~16px, headline ~48-56px desktop, subcopy ~18px with comfortable line spacing
- Background composition:
  - Base: Warm off-white/cream background consistent with brand palette
  - Optional subtle musical accent elements (music notes, soft shapes) at low opacity
  - Clean, approachable layout emphasizing accessibility and warmth
- Visual elements:
  - Minimal decorative accents to maintain focus on communication
  - Optional small character illustration or musical instrument icon
  - Emphasis on welcoming, open communication rather than formal business contact
- Content focus:
  - Approachability: Easy, friendly way to get in touch
  - Support: Emphasizes help and guidance rather than sales
  - Personal connection: Reinforces the one-on-one, caring approach
  - Accessibility: Multiple ways to connect (form, email, phone)
- Tone: Warm, welcoming, and supportive - emphasizing the caring, personal approach to music education
- Call-to-action preparation:
  - Sets expectation for helpful, personal response
  - Builds confidence in the supportive teaching approach
  - Leads naturally into contact form and direct contact options below

2) Contact Form
- Fields: Name, Email, Phone (optional), Message, consent checkbox.
- Client-side Formspree (or similar); honeypot for spam.
- Clear success/failure states.

3) Direct Info
- Email link, phone, hours or “by appointment”.
- Optional map or service area note.

4) Footer
- Global footer.

Privacy (/privacy) and Terms (/terms)
Purpose: Legal transparency.
- Each is a simple static page with headings, lists, and updated dates.
- Linked from footer; directly accessible via routes.

Key interactive behaviors (minimal v1)
- Enroll stepper: Mock-first → live endpoints pre-launch; redirect builder per PRD.
- Inline accordions: Home micro-FAQ only; accessible keyboard interactions.
- Navigation: Sticky header; active page styles; mobile drawer.

Responsive layout guidelines
- Desktop (≥1200px): 12-column grid; ~80px section padding.
- Tablet (768–1199px): 8-column grid; ~48px padding.
- Mobile (<768px): 4-column grid; ~24px padding; stacked sections.

Mapping to design assets
- Header/nav: [navigation.png](ai_docs/context/design_elements/navigation.png)
- Home hero: [hero.png](ai_docs/context/design_elements/hero.png)
- Secondary sections/cards: [secondary_section.png](ai_docs/context/design_elements/secondary_section.png)
- About hero/content: [about_hero.png](ai_docs/context/design_elements/about_hero.png), [about_secondary_section.png](ai_docs/context/design_elements/about_secondary_section.png)
- Collage: [image_cluster.png](ai_docs/context/design_elements/image_cluster.png)
- Scheduling/Stepper cues: [scheduling.png](ai_docs/context/design_elements/scheduling.png)
- Visual intent exports: [html_home.html](ai_docs/context/design_elements/html_home.html), [html_about.html](ai_docs/context/design_elements/html_about.html)

Acceptance criteria checklist (v1 scope)
- Global:
  - Header includes Home, About, Pricing, Enroll, Contact; footer includes Privacy and Terms.
  - Mobile responsive layouts meet breakpoints; images optimized/lazy where applicable.
- Home:
  - Hero with primary CTA to /enroll; value props; About teaser; optional availability; micro-FAQ inline.
- About:
  - Studio story; single teacher card; compact CTA band.
- Pricing:
  - Billing frequency selector shows indicative pricing; CTA to /enroll.
- Enroll:
  - 3-step flow; redirect URL built with required params; mock-first with pre-launch live switch.
- Contact:
  - Client-side form with consent and honeypot; success/failure states.
- Privacy/Terms:
  - Static pages accessible via footer.

Notes
- Remove all “BeatWave” brand references from design exports during implementation; substitute with Cedar Heights Music Academy branding and copy per [design_brief.md](ai_docs/context/core_docs/design_brief.md).
## Home Hero — Headline options (replace the current placeholder)

Purpose: Provide a stronger, parent-centered headline for the hero that aligns with the Design Brief (trust-first, single-teacher studio, local) and increases conversion to Enroll.

Guidelines
- Length: 4–8 words preferred; keep to one line on mobile when possible.
- Tone: Warm, patient, confidence-building; avoid big-brand hype.
- Audience: Parents and beginners in Cedar/Nanaimo BC.
- CTA pairing: Primary “Enroll Now”, secondary “Contact”.

Primary recommendation
- Headline: “Where Your Musical Journey Begins”
- Subheadline: “One-on-one instruction in Cedar Heights—patient, flexible, beginner‑friendly.”

Additional vetted options (choose one)
1) “Start music with confidence.”
   - Sub: “Friendly one-on-one lessons for kids and adults in Cedar Heights.”
2) “Small studio. Big progress.”
   - Sub: “One teacher. Focused attention. Real results.”
3) “Your music journey starts here.”
   - Sub: “Personal lessons that meet you where you are.”
4) “Learn faster with one-on-one lessons.”
   - Sub: “Personal instruction that fits your family’s schedule.”
5) “Build a lifelong love of music.”
   - Sub: “Encouraging, private lessons in Cedar Heights.”
6) “Local, patient music lessons.”
   - Sub: “Simple scheduling and clear progress every week.”
7) “From first note to confident playing.”
   - Sub: “Supportive lessons tailored to your goals.”
8) “Learn the right way, from day one.”
   - Sub: “Beginner-friendly lessons for kids and adults.”
9) “Consistent lessons. Confident playing.”
   - Sub: “Weekly one-on-one instruction that fits family life.”
10) “Personal lessons. Real results.”
    - Sub: “Focused, one-on-one teaching for steady progress.”

Implementation notes
- Replace the current Home hero headline and subheadline with the chosen pair.
- Keep CTA labels as “Enroll Now” (primary) and “Contact” (secondary) to match the funnel.
- If space is tight, omit the subheadline on mobile; retain on tablet/desktop for trust copy.