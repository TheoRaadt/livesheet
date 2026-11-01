# Pages and page breaks

LiveSheet's canvas is one long scrolling sheet. You can split it into A4 pages by inserting page
breaks, the way you would in a word processor. Page breaks decide where printed sheets start, and
they also decide the order in which your regions are calculated.

## The order regions are calculated in

LiveSheet calculates your regions in this order:

1. **Page by page.** Everything on page 1 first, then everything on page 2, and so on. If you have
   not inserted any page breaks, the whole sheet is a single page.
2. **Within a page, left to right.** A region further to the left is calculated before one further
   to the right.
3. **Then top to bottom.** If two regions are in the same column (at about the same horizontal
   position), the higher one is calculated first.

A region can only use names defined by regions that are calculated before it. So a definition has
to be further left than where it is used, or in the same column higher up, or on an earlier page.

Positions are compared on the canvas grid (10 units), so tiny differences you cannot see do not
matter. If two regions sit at exactly the same grid position, the one you created first is
calculated first. That stays true after you save and reopen the file.

**Worked example.** Put `a := 2` at the left of the sheet and `a =` further right, on the same
line. The right-hand region shows `= 2`. Now drag `a =` to the left of the definition. It is now
calculated first, so it shows an error saying `a` is not defined. Move it back and the result
returns.

Sheets saved by an earlier version of LiveSheet are calculated in the new order when you open
them. If a sheet relied on the old order (top to bottom first), a region may now be calculated
before the definition it needs; move the definition to the left of, or into the same column
above, the region that uses it.

## Inserting a page break

1. Click on the canvas where you want the new page to begin. The red cross marks the spot.
2. Choose **Insert > Page Break**, or press **Ctrl+Return**.

LiveSheet starts a new A4 page at that point. Everything at or below the cross moves down so that it
begins at the top of the next A4 page. Everything above stays where it was. A full-width line
labelled with the page number ("Page 2", and so on) marks the new page. The cross moves to the top of
the new page, ready for your next region. Text, math, plot and component regions all move
together, and wires follow their components.

The status bar tells you what happened, for example `Page break inserted; moved 2 regions down by
720 units.`

**Worked example.** You have three regions at heights 100, 600 and 1300 on a fresh sheet, and
you click at height 500 and press Ctrl+Return. A4 pages are 1220 units tall, so the new page starts
at 1220. The region at 100 stays put. The regions at 600 and 1300 move down by 720 units, to 1320
and 2020. The first region is on page 1 and the other two are on page 2, so the first is
calculated first.

If the page you are on is already taller than one A4 sheet, the break goes at the next A4 sheet
boundary counted from the top of that page.

If the cross is at the top of the sheet, or exactly on an existing page break, LiveSheet refuses
and shows `This position is already the top of a page.` (see [Error messages](errors.md)). Click
lower down and try again.

You can insert as many breaks as you like. Breaks below the one you insert keep their
spacing and move down with the content.

## Deleting a page break

Click the page-break line to select it, then press **Delete** (or use **Edit > Delete Region**).
Only the line is removed. Content that was pushed down does not move back up, so there may be a
gap where the break used to be. The two pages merge, and the calculation order updates straight
away.

You cannot drag a page-break line. To move one, delete it and insert a new one. **Select All
Regions** does not select page-break lines.

## Moving regions across a break

Dragging a region across a page-break line is allowed and moves nothing else. The region simply
belongs to the page it is now on, judged by its top-left corner, and the calculation order follows.
A region that is tall enough to cross the line is drawn over it; it counts as belonging to the page
where its top-left corner is.

## Fold guides

LiveSheet never moves your content on its own. If a page is taller than one A4 sheet, dashed
guide lines appear every 1220 units from the top of that page (the top of the sheet, or its
previous page break). They show where Export PDF will continue onto an extra sheet. A sheet with
no page breaks gets the same guides from the top. The guides are only on screen and are not
printed.

## Export PDF

**File > Export PDF** (or the toolbar button) prints on A4 with 15 mm margins.

- **Each page break starts a new sheet.** The content of a page begins at the top of its own sheet,
  even if the previous page ended halfway down.
- **A very tall page** continues onto extra sheets, cut where the fold guides are.
- **A little shrinking.** When your sheet has page breaks, everything is scaled down by about
  0.4% so that a full 1220-unit page fits on one sheet. A sheet without page breaks is
  exported exactly as before.
- **No blank last sheet.** If the last page has nothing on it, no empty sheet is printed. Empty
  pages in the middle are still printed.
- The page-break lines, their labels, the fold guides, the grid dots and the red cross never
  appear in the PDF.
- A region that starts on one page but is tall enough to cross into the next appears at the bottom of
  its own sheet and its lower part also shows at the top of the next sheet.

## Saving and opening

Page breaks are saved in the `.lsheet` file. A sheet with page breaks is saved in a newer file
version (version 4), so a version of LiveSheet from before page breaks cannot open it. Sheets
without any page breaks are saved the same way as before.

## Things to know

- There is no undo yet. Inserting a page break moves regions and cannot be taken back with a
  keystroke. If you are unsure, save first; the status message tells you exactly how far things moved.
