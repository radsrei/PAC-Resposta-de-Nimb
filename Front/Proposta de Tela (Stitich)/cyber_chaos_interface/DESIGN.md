---
name: Cyber-Chaos Interface
colors:
  surface: '#13131a'
  surface-dim: '#13131a'
  surface-bright: '#393840'
  surface-container-lowest: '#0e0e15'
  surface-container-low: '#1b1b22'
  surface-container: '#1f1f26'
  surface-container-high: '#2a2931'
  surface-container-highest: '#34343c'
  on-surface: '#e4e1ec'
  on-surface-variant: '#cec2d7'
  inverse-surface: '#e4e1ec'
  inverse-on-surface: '#303038'
  outline: '#978da0'
  outline-variant: '#4b4454'
  surface-tint: '#d8b9ff'
  primary: '#d8b9ff'
  on-primary: '#450086'
  primary-container: '#ae71ff'
  on-primary-container: '#3c0076'
  inverse-primary: '#7d2dd9'
  secondary: '#43e090'
  on-secondary: '#00391f'
  secondary-container: '#00c175'
  on-secondary-container: '#004728'
  tertiary: '#ffb95d'
  on-tertiary: '#462a00'
  tertiary-container: '#c68218'
  on-tertiary-container: '#3d2400'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#eedcff'
  primary-fixed-dim: '#d8b9ff'
  on-primary-fixed: '#290055'
  on-primary-fixed-variant: '#6300bb'
  secondary-fixed: '#66feaa'
  secondary-fixed-dim: '#43e090'
  on-secondary-fixed: '#002110'
  on-secondary-fixed-variant: '#00522f'
  tertiary-fixed: '#ffddb7'
  tertiary-fixed-dim: '#ffb95d'
  on-tertiary-fixed: '#2a1700'
  on-tertiary-fixed-variant: '#653e00'
  background: '#13131a'
  on-background: '#e4e1ec'
  surface-variant: '#34343c'
  neon-purple-dim: rgba(162, 89, 255, 0.2)
  neon-green-dim: rgba(57, 217, 138, 0.25)
  deep-surface: '#13131F'
  input-base: '#1A1A2E'
  glitch-white: '#F0EEF8'
typography:
  headline-xl:
    fontFamily: Space Grotesk
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Space Grotesk
    fontSize: 32px
    fontWeight: '700'
    lineHeight: '1.2'
  headline-sm:
    fontFamily: Space Grotesk
    fontSize: 20px
    fontWeight: '600'
    lineHeight: '1.4'
  body-lg:
    fontFamily: Space Grotesk
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.65'
  body-md:
    fontFamily: Space Grotesk
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.6'
  code-md:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '400'
    lineHeight: '1.5'
  label-caps:
    fontFamily: Space Grotesk
    fontSize: 10px
    fontWeight: '600'
    lineHeight: '1'
    letterSpacing: 0.1em
  metadata:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '400'
    lineHeight: '1'
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  gutter: 20px
  margin-mobile: 16px
  margin-desktop: 28px
  container-max: 1280px
---

## Brand & Style

The design system is built on a narrative of **Controlled Chaos** and **High-Tech Absurdisim**. It targets a developer-centric, tech-native audience that values both precision and expressive edge. The personality is unapologetically bold, energetic, and slightly subversive.

The aesthetic blends **Modern Minimalism** with **Cyberpunk/Glitch** elements. It utilizes a deep-space dark mode as a canvas for high-chroma neon accents. Visual interest is generated through:
- **Digital Distortions:** Subtle glitch effects on hover states and decorative UI elements.
- **Atmospheric Depth:** Using vibrant glows and backdrop blurs to simulate a high-tech terminal.
- **Technical Rigor:** Balancing the "caotic" visuals with ultra-clean, monospaced typography and structured layouts.

## Colors

The palette is anchored by a **Deep Space Black** (`#0D0D14`) which provides the necessary contrast for the neon accents. 

- **Primary Purple:** Used for brand identity, AI-driven components, and primary interactive states. It represents the "mystical" and intelligent side of the interface.
- **Secondary Neon Green:** Used for user actions, success states, and status indicators. It provides a sharp, energetic counterpoint to the purple.
- **Glitch White:** A slightly tinted off-white used for primary text to reduce eye strain against the deep background while maintaining high legibility.
- **Atmospheric Gradients:** Always use a combination of Primary and Secondary neons with high transparency for background glows to create environmental depth.

## Typography

This design system uses a technical pairing to reinforce the "pro-tool" aesthetic. 

**Space Grotesk** is the primary workhorse, used for headings and body copy. Its geometric nature feels modern and accessible. **JetBrains Mono** is reserved for metadata, system labels, keyboard shortcuts, and code snippets, injecting a "terminal" feel into the UI.

For mobile layouts, scale down `headline-xl` to `32px` and `headline-lg` to `24px` to ensure the dramatic typography doesn't overwhelm the smaller viewport.

## Layout & Spacing

The layout is built on a **Fluid Grid** system with a technical 4px baseline unit. 

- **Desktop:** A 12-column grid with a 220px fixed sidebar. Content is centered within a 1280px container.
- **Mobile:** The sidebar collapses into a hidden drawer. Margins reduce to 16px. Elements like message bubbles and cards transition to full-width to maximize screen real estate.
- **Rhythm:** Use `20px` (5 units) for primary component spacing to create a sense of airiness that balances the high-density color palette.

## Elevation & Depth

Hierarchy is achieved through **Tonal Layering** and **Luminous Depth**. 

Instead of traditional grey shadows, this system uses:
- **Outer Glows:** Primary buttons and active containers use a soft `8px` blur of their own accent color at low opacity (8-10%).
- **Rim Lighting:** A subtle `1px` inner border (top-aligned) using `#FFFFFF` at 5% opacity to give surfaces a "glass edge."
- **Backdrop Blurs:** Fixed elements like the top navigation bar and floating input zones must use a `12px` blur with a 80% opaque background to maintain legibility over scrolling content.

## Shapes

The shape language is **Techno-Organic**, featuring generous rounding that contrasts with the "glitch" aesthetic.

- **Containers:** Main interface wrappers use a `20px` radius.
- **Interactive Elements:** Buttons and input fields use a `14px` radius to feel approachable.
- **Small Components:** Chips and status indicators use a fully rounded (pill) style to distinguish them from structural elements.

## Components

### Buttons
Primary buttons use a diagonal gradient from `--purple-500` to `--green-500`. On hover, apply a `1.02` scale and increase the outer glow intensity.

### Input Fields
Inputs are dark-surfaced (`--input-base`) with a subtle `--neon-purple-dim` border. Upon focus, the border brightens to full `--purple-400` with a soft purple ambient glow.

### Message Bubbles
AI responses should be styled with a subtle purple tint and a left-aligned accent border. User messages use a green border (`--neon-green-dim`) to clearly delineate roles.

### Suggestion Chips
Pill-shaped with `--text-muted` and a `1px` transparent border. On hover, the border becomes visible in `--purple-400` and the text shifts to white.

### Glitch Decorative Elements
Use 2px high horizontal lines of Primary Purple and Secondary Green, offset by a few pixels, to create "scan-line" or "glitch" artifacts in empty states or sidebar headers.