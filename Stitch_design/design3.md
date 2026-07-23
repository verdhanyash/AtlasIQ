---
name: Liquid Glass Industrial
colors:
  surface: '#141313'
  surface-dim: '#141313'
  surface-bright: '#3a3939'
  surface-container-lowest: '#0e0e0e'
  surface-container-low: '#1c1b1b'
  surface-container: '#201f1f'
  surface-container-high: '#2a2a2a'
  surface-container-highest: '#353434'
  on-surface: '#e5e2e1'
  on-surface-variant: '#c4c7c8'
  inverse-surface: '#e5e2e1'
  inverse-on-surface: '#313030'
  outline: '#8e9192'
  outline-variant: '#444748'
  surface-tint: '#c6c6c7'
  primary: '#ffffff'
  on-primary: '#2f3131'
  primary-container: '#e2e2e2'
  on-primary-container: '#636565'
  inverse-primary: '#5d5f5f'
  secondary: '#c6c6cf'
  on-secondary: '#2f3037'
  secondary-container: '#45464e'
  on-secondary-container: '#b4b4bd'
  tertiary: '#ffffff'
  on-tertiary: '#2f3131'
  tertiary-container: '#e2e2e2'
  on-tertiary-container: '#636565'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#e2e2e2'
  primary-fixed-dim: '#c6c6c7'
  on-primary-fixed: '#1a1c1c'
  on-primary-fixed-variant: '#454747'
  secondary-fixed: '#e2e1eb'
  secondary-fixed-dim: '#c6c6cf'
  on-secondary-fixed: '#1a1b22'
  on-secondary-fixed-variant: '#45464e'
  tertiary-fixed: '#e2e2e2'
  tertiary-fixed-dim: '#c6c6c7'
  on-tertiary-fixed: '#1a1c1c'
  on-tertiary-fixed-variant: '#454747'
  background: '#141313'
  on-background: '#e5e2e1'
  surface-variant: '#353434'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '600'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.2'
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '500'
    lineHeight: '1.3'
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
  label-md:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: '1.4'
    letterSpacing: 0.02em
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: '1.4'
    letterSpacing: 0.04em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  container-max: 1440px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 40px
---

## Brand & Style

The design system is engineered for **AtlasIQ**, an enterprise RAG platform. The aesthetic is "Liquid Glass"—a fusion of high-end minimalism and industrial precision. It prioritizes clarity, data integrity, and high-trust interactions through a monochrome palette that emphasizes depth over color.

The emotional response should be one of "Calculated Calm." By removing saturated branding, the focus shifts entirely to the information architecture. The design utilizes deep layering, background blurs, and subtle luminosity to create a sophisticated, high-performance environment suitable for mission-critical data analysis.

## Colors

This design system employs a strictly monochrome foundation to maintain an industrial, authoritative tone. Functional colors are used only as "status signals" and are desaturated to integrate seamlessly with the glass surfaces.

- **Base:** The background is a deep, near-black (#0A0A0A), providing the necessary contrast for the glass layers.
- **Monochrome Scale:** Pure white is reserved for high-priority text and active states. Silver and Zinc tones (A1A1AA) define secondary information.
- **Functional Accents:** Soft, desaturated tints of green, amber, and red are used exclusively for semantic feedback (e.g., confidence scores, system health, or error states).

## Typography

The typography strategy balances modern interface clarity with technical precision. 

- **Inter** is the primary typeface, chosen for its neutral, highly legible characteristic in complex UI layouts. It handles the bulk of the platform's communicative needs.
- **JetBrains Mono** is utilized for "Machine Data"—including citations, metadata, confidence scores, and code snippets. Its monospaced nature signals to the user that they are looking at raw or system-generated evidence.

Text contrast is strictly managed: 
- **Primary:** White (90-100% opacity)
- **Secondary:** Silver (60-70% opacity)
- **Disabled/Muted:** Zinc (30-40% opacity)

## Layout & Spacing

The layout follows a strict **4px baseline grid** to reinforce the industrial nature of the product. 

- **Grid:** A 12-column fluid grid for desktop with 24px gutters.
- **Margins:** Generous outer margins (40px on desktop) ensure the glass containers have room to "breathe" against the dark background.
- **Sectioning:** Content is grouped into high-context clusters. Use 64px+ spacing between major functional blocks to maintain the minimalist ethos.
- **Responsive:** On mobile, the grid collapses to 4 columns with 16px margins; typography scales down specifically for headlines to maintain readability without excessive wrapping.

## Elevation & Depth

Depth in the design system is defined by "Liquid Glass" layers. Instead of traditional shadows, elevation is communicated through background opacity, blur intensity, and border thickness.

- **Level 1 (Surface):** Used for persistent sidebars or background groupings. 3% white background, 24px backdrop blur, 8% white border.
- **Level 2 (Mid-ground):** The standard for cards and content containers. 5% white background, 32px backdrop blur, 10% white border.
- **Level 3 (Foreground):** Used for modals, popovers, and floating tooltips. 8% white background, 40px backdrop blur, 12% white border.

**Active States:** When an element is focused or active, apply a soft white ambient glow. This is a 20px spread, low-opacity (#FFFFFF at 10-15%) outer glow that replaces the need for high-contrast color changes.

## Shapes

The shape language is "Geometric-Soft." 

- **Cards/Containers:** Use a consistent 16px radius. This softens the industrial edge, making the dense data feel more approachable.
- **Inputs/Buttons:** Use an 8px radius to signify interactivity.
- **Status Indicators:** Use 4px or fully rounded (pill) shapes depending on the density of the information.
- **Borders:** All borders on glass elements must be inner-aligned to maintain sharp outer edges.

## Components

### Buttons
- **Primary:** Solid white text on Level 2 glass background. On hover, apply the 20px white ambient glow.
- **Secondary:** Ghost style with a 1px 15% white border.
- **Tertiary:** Text-only (Inter Medium) with JetBrains Mono icons.

### Input Fields
- **Style:** Level 1 glass base with an 8px radius. 
- **Focus:** Border opacity increases to 40% white with a subtle internal 2px glow. Label shifts to JetBrains Mono (label-sm).

### Cards
- Always utilize Level 2 glass. 
- Header areas within cards should be separated by a 1px 10% white horizontal line.

### Chips/Tags (Citations)
- Use **JetBrains Mono**.
- Level 1 glass background with a pill-shaped radius. 
- Prefix with a numerical index for RAG sourcing.

### Lists
- Hovering over a list item should trigger a Level 1 glass highlight (3% white bg) with 0px radius to maintain a continuous vertical flow, or 8px if items are visually separated.

### Feedback Elements
- **Success/Warning/Error:** Do not fill the background with color. Use a 2px vertical "accent bar" on the left edge of the glass card using the functional accent colors, and tint the icon/primary text of the message slightly with that same color.