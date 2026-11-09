# 025 Larger Standard toolbar buttons (icon + label, size-matched to the tab strip, HiDPI, narrow-width overflow)

Source inspiration (concept only, nothing copied):
- General, long-established desktop toolbar practice: a toolbar button is an icon with a short text
  label beside it when there is room, icon-only with a tooltip when there is not, and a trailing
  overflow ("more") menu as the last resort. Generic toolkit behaviour (the stock Qt toolbar
  already provides the overflow menu), not a feature of any one product.
- General, public usability guidance on pointing-target size (larger targets are faster and less
  error-prone; common platform guidance puts comfortable desktop click targets at roughly 28-36
  logical pixels) and on resolution independence (draw icons as vectors, render at the screen's
  device-pixel ratio). Guideline writing only; no text reproduced.
- Project's own .claude/skills/gui-concepts/SKILL.md: "consistent spacing scale", "resizable text",
  "screen-reader-friendly labels", "one way to do a given action ... menu, toolbar, shortcut all
  trigger the same command", "light and dark variants from the same token set".
- Own prior specs: 007-main-window.md (Standard toolbar reuses the menu QActions), 022 (tab strip
  metrics). No vendor software, help text, screenshot or icon set was consulted.

Scope: look and size of the existing Standard toolbar only. Same five commands (New, Open, Save,
Export PDF, Recalculate), same order and separators, same QAction objects, same shortcuts, same
movable-but-not-floatable behaviour, same saved-state keys. No engine or .lsheet change.
Size: one phase, about 1 day (new small icon module + toolbar styling + width-driven style switch).

## Current state (read from livesheet/gui/main_window.py ~L239-253, sidepanel.py, tabstrip.py)
- The toolbar is a stock QToolBar holding five QActions with text only: no icons exist anywhere in
  the project (there are no icon assets), no icon size, no style or padding set, so the buttons are
  the platform's default small text buttons.
- Tab strip buttons (spec 022, tabstrip.py): height = bold font height + 12 px, width = text + 24 px.
- Button-band token buttons (sidepanel.py): QPushButton with 3 px vertical / 6 px horizontal padding
  and a 1 px border, i.e. font height + about 8 px.
- Result (Theo's observation): toolbar buttons are visibly the smallest, lowest-contrast clickable
  things in the chrome.

## User story
As a user I want the Standard toolbar buttons to be at least as large and as easy to hit as the tab
strip and the band's buttons, recognisable at a glance by an icon plus a short label, and still
usable (not clipped, not widening the window) when I shrink the window.

## Behaviour (own words)

### 1. Size rule (rule-based so it follows the system font)
Let `F` = the application font's line height (QFontMetrics.height()) and `T` = the tab strip
button height (bold line height + 12, the value spec 022 already computes).
- Icon edge = 20 logical px at the default font; scale as `round(20 * F / 15)` snapped to an even
  number, minimum 20, maximum 32. (Resizable text therefore grows the icons too.)
- Button height = `max(32, T + 4)` logical px. Typical result with a 13-14 pt system font: 32-34 px,
  i.e. clearly taller than a band button (about F + 8) and 4 px taller than a tab, so the toolbar
  reads as the top-level row without being oversized.
- Horizontal padding 10 px each side; gap between icon and label 6 px; 4 px gap between buttons;
  separators keep the platform default plus 4 px.
- Corner radius and border: reuse the band button treatment (rounded 4 px, hover/pressed/checked
  states drawn by the current style or by a stylesheet using palette roles only, no hard-coded
  colours) so light and dark appearance both work.
- Label font = application font, regular weight, same size as the tab strip. No third font size.

### 2. Layout: text beside icon
Wide layout uses icon on the left, label on the right ("text beside icon"). Rationale: it keeps the
toolbar one row high (labels under icons would make it about 52 px tall and take vertical space
from the canvas). Labels, exactly as the action texts without the mnemonic ampersand and without
the trailing ellipsis: `New`, `Open`, `Save`, `Export PDF`, `Recalculate`.

### 3. Icons (own, generic, vector-drawn)
No icon files are shipped or copied. A small module (suggested livesheet/gui/icons.py) draws five
monochrome glyphs with QPainter paths onto a QIcon, in own geometry, generic metaphors only:
- New: a blank page with a folded top-right corner.
- Open: an open-folder outline (tab on the upper left, slanted front edge).
- Save: a square with a notched top corner and a small inset label rectangle (the near-universal
  "stored on disk" metaphor; draw it from simple rectangles, no tracing of any existing set).
- Export PDF: a page with a short arrow pointing out of its right edge.
- Recalculate: an open circular arc with an arrowhead (the near-universal "refresh" metaphor).
Rules: stroke 1.5-2 px at 20 px edge (scale with edge), round caps, no fills except the Save label;
colour taken from the palette `ButtonText` role (and the Disabled colour group for the disabled mode),
so one drawing serves light, dark and disabled states. Render on demand for the requested size and
the screen's device-pixel ratio (QIconEngine, or a QIcon fed with pixmaps at ratios 1, 1.5, 2, 3);
re-render when the palette or screen changes. No raster assets, so nothing blurry at 125/150/200 %.
The five QActions get these icons. Menu items must NOT show them (`setIconVisibleInMenu(False)`),
so the File and Calculate menus look exactly as today on every platform.

### 4. Narrow windows: three tiers, no clipping, no forced width
The toolbar's natural width at the default font is about 520 px (icon+label) or about 190 px
(icon only). The window's own minimum width is set by the widest tab and the 400 px canvas minimum,
and the toolbar must never raise it.
1. Enough room for icon+label for all five: style = TextBesideIcon.
2. Not enough: switch the toolbar to IconOnly (same button size, label hidden). Every button's
   tooltip is `<Label> (<shortcut as shown by the platform>)`, e.g. `Save (Ctrl+S)`, which makes
   the labels discoverable; the accessible name stays the full label in both styles.
3. Still not enough (rare, very narrow): keep IconOnly and let Qt's built-in toolbar extension
   button ("more" chevron) appear at the right end; its menu lists the hidden actions with their
   text. They remain the same QActions.
Switching rule: compute the width of the TextBesideIcon layout (sum of button size hints plus
separators and margins) once per resize/font change; use IconOnly while the toolbar's available
width is less than that sum. Use a 24 px hysteresis band (switch to IconOnly below sum, back to
TextBesideIcon only above sum + 24) so the style does not flicker while dragging the window edge.
The chosen style is derived, never saved. If the toolbar is docked to a left/right edge (still
allowed by the existing movable setting), use IconOnly always and stack vertically.

### 5. Consistency and other rules
- Keyboard focus: the toolbar buttons keep Qt's default focus handling; a visible focus ring uses
  the same 2 px dotted WindowText ring the tab strip uses.
- Disabled actions (none today) render with the disabled palette group.
- The toolbar keeps `setMovable(True)`, `setFloatable(False)`, its object name `standard-toolbar`
  and the View > Standard Toolbar toggle; saved layouts stay valid.
- Status tips are unchanged.

## Syntax proposal
None (GUI chrome only).

## Acceptance criteria
Use QT_QPA_PLATFORM=offscreen, default test font, window.show(); numbers below are logical px.
1. All five toolbar actions have a non-null icon; `standard_toolbar.iconSize()` is 20x20 at the
   default font and 24x24 after the application font's height is increased to about 19 px.
2. For each toolbar button `sizeHint().height() >= 32` and `>= tab_strip_button_height + 4`.
   Each toolbar button's height is greater than the tallest band token button's `sizeHint().height()`.
3. At window width 1000: `toolButtonStyle() == TextBesideIcon`; every button is fully inside the
   toolbar rect; the extension button is not visible.
4. At window width 480 (below the ~520 sum): style is `IconOnly`, all five buttons are visible,
   each button `toolTip()` equals `"<Label> (<shortcut>)"` for those with shortcuts (`Export PDF
   (Ctrl+Shift+E)`, `Recalculate (F9)`), accessibleName is the plain label.
5. Resizing 1000 -> 540 -> 500 -> 540 -> 1000 never changes style more than once per crossing
   (hysteresis): 540 stays IconOnly on the way back up until >= sum + 24.
6. At the smallest width the window allows, no button overlaps another, the window's minimumWidth
   is the same value as before this change (toolbar does not raise it), and the extension menu
   (if shown) contains the hidden actions' texts.
7. Clicking a toolbar button and triggering the menu action call the same QAction (object identity
   of `toolbar.actions()` entries equals `action_new` ... `action_recalculate`, unchanged).
8. `action.isIconVisibleInMenu()` is False for all five.
9. Icon pixmap rendered at devicePixelRatio 2 for edge 20 has size 40x40 and is not all
   transparent; rendering the Dark palette versus Light palette gives different glyph colours
   (compare the dominant opaque pixel colour).
10. Existing tests for toolbar object name / movable / non-floatable / saved-state restore still pass.

## Edge cases
- Font change at run time: icon edge, button height and the style threshold are recomputed.
- Translations or a longer label ("Export PDF" becoming longer): the threshold is computed from
  real size hints, not constants.
- Screen move between a 1x and a 2x monitor: icons re-render for the new ratio.
- Toolbar hidden via View menu and shown again: style recomputed on show.

## IP check
Pass. Generic toolbar sizing/overflow practice from toolkit conventions and public pointing-target
guidance; icons are own simple vector drawings of near-universal metaphors (page, folder, disk,
arrow, refresh) with no third-party glyph set, no file copied and nothing traced. Not tied to the
engineering-calculation product category. Open IP question: none; the manager may still want to
glance at the Save glyph to be sure it is a plain geometric drawing and not a recognisable
reproduction of a specific icon set.

## Fits current architecture?
GUI only: livesheet/gui/main_window.py (toolbar block), new livesheet/gui/icons.py. No engine
import of PySide6, no .lsheet change.
