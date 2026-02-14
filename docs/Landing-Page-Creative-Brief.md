# SimplyNarrated Landing Page Creative Brief

## 1) Objective

Create a branded landing experience that communicates what SimplyNarrated does in under 5 seconds:

- Convert documents into audiobooks locally
- Preserve privacy with local-first processing
- Offer a modern, high-trust, productivity-oriented product feel

Primary CTA: **Start Converting**
Secondary CTA: **Open Library**

## 2) Product Truth to Reflect (Do Not Overclaim)

- Input formats: TXT, MD, PDF
- Output: MP3 chapters
- Built-in features: progress tracking, bookmarks, library management, cover images
- Local operation with FastAPI + Kokoro voices

Avoid claims that are not currently shipped (for example WAV output or dialogue voice switching).

## 3) Visual Direction

### Brand Personality

- Professional, calm, premium productivity
- Dark mode native
- "Studio-grade narration" without looking like a consumer music app

### Color + Style Anchors

- Keep primary accent near `#137fec`
- Deep navy/charcoal base backgrounds
- Glass panels, subtle glows, clean typography (Inter-like geometry)
- High-contrast text, minimal visual clutter

### Hero Concept

A split hero:

- Left: bold headline + trust copy + CTA pair
- Right: custom illustration/composite showing:
  - document upload source (paper/file icon stack)
  - AI processing wave/node motif
  - audiobook/player output card with chapter progress

This visual should read as a pipeline: **Document → AI Voice → Audiobook**.

## 4) Asset List Needed

1. **Hero Illustration (Desktop)**
   - Ratio: 16:10 (recommended 1920x1200 source)
   - Use as main hero visual on landing page
2. **Hero Illustration (Mobile Crop-safe)**
   - Ratio: 4:5 (recommended 1200x1500 source)
   - Preserve key focal elements in center
3. **Brand Mark / Logo Lockup**
   - Horizontal lockup + icon-only mark
   - Transparent background PNG and SVG target
4. **Feature Icons (Custom set of 6)**
   - Upload, AI processing, voice, chapters, bookmarks, local privacy
5. **Social Preview Image (OpenGraph)**
   - 1200x630
   - Product name + core value proposition + hero motif

## 5) Copy Framework for New Landing

### Hero headline options

- "Turn Documents Into Audiobooks, Locally"
- "From Text to Voice in Minutes"
- "Your Private AI Audiobook Studio"

### Hero subcopy

"Upload TXT, Markdown, or PDF files and generate chapter-based MP3 audiobooks with natural AI voices—directly on your machine."

### Proof strip

- "Local-first processing"
- "Chapter-based output"
- "Built-in player + bookmarks"

## 6) Image Generator Prompts

Use these prompts directly in your image generator.

### A) Hero Image Prompt (No Screenshot)

"Design a premium SaaS hero illustration for a desktop web app called SimplyNarrated. Theme: convert documents into audiobooks locally with AI. Dark mode UI aesthetic with deep navy background, electric blue accent (#137fec), glassmorphism cards, subtle volumetric glow. Show a clean visual pipeline from left to right: document upload card (TXT/MD/PDF), AI processing node/wave visualization in the center, and audiobook player output card on the right with chapter progress and play button. Style: modern product illustration, high-detail but minimal, no characters, no photoreal humans, no copyrighted logos, no watermark, no lorem ipsum. Composition optimized for website hero area, 16:10, sharp, high contrast, professional enterprise feel."

### B) Hero Image Prompt (Screenshot-Guided)

"Using the attached screenshot as layout/style reference, redesign and elevate it into a polished branded hero graphic for SimplyNarrated. Keep dark mode, glass cards, and blue accent direction, but replace generic visuals with a strong document-to-audiobook story: upload panel, AI transformation motif, and final audiobook player card with chapters. Preserve visual hierarchy and spacing from the reference while improving typography polish, depth, lighting, and icon consistency. No stock-photo people, no copied third-party branding, no watermark, no placeholder text. Create a production-ready hero visual for a software landing page, 16:10."

### C) Logo / Brand Mark Prompt

"Create a clean modern logo for software product 'SimplyNarrated'. Concept: document pages transforming into audio waves or headphones. Minimal geometric mark, scalable, readable at small sizes, suitable for app header and favicon. Palette anchored on #137fec with optional neutral monochrome variants. Output style: flat vector logo, transparent background, no mockup scene, no 3D extrusion, no watermark."

### D) Feature Icon Set Prompt

"Create a cohesive set of 6 flat vector UI icons for a dark SaaS landing page. Concepts: upload document, AI processing, voice narration, chapter timeline, bookmark resume, local privacy/offline. Style: rounded geometric, minimal stroke detail, bright blue accent on dark background, consistent grid and stroke weight. No text labels, transparent background, production-ready."

### E) OpenGraph Social Card Prompt

"Design a 1200x630 social preview image for SimplyNarrated. Dark premium background, blue accent, bold title 'Turn Documents Into Audiobooks, Locally', subtitle 'Private AI narration for TXT, MD, and PDF'. Include simplified pipeline motif: document → AI wave → audiobook player. Modern, high contrast, clean whitespace, no watermark, no external logos."

## 7) Screenshot-Guided Workflow (Recommended)

1. Capture current landing view screenshot at desktop width.
2. Feed screenshot + Prompt B to keep layout DNA while upgrading aesthetics.
3. Generate 4 variants:
   - Variant 1: minimal
   - Variant 2: brighter blue accent
   - Variant 3: stronger data-flow motif
   - Variant 4: higher contrast typography
4. Pick the best base and run one refinement pass:
   - "Increase legibility of key focal card"
   - "Reduce visual noise by 15%"
   - "Keep center pipeline line clearer"
5. Export web-optimized assets (WebP/PNG) and keep source-resolution master.

## 8) Acceptance Criteria for Visual Assets

- At a glance (<5 seconds), user understands document-to-audio transformation
- Brand accent and style align with existing product UI
- No false feature implications
- Text remains readable in dark mode environments
- Hero works with both desktop and mobile crops
