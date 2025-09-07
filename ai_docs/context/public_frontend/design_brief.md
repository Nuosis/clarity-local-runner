# Cedar Heights Music Academy — Design Brief
**Version 1.0 | Date: August 21, 2025**

## Executive Summary

This Design Brief establishes the comprehensive UI/UX foundation for Cedar Heights Music Academy's public marketing website. The goal is to create a **beautiful, useful, and clean** interface that increases enrollment by 20% in 6 months through a conversion-focused, nurturing user experience that guides parents seamlessly from discovery to enrollment.

## Design Vision Statement

**"A warm, nurturing digital community where parents feel confident their child will be cared for, encouraged, and inspired to grow musically."**

### Core Emotional Goal
**Warmth & Nurturing Community** - Parents should immediately feel this is a safe, supportive environment where their child will be cared for and encouraged, not just a business transaction.

### Emotional Consistency Strategy
Maintain the same warm, supportive tone throughout all pages (Home → About → Pricing → Enroll) for maximum emotional consistency and trust-building.

## Visual Design System

### Design Authority
- **Primary Source**: Figma Design System - https://www.figma.com/design/8iXCoxrnEkJaAEVERBY4wr/Music?node-id=0-1&p=f&t=mEFgAvR3fs6muKHj-0
- **Constraint**: Strict adherence required for brand trust and consistency
- **Reference Materials**: Design elements in `ai_docs/context/design_elements/` (Button.png, hero.png, image_cluster.png, navigation.png, scheduling.png, secondary_section.png)

### Color Palette
- **Primary**: Warm browns (#2c1810, #8b4513, #a0522d)
- **Accent**: Gold (#ffd700, #ffed4e)
- **Hero Background**: Ripe wheat (rgb(252, 244, 226)) - warm, nurturing base color
- **Strategy**: Maintain exact Figma color relationships across all pages for maximum brand recognition
- **Application**: Colors convey warmth, quality, and approachability

### Typography
- **Current Foundation**: System fonts with clean hierarchy
- **Requirement**: Follow Figma typography specifications exactly
- **Accessibility**: Ensure WCAG 2.1 AA contrast ratios

## Unique Features & Innovations

### Seasonal Background System
- **Concept**: Hero background changes based on time of year
- **Assets**: 
  - Summer: `summer_bg_lrg.png`
  - Fall: `fall_bg.png` 
  - Winter: `winter_bg_lrg.png`
- **Benefits**: Creates returning visitor engagement and seasonal relevance
- **Implementation**: Date-based logic for automatic background selection

### Character Assets
- **Available**: `boy+guitar.png`, `girl+guitar.png`, `girl&guitar.png`
- **Usage**: Friendly, approachable imagery supporting the nurturing community feeling
- **Brand Elements**: `logo.JPG`, `Group 255.png`, `Mask group.png`

## Complete Asset Map

### Visual Assets Inventory (Repository Paths)

#### Brand Identity Assets
- **Primary Logo**: `public/logo.JPG` (280x280px, JPG format)
- **Brand Graphics**:
  - `public/Group 255.png` (Brand element/icon)
  - `public/Mask group.png` (Brand element/mask)

#### Seasonal Background System
- **Base Color**: Ripe wheat (rgb(252, 244, 226)) - warm, nurturing foundation
- **Summer Background**: `public/summer_bg_lrg.png` (Large format, hero background) - **ACTIVE**
- **Fall Background**: `public/fall_bg.png` (Large format, hero background)
- **Winter Background**: `public/winter_bg_lrg.png` (Large format, hero background)
- **Implementation**: Background images overlay the ripe wheat base color for enhanced warmth

#### Character Illustrations
- **Boy with Guitar**: `public/boy+guitar.png` (Hero character, right-positioned)
- **Girl with Guitar (Version 1)**: `public/girl+guitar.png` (Alternative character)
- **Girl with Guitar (Version 2)**: `public/girl&guitar.png` (Alternative character)

#### Design Reference Elements (Figma-based)
- **Hero Layout Reference**: `ai_docs/context/design_elements/hero.png`
- **Button Specifications**: `ai_docs/context/design_elements/Button.png`
- **Navigation Design**: `ai_docs/context/design_elements/navigation.png`
- **Secondary Section Layout**: `ai_docs/context/design_elements/secondary_section.png`
- **About Page Hero**: `ai_docs/context/design_elements/about_hero.png`
- **About Secondary Section**: `ai_docs/context/design_elements/about_secondary_section.png`
- **Image Cluster Layout**: `ai_docs/context/design_elements/image_cluster.png`
- **Scheduling Interface**: `ai_docs/context/design_elements/scheduling.png`

#### Technical Assets
- **React Default**: `src/assets/react.svg` (Framework asset, not user-facing)

### Asset Usage Guidelines
- **Seasonal Logic**: Backgrounds rotate based on date (Summer: Jun-Aug, Fall: Sep-Nov, Winter: Dec-Feb, Spring: Mar-May defaults to Fall)
- **Character Positioning**: Hero characters positioned bottom-right with drop-shadow effects
- **Logo Treatment**: White background padding, rounded corners, shadow for contrast
- **Reference Authority**: Design elements serve as visual reference; actual branding uses Cedar Heights Music Academy identity

## Visual Authority Documentation

### Primary Design System Authority
- **Figma Design System URL**: https://www.figma.com/design/8iXCoxrnEkJaAEVERBY4wr/Music?node-id=0-1&p=f&t=mEFgAvR3fs6muKHj-0
- **Authority Level**: Primary visual authority for layout, typography, spacing, and component specifications
- **Usage Constraint**: Strict adherence required for brand trust and consistency
- **Adaptation Note**: Generic "Beat" branding in Figma adapted to Cedar Heights Music Academy identity

### Reference Asset Catalog with Provenance

#### Design Reference Elements (Figma-Derived)
**Source**: Exported from Figma design system for layout and component reference
**Location**: `ai_docs/context/design_elements/`
**Provenance**: Design system exports adapted for Cedar Heights Music Academy

- **Hero Layout Reference**: `hero.png`
  - **Purpose**: Homepage hero section layout and composition
  - **Usage**: Spatial relationships, character positioning, CTA placement
  - **Adaptation**: Replace "Beat" branding with Cedar Heights Music Academy elements

- **Button Specifications**: `Button.png`
  - **Purpose**: Primary and secondary button styling reference
  - **Usage**: Color gradients, border radius, typography, hover states
  - **Implementation**: Maintain visual style with Cedar Heights color palette

- **Navigation Design**: `navigation.png`
  - **Purpose**: Global navigation structure and styling
  - **Usage**: Menu layout, typography, active states, responsive behavior
  - **Adaptation**: Update navigation labels to match Cedar Heights page structure

- **Secondary Section Layout**: `secondary_section.png`
  - **Purpose**: Content section layout patterns
  - **Usage**: Grid systems, content hierarchy, spacing relationships
  - **Implementation**: Apply to About, Pricing, and other content pages

- **About Page References**:
  - `about_hero.png`: About page hero section layout
  - `about_secondary_section.png`: About page content sections
  - **Usage**: Teacher bio layouts, studio story presentation
  - **Adaptation**: Cedar Heights content with maintained visual structure

- **Image Cluster Layout**: `image_cluster.png`
  - **Purpose**: Multi-image arrangement patterns
  - **Usage**: Teacher photo galleries, feature showcases
  - **Implementation**: Maintain spacing and arrangement principles

- **Scheduling Interface**: `scheduling.png`
  - **Purpose**: Time slot selection and booking interface
  - **Usage**: Enrollment configurator step design
  - **Implementation**: Adapt for Cedar Heights timeslot selection flow

#### Production Assets (Cedar Heights Branded)
**Source**: Cedar Heights Music Academy brand assets
**Location**: `public/` directory
**Provenance**: Academy-provided brand materials and custom illustrations

- **Brand Identity Assets**:
  - `logo.JPG`: Official Cedar Heights Music Academy logo
  - `Group 255.png`, `Mask group.png`: Supporting brand elements
  - **Authority**: Primary brand identity source
  - **Usage**: Exact reproduction without modification

- **Seasonal Background System**:
  - `summer_bg_lrg.png`, `fall_bg.png`, `winter_bg_lrg.png`
  - **Source**: Custom seasonal illustrations for Cedar Heights
  - **Usage**: Hero background rotation based on calendar date
  - **Implementation**: Date-driven background selection logic

- **Character Illustrations**:
  - `boy+guitar.png`, `girl+guitar.png`, `girl&guitar.png`
  - **Source**: Custom character illustrations for music academy
  - **Usage**: Friendly, approachable hero imagery
  - **Positioning**: Bottom-right with drop-shadow effects

### Authority Hierarchy and Decision Framework

#### Primary Authority (Figma Design System)
- **Layout Structure**: Spatial relationships, grid systems, component positioning
- **Typography System**: Font families, sizes, weights, line heights, letter spacing
- **Color Relationships**: Color harmony, contrast ratios, gradient applications
- **Component Specifications**: Button styles, form elements, navigation patterns
- **Responsive Behavior**: Breakpoint definitions, mobile-first adaptations

#### Secondary Authority (Cedar Heights Brand Assets)
- **Brand Identity**: Logo usage, brand colors, brand voice and messaging
- **Content Strategy**: Academy-specific copy, teacher information, pricing structure
- **Seasonal Elements**: Background imagery, thematic variations
- **Character Design**: Illustration style, character positioning, visual personality

#### Conflict Resolution Protocol
1. **Brand Identity Conflicts**: Cedar Heights brand assets take precedence over Figma generic branding
2. **Layout Conflicts**: Figma design system takes precedence for spatial and structural decisions
3. **Content Conflicts**: Cedar Heights content and messaging take precedence
4. **Technical Conflicts**: Performance and accessibility requirements override visual preferences

### Implementation Validation Against Authority
- **Figma Overlay Comparison**: Use Figma design overlay to validate layout accuracy
- **Brand Compliance Check**: Ensure Cedar Heights logo and branding are correctly implemented
- **Asset Integrity Verification**: Confirm all assets load correctly and maintain quality
- **Responsive Validation**: Test design system breakpoints across device sizes
- **Authority Documentation**: Maintain clear record of design decisions and their authority source

## Information Architecture

### Page Structure (Per PRD)
- **Home (/)**: Hero with primary CTA, value propositions
- **About (/about)**: Studio story, teacher bios with photos
- **Pricing (/pricing)**: Billing frequency selection, indicative pricing
- **Enroll (/enroll)**: 3-step configurator → handoff to protected app
- **Contact (/contact)**: Client-side form via Formspree
- **Privacy (/privacy)** & **Terms (/terms)**: Static policy pages

### Navigation Strategy
- **Global Navigation**: Home, About, Pricing, Enroll, Contact
- **Footer**: Privacy, Terms, contact links
- **Consistency**: Maintain warm, nurturing tone across all touchpoints

## User Experience Design

### Primary User Journey
**Discovery → Trust Building → Enrollment**
1. **Home**: Immediate warmth and community feeling
2. **About**: Deepen trust through teacher expertise and studio story
3. **Pricing**: Transparent, approachable pricing information
4. **Enroll**: Streamlined conversion experience
5. **Handoff**: Seamless transition to protected enrollment system

### Enrollment Configurator UX
- **Strategy**: Streamlined wizard experience
- **Goal**: Fast, simple steps with clear progress indicators to minimize drop-off
- **Flow**: 
  1. Instrument selection (mapped to instrument_id)
  2. Preferred timeslot selection (from live API data)
  3. Billing frequency (monthly | yearly | semester)
- **Completion**: Immediate redirect to protected app with context parameters

### Progress Indicators
- **Visual**: Clear step progression (1 of 3, 2 of 3, 3 of 3)
- **Accessibility**: Screen reader announcements for progress
- **Design**: Consistent with Figma design system

## Accessibility Standards

### Compliance Level
**WCAG 2.1 AA** - Full industry standard accessibility for maximum inclusivity

### Key Requirements
- **Color Contrast**: Minimum 4.5:1 for normal text, 3:1 for large text
- **Keyboard Navigation**: Full keyboard accessibility for all interactive elements
- **Screen Readers**: Proper semantic HTML, ARIA labels, and announcements
- **Focus Management**: Clear focus indicators and logical tab order
- **Alternative Text**: Descriptive alt text for all images
- **Form Accessibility**: Proper labels, error messages, and validation feedback

### Implementation Strategy
- Semantic HTML5 structure
- ARIA landmarks and roles
- Skip navigation links
- Accessible form design with clear error handling
- Screen reader testing throughout development

## Performance Requirements

### Core Web Vitals Targets (75th percentile mobile)
- **LCP (Largest Contentful Paint)**: ≤ 2.5 seconds
- **CLS (Cumulative Layout Shift)**: ≤ 0.1
- **FID (First Input Delay)**: ≤ 100ms

### Optimization Strategy
- **Images**: Optimize and lazy-load all assets
- **Seasonal Backgrounds**: Preload current season, lazy-load others
- **Bundle**: Tree shaking, code splitting, minimize bundle sizes
- **Caching**: Leverage browser caching and CDN for static assets
- **Critical Path**: Prioritize above-the-fold content loading

## Technical Implementation

### Technology Stack
- **Framework**: React + Vite
- **Language**: TypeScript (per architecture requirements)
- **Routing**: react-router-dom
- **State Management**: TanStack Query for API caching
- **Styling**: Tailwind CSS configured to match Figma tokens
- **Performance**: Lazy loading, code splitting, optimized images

### Data Integration
- **Week 1**: Mock data for development
- **Pre-launch**: Live API endpoints
  - GET /public/teachers
  - GET /public/timeslots?teacher_id=&weekday=&active=true
- **Caching**: 120-second TTL with stale-while-revalidate

### Handoff Integration
- **Target URL**: https://app.cedarheightsmusic.com/enroll/start
- **Parameters**: instrument_id, teacher_id, timeslot_id, billing_frequency, source=public_site
- **Behavior**: Immediate redirect on configurator completion

## Component Design Patterns

### Reusable Components (Based on Figma)
- **Buttons**: Primary CTA, secondary actions, form buttons
- **Cards**: Teacher profiles, pricing options, feature highlights
- **Forms**: Contact form, configurator steps
- **Navigation**: Header navigation, footer links
- **Progress**: Step indicators, loading states
- **Modals**: Error messages, confirmations (if needed)

### Responsive Design
- **Mobile-First**: Primary design approach
- **Breakpoints**: Follow Figma responsive specifications
- **Touch Targets**: Minimum 44px for accessibility
- **Content Priority**: Ensure key actions remain prominent on all devices

## Content Strategy

### Voice & Tone
- **Warm**: Approachable and friendly language
- **Supportive**: Encouraging and nurturing
- **Professional**: Competent without being intimidating
- **Local**: Cedar/Nanaimo community connection
- **Consistent**: Same tone across all pages

### Key Messaging
- **Home**: "Nurturing young musicians in a supportive environment"
- **About**: Teacher expertise and studio community
- **Pricing**: Transparent, value-focused pricing
- **Enroll**: Simple, confident enrollment process
- **Contact**: Open communication and support

## Error Handling & Edge Cases

### Graceful Degradation
- **API Failures**: Fallback to cached data or helpful error messages
- **Image Loading**: Placeholder images while loading
- **JavaScript Disabled**: Basic functionality still available
- **Slow Connections**: Progressive loading with clear feedback

### User Feedback
- **Loading States**: Clear indicators during API calls
- **Error Messages**: Helpful, actionable error text
- **Success States**: Confirmation of completed actions
- **Form Validation**: Real-time, accessible validation feedback

## Success Metrics

### Conversion Goals
- **Primary**: 15 completed enrollments per month via public site
- **Secondary**: Increased click-through to enrollment flow
- **Tertiary**: Improved time-on-site and page engagement

### User Experience Metrics
- **Performance**: Meet Core Web Vitals targets
- **Accessibility**: Pass WCAG 2.1 AA automated and manual testing
- **Usability**: Low bounce rate on enrollment configurator
- **Trust**: Increased completion rate of contact forms

## Validation Criteria and Success Standards

### Design Fidelity Validation
- **Figma Adherence Threshold**: ≥95% visual accuracy to Figma design system
- **Color Accuracy**: Exact hex values match Figma specifications (±0 tolerance)
- **Typography Compliance**: Font families, sizes, weights, and line heights match Figma specs exactly
- **Spacing Precision**: Layout spacing within ±2px of Figma measurements
- **Component Consistency**: All UI components (buttons, forms, cards) match Figma component library

### Performance Validation Standards
- **Core Web Vitals (75th percentile mobile)**:
  - LCP (Largest Contentful Paint): ≤ 2.5 seconds (Target: ≤ 2.0 seconds)
  - CLS (Cumulative Layout Shift): ≤ 0.1 (Target: ≤ 0.05)
  - FID (First Input Delay): ≤ 100ms (Target: ≤ 50ms)
- **Page Load Speed**: Initial page load ≤ 3 seconds on 3G connection
- **Image Optimization**: All images compressed to ≤ 500KB without quality loss
- **Bundle Size**: JavaScript bundle ≤ 250KB gzipped

### Accessibility Validation Criteria
- **WCAG 2.1 AA Compliance**: 100% automated testing pass rate
- **Color Contrast**: All text meets minimum 4.5:1 contrast ratio (7:1 for enhanced)
- **Keyboard Navigation**: 100% of interactive elements accessible via keyboard
- **Screen Reader Compatibility**: Full functionality with NVDA, JAWS, and VoiceOver
- **Focus Management**: Clear focus indicators on all interactive elements
- **Alternative Text**: Descriptive alt text for all meaningful images

### Functional Validation Standards
- **Cross-Browser Compatibility**: 100% functionality across Chrome, Firefox, Safari, Edge
- **Responsive Design**: Perfect layout integrity across all breakpoints (320px - 1920px)
- **Form Validation**: Real-time validation with accessible error messages
- **Seasonal Background Logic**: Correct background rotation based on current date
- **API Integration**: Graceful handling of API failures with appropriate fallbacks

### User Experience Validation Metrics
- **Enrollment Flow Completion**: ≥85% completion rate from start to handoff
- **Form Abandonment**: ≤15% abandonment rate on contact forms
- **Mobile Usability**: ≥4.5/5 average mobile usability score
- **Page Engagement**: Average time on site ≥2 minutes
- **Bounce Rate**: ≤40% bounce rate on landing pages

### Brand Consistency Validation
- **Logo Treatment**: Consistent sizing, padding, and shadow effects across all pages
- **Voice and Tone**: 100% adherence to warm, nurturing, professional messaging
- **Visual Hierarchy**: Clear information hierarchy supporting user goals
- **Emotional Impact**: User testing confirms "warm and nurturing" first impression

### Technical Validation Criteria
- **Code Quality**: ESLint passing with 0 errors, 0 warnings
- **Type Safety**: 100% TypeScript coverage with strict mode enabled
- **Error Handling**: Comprehensive error boundaries and graceful degradation
- **Security**: No exposed sensitive data, proper input sanitization
- **SEO Readiness**: Proper meta tags, semantic HTML, structured data

### Comparison and Testing Standards
- **A/B Testing Framework**: Ability to test design variations for optimization
- **User Testing Protocol**: Minimum 5 user sessions per major page/flow
- **Automated Testing**: 100% critical path coverage with automated tests
- **Visual Regression Testing**: Automated screenshot comparison for design consistency
- **Performance Monitoring**: Continuous monitoring with alerting for threshold breaches

### Success Validation Timeline
- **Week 1 Checkpoint**: Design system components pass Figma adherence validation
- **Week 2 Checkpoint**: Performance and accessibility targets met
- **Pre-Launch**: All validation criteria pass with documented evidence
- **Post-Launch**: Monthly validation reports with improvement recommendations

### Validation Tools and Methods
- **Design Comparison**: Figma overlay comparison, pixel-perfect validation tools
- **Performance Testing**: Lighthouse CI, WebPageTest, Core Web Vitals monitoring
- **Accessibility Testing**: axe-core, WAVE, manual screen reader testing
- **Cross-Browser Testing**: BrowserStack, manual testing across device matrix
- **User Testing**: Moderated sessions, unmoderated task completion studies

## Implementation Phases

### Phase 1: Foundation (Week 1)
- Implement page structure and navigation
- Build configurator with mock data
- Establish design system components
- Implement seasonal background logic

### Phase 2: Integration (Week 2)
- Connect to live API endpoints
- Add real teacher content and photos
- Performance optimization and testing
- Accessibility audit and fixes

### Phase 3: Launch Preparation
- Final Figma design adherence review
- Cross-browser testing
- Performance validation
- Accessibility compliance verification

## Risk Mitigation

### Design Risks
- **Figma Adherence**: Regular design reviews against Figma source
- **Performance Impact**: Optimize seasonal backgrounds and character assets
- **Accessibility Compliance**: Continuous testing throughout development
- **Mobile Experience**: Prioritize mobile-first responsive design

### Technical Risks
- **API Integration**: Mock-first development with swappable data layer
- **Performance Targets**: Early and continuous performance monitoring
- **Browser Compatibility**: Test across target browser matrix
- **Seasonal Logic**: Robust date-based background selection

## Conclusion

This Design Brief establishes Cedar Heights Music Academy's website as a warm, nurturing digital community that converts visitors into enrolled students through a beautiful, accessible, and performant user experience. The combination of seasonal backgrounds, streamlined enrollment flow, and consistent emotional tone creates a unique and memorable experience that builds trust and drives enrollment.

The strict adherence to Figma designs, WCAG 2.1 AA accessibility standards, and aggressive performance targets ensures the site will serve all users effectively while achieving the business goal of 20% enrollment increase within 6 months.