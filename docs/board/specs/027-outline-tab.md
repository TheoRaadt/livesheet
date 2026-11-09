# 027 Outline tab: list the sheet's headings and jump to them

Source inspiration (concept only, nothing copied):
- General, widely shared document-navigation convention: a document map/outline lists the headings
  of a document in reading order, grouped by page or section, and activating an entry moves the
  view to it. Found in word processors, code editors, PDF viewers and note tools alike; generic.
- General usability heuristics (visibility of system state, flexibility for large documents,
  helpful empty states). Heuristics writing only.
- Own material: specs 007/011/022 (tab, band, FlowLayout, group headers), 021 (page breaks),
  the existing text-region bold toggle. No vendor software or help consulted.

Scope: GUI only. Fills the Outline tab. No engine change, no .lsheet change (a heading is
recognised from existing rich-text content, no new region field). Does not touch the Data tab.
Size: one phase, about 2 days.

## Feasibility (honest)
Feasible now without engine or file-format work, because text regions are stored as rich text (HTML
in the `text` field) in which bold is already available (Ctrl+B in a text region), the sheet knows
all regions and the page-break positions, and the view can centre on a point. What is NOT available
and therefore not promised: heading levels/nesting (no heading styles exist), an explicit
"Heading" region type (would need a .lsheet format addition and a Theo decision), numbering, and
folding. Those need a separate spec if wanted.

## User story
As a user with a long, multi-page sheet I want the Outline tab to list its headings, grouped by
page, so I can jump to a part of the sheet with one click instead of scrolling.

## Behaviour (own words)

### What counts as a heading
A text region is a heading when its first paragraph is non-empty and every character of it is bold.
The entry text is that first paragraph's plain text, whitespace-collapsed, elided with an ellipsis
beyond 32 characters (full text in the tooltip). Math, plot and component regions never appear.
No levels: one flat list.

### Order and grouping
Entries are in reading order: page by page (pages are bounded by the sheet's page breaks, spec 021),
and within a page top to bottom, then left to right. A small grey page header ("Page 1", "Page 2",
...) starts each page that has at least one heading, using the same group-header style and
new-row rule as the Elements tab. A sheet without page breaks shows a single page and omits the
header.

### Presentation (reuses the band mechanism)
Each entry is a flat button in the band's FlowLayout, same style as the token buttons, label =
the elided heading text. Entries wrap in rows; the band's existing height rules and inner scrolling
apply. Clicking an entry: selects that region, scrolls the canvas so the region sits near the top of
the view (without changing zoom), and leaves keyboard focus where it was (like all band buttons).
Tooltip: full heading text and its page. Accessible name = full heading text.

### Empty state
No headings: the band shows one grey message instead of buttons: "No headings yet. Make the first
line of a text region bold (Ctrl+B) to list it here." (replaces the old placeholder text).

### Refresh
The list is rebuilt when (a) the Outline tab becomes the selected tab, (b) the sheet is loaded or
cleared, and (c) while the tab is selected, after region add/delete/move, text edits and page-break
changes, debounced by about 300 ms. When another tab is selected nothing is recomputed (no cost).
Uses the sheet's existing content-changed notifications; the developer adds a thin signal only if one
is missing.

### Not included
Heading levels/indent, a heading style or Insert > Heading command, numbering, collapse/expand,
drag-to-reorder, searching, outline in PDF export.

## Syntax proposal
None.

## Acceptance criteria
1. Sheet with three text regions: "Intro" (all bold, y=40), "Some prose" (not bold, y=120),
   "Results" (bold only for the first word "Re", y=200), and one math region: Outline shows exactly
   one entry, "Intro". Making all of "Results" bold and refreshing shows two entries in order
   Intro, Results.
2. Order: headings A (page 1, y=300), B (page 1, y=100), C (page 2 after a page break at y=500)
   list as B, A under "Page 1" then C under "Page 2". With no page break there is no page header.
3. A heading of 50 characters shows a label of 32 characters ending in an ellipsis; tooltip has all
   50.
4. Clicking an entry sets that region selected, and the view's visible rectangle contains the region
   with its top inside the upper quarter of the view; `view.zoom()` is unchanged; the editing focus
   (if a region was being edited) is unchanged.
5. Empty sheet or no bold-first-paragraph regions: the band contains the message text above and no
   entry buttons.
6. Editing a heading's text while the Outline tab is selected updates the label within 500 ms
   (processEvents after the debounce); while another tab is selected, no rebuild occurs (count calls
   to the builder).
7. Loading a saved .lsheet containing bold text regions lists them after load; saving and reopening
   changes nothing in the file (no format change; saved bytes equal pre-change output).
8. Tab order, TAB_ORDER and the other nine tabs are untouched; `OUTLINE_PLACEHOLDER` text is
   replaced by the empty-state message; tests asserting the old placeholder are updated.

## Edge cases
- Very many headings (hundreds): rebuild stays under about 100 ms for 200 regions; the band scrolls.
- Duplicate heading texts: both listed (buttons are distinguished by position/page).
- Heading region deleted while the list shows it: the next refresh removes it; a click on a stale
  entry is a no-op, not an exception.
- Text region whose HTML is malformed/legacy: treated as non-heading, no exception.
- Heading in the first paragraph only partly bold: not a heading (stated in the empty-state hint).

## IP check
Pass. A document outline / navigation list is a generic feature of many document tools and not tied
to the engineering-calculation product category; implemented with ordinary toolkit buttons in the
existing band, not as a bespoke on-canvas interaction. Heading detection by bold is LiveSheet's own
convention. Open IP question: none.

## Fits current architecture?
GUI only: livesheet/gui/sidepanel.py (Outline page builder replacing the placeholder),
a small read-only helper on the worksheet (list headings with page index and position), and a call
into the existing view-centre/scroll API. No engine or document.py change.

## Open questions for Theo
See the manager report: explicit Heading type vs bold-first-line convention; heading levels.
