---
name: Civic Transparency Framework
colors:
  surface: '#fbf8fa'
  surface-dim: '#dcd9db'
  surface-bright: '#fbf8fa'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f5f3f4'
  surface-container: '#f0edef'
  surface-container-high: '#eae7e9'
  surface-container-highest: '#e4e2e3'
  on-surface: '#1b1b1d'
  on-surface-variant: '#45474c'
  inverse-surface: '#303032'
  inverse-on-surface: '#f3f0f2'
  outline: '#75777d'
  outline-variant: '#c5c6cd'
  surface-tint: '#1f5bb8'
  primary: '#001334'
  on-primary: '#ffffff'
  primary-container: '#00265b'
  on-primary-container: '#5c8eee'
  inverse-primary: '#aec6ff'
  secondary: '#006a61'
  on-secondary: '#ffffff'
  secondary-container: '#86f2e4'
  on-secondary-container: '#006f66'
  tertiary: '#111516'
  on-tertiary: '#ffffff'
  tertiary-container: '#26292b'
  on-tertiary-container: '#8d9092'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d8e2ff'
  primary-fixed-dim: '#aec6ff'
  on-primary-fixed: '#001a42'
  on-primary-fixed-variant: '#004396'
  secondary-fixed: '#89f5e7'
  secondary-fixed-dim: '#6bd8cb'
  on-secondary-fixed: '#00201d'
  on-secondary-fixed-variant: '#005049'
  tertiary-fixed: '#e0e3e5'
  tertiary-fixed-dim: '#c4c7c9'
  on-tertiary-fixed: '#191c1e'
  on-tertiary-fixed-variant: '#444749'
  background: '#fbf8fa'
  on-background: '#1b1b1d'
  surface-variant: '#e4e2e3'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-md-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  title-sm:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 28px
  body-base:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-caps:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 4px
  gap-xs: 0.5rem
  gap-sm: 1rem
  gap-md: 1.5rem
  container-margin: 2rem
  desktop-max-width: 1440px
---

## Brand & Style

This design system is built on the principles of **Institutional Transparency** and **Functional Clarity**. The brand personality is authoritative yet accessible, designed to bridge the gap between bureaucratic efficiency and citizen-centric service. 

The aesthetic follows a **Corporate / Modern** direction with a focus on high-information density without visual clutter. It utilizes a structured grid, generous white space, and a refined color palette to evoke a sense of calm, order, and reliability. The visual language avoids decorative flourishes, ensuring that every element serves a functional purpose in the redressal workflow.

## Colors

The palette is engineered for trust and systematic navigation. 

*   **Primary (#2660BD):** A professional Blue used for institutional headers, primary navigation, and high-level typography to establish a modern sense of authority.
*   **Secondary (#0D9488):** A bright Teal used exclusively for primary actions (buttons, submission anchors) to signify progress and resolution.
*   **Neutral (#F8FAFC):** An off-white background gray that reduces eye strain during long-form data entry.
*   **Status Tones:** Urgent issues use a high-contrast Red (#BA1A1A); Moderate issues use Amber for visibility without panic; Low-priority issues use Emerald to signal a "safe" or "received" state.

## Typography

The design system utilizes **Inter** exclusively for its exceptional legibility in UI contexts. 

- **Scale:** A tight modular scale ensures hierarchical clarity in complex dashboards. 
- **Accessibility:** Minimum body size is set to 16px for general content and 14px for supporting metadata.
- **Labels:** Use `label-caps` for table headers and form section titles to distinguish metadata from user input.
- **Contrast:** Ensure all text-on-background combinations meet WCAG AA standards.

## Layout & Spacing

This design system employs a **Fluid-Fixed Hybrid Grid**. 
- **Dashboard Views:** Use a 12-column grid with a 24px gutter. The sidebar is fixed at 280px, while the main content area is fluid.
- **Content Width:** Long-form submission forms are constrained to a maximum width of 720px (centered) to maintain readability.
- **Spacing Rhythm:** Based on a 4px baseline. All margins and paddings must be multiples of 4 (e.g., 8, 16, 24, 32).
- **Responsive Behavior:** On mobile (<640px), margins reduce to 16px and the 12-column grid collapses into a single-column stack.

## Elevation & Depth

The design system uses **Low-contrast outlines** combined with **Tonal layers** to create depth without the visual noise of heavy shadows.

- **Level 0 (Floor):** Background color (#F8FAFC).
- **Level 1 (Cards/Sections):** White background with a 1px border.
- **Level 2 (Popovers/Modals):** White background with a subtle, diffused ambient shadow (0px 10px 15px -3px rgba(0,0,0,0.05)).
- **Map Containers:** Leaflet containers should use a 1px inset border to appear "embedded" into the page surface.

## Shapes

The shape language is **Soft (0.25rem)** to maintain a professional, slightly rigid institutional feel while avoiding the harshness of sharp corners.

- **Standard Elements:** Input fields, buttons, and alert banners use `rounded` (4px).
- **Large Containers:** Dashboard cards and map containers use `rounded-lg` (8px).
- **Priority Indicators:** Status chips and badges use `rounded-full` (pill-shaped) to distinguish them from interactive buttons.

## Components

### Buttons & Inputs
- **Primary Action:** Solid background (#0D9488), white text, 4px radius. 
- **Secondary Action:** Ghost style, 1px border, primary text color (#2660BD).
- **Inputs:** High-contrast borders that darken to Primary (#2660BD) on focus. Ensure focus rings are high-visibility (Teal).

### Privacy-First UI
- **Sensitive Data Masking:** Use a "dotted-mask" pattern for PII (Personally Identifiable Information). Elements should be blurred by default (blur: 4px) with a "Click to Reveal" icon-button (Eye icon).
- **Data States:** Use a distinct mono-spaced font for masked IDs to signify they are system-generated.

### Status Badges
- **Urgent:** Red background (10% opacity) with solid Red text.
- **Moderate:** Amber background (10% opacity) with solid Amber text.
- **Low:** Emerald background (10% opacity) with solid Emerald text.

### Leaflet Map Containers
- Map UI controls (Zoom, Layers) must be restyled to match the 4px roundedness.
- Use custom map markers in the Primary Blue (#2660BD) with color-coded pips inside the marker to indicate complaint priority.

### Progress Stepper
- Used for redressal tracking. Use a vertical orientation on mobile and horizontal on desktop. Completed steps use Teal, active steps use Primary Blue, and pending steps use neutral grays.