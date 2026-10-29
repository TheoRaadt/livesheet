---
name: gui-concepts
description: Conceptual map of modern desktop-application UI/UX patterns (layout, navigation, typography, theming, feedback, accessibility) drawn from general, product-agnostic design guidance. Use when writing LiveSheet specs for look-and-feel, layout or interaction polish.
---
# Desktop-app UI/UX concepts (from general, public design guidance)

Use as a checklist of IDEAS, not a template to trace. Draw on general design-system
documentation (e.g. publicly published design guidelines, platform HIGs, open-source
design systems) and genuinely cross-app conventions, never on a single competitor's
literal layout, icon set, colour palette, chrome arrangement or widget-for-widget
structure. If a pattern is distinctive to one product rather than common across many,
leave it out — see ip-cleanroom.

- Layout: clear primary canvas vs. chrome; collapsible/dockable side panels; a slim
  top toolbar for the most-used actions; status bar for state (units, zoom, mode).
- Visual hierarchy: consistent spacing scale, limited type scale (2-3 sizes), one
  accent colour used sparingly, clear focus/selection states.
- Theming: light and dark variants from the same token set; respect OS-level
  appearance setting by default.
- Navigation: breadcrumbs or tabs for multi-document/multi-sheet state; command
  palette or searchable menu for discoverability; consistent keyboard shortcuts
  shown next to menu items.
- Feedback: inline validation near the thing being edited, not only in a far-away
  log; non-blocking toasts for transient status; progress indication for anything
  over ~300ms.
- Empty/first-run states: a blank canvas explains itself (placeholder text or a
  short inline hint) instead of looking broken.
- Accessibility: resizable text, sufficient contrast, full keyboard navigation,
  screen-reader-friendly labels on custom widgets.
- Consistency: one way to do a given action, reachable the same way everywhere
  (menu, toolbar, shortcut all trigger the same command).

Sources: general, publicly published UI/UX and design-system guidance (platform
human-interface guidelines, open design systems, general UX-heuristics writing),
never a specific competitor's screenshots, marketing pages, or installed app.
Do not reproduce any single product's distinctive chrome layout, icon design,
colour palette, or widget arrangement; translate only the generic idea into
LiveSheet's own visual language. Check every resulting spec against
docs/IP-POLICY.md (see ip-cleanroom).
