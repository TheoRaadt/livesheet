# Moving regions

You can rearrange your sheet at any time. Drag a region with the mouse, or nudge it with the arrow
keys. Everything on the sheet recalculates as you move, so you can see straight away what a new
position does to your results.

## Dragging with the mouse

1. Press the left mouse button on a region (on its text, its result, or the space around them).
2. Move the mouse. Once the pointer is about 4 screen pixels away from where you pressed, the region
   starts to follow it, and the pointer turns into a closed hand.
3. Release the button to drop the region.

A region always lands on the dotted grid (10 units), so you will see it step from dot to dot as you
drag. A region cannot be moved past the top or left edge of the sheet.

- **A click is not a drag.** If the pointer moves less than 4 pixels, nothing moves. The region is
  just selected, and the sheet is not marked as changed.
- **Zoom does not matter.** The region follows the pointer on screen. At 200% zoom, dragging 100
  pixels moves the region 50 units on the sheet.
- **Near the window edge,** the view scrolls on its own so the region you are dragging stays
  visible.
- **Hovering** over a region you can move shows an open hand.
- The right and middle mouse buttons never move anything.

**Worked example.** A region `a := 1` sits at position (100, 100). Press inside it, drag the pointer
53 units to the right and 27 down, and release. The region lands at (150, 130): the nearest grid
position to (153, 127). It stays selected, and the sheet is marked as changed.

## Click first, then drag

You can click a region to select it and then, straight away, press again and drag. That works. (Two
quick presses in a row are normally a double-click, which starts editing; LiveSheet waits to see
whether you move. If you move the pointer, it is a drag. If you hold still and release, it is a
double-click and the region starts editing, as before.) Plot regions work the same way: the plot
dialog opens only if you did not drag.

To start editing a region without dragging it, double-click it, or select it and press Enter.

## Dragging a region you are editing

While you edit a region, its text area belongs to the caret: pressing and dragging inside the text
selects text and never moves the region.

To move a region you are editing, press on its frame, the thin ring around the text, and drag. The
region moves and stays in editing mode, with your text and the caret exactly as they were. The
pointer shows an open hand over the frame and a text cursor over the text.

## Moving several regions at once

Select more than one region first, by dragging a selection rectangle on empty canvas or with
**Select All Regions**. Then drag any one of the selected regions. All of them move by the same
amount and keep their distances from each other, even when they are different kinds (math, text,
plot, component).

If one of the selected regions would be pushed past the top or left edge, the whole group stops
there, so the group is never squashed.

**Worked example.** Region 1 is at (10, 10) and region 2 at (200, 150), both selected. Drag region 1
by 100 units up and to the left. Region 1 stops at (0, 0) and region 2 ends at (190, 140): they are
still 190 units apart horizontally and 140 vertically.

Page-break lines are never moved by a drag, even if they are part of the selection.

## Cancelling a drag with Esc

While you are still holding the mouse button, press **Esc**. Every region jumps back to where it was
when you pressed, the sheet is no longer marked as changed by that drag, and the results go back to
what they were. The rest of that press, move and release does nothing. Switching to another window
mid-drag has the same effect.

Esc when you are not dragging works as before: it leaves editing.

## Nudging with the arrow keys

Select one or more regions (none of them in editing mode) and press an arrow key:

| Key | What it does |
|---|---|
| Arrow key | Moves the selection one grid cell (10 units) in that direction |
| Shift + arrow key | Moves the selection five grid cells (50 units) |

Holding the key down repeats the move. If any selected region would cross the top or left edge, the
whole selection stays still in that direction, and a nudge that moves nothing does not mark the sheet
as changed. With nothing selected, the arrow keys move the red cross instead (Shift moves it 50
units there too).

**Worked example.** Region `a := 1` is selected at (100, 100). Press Right: it is at (110, 100). Press
Shift+Down: it is at (110, 150). Press Left ten times and then once more: it stops at x = 0.

## Moving changes the calculation order

LiveSheet calculates left to right, then top to bottom, page by page (see
[Pages and page breaks](pages.md)). The order is worked out from where your regions are now, so
moving a region can change it. Results update when you drop the region (right away after a drag, and
after a short pause for a nudge), and they also refresh during a drag whenever you pause.

**Worked example.** `a := 1` is at (300, 50) and `a =` is at (10, 200). The right-hand one is to the
left, so it is calculated first and shows that `a` is not defined. Drag `a := 1` to (10, 100): now it
is above `a =` in the same column, so `a =` shows `= 1`. Drag it back to (300, 50) and the error
returns. See [Error messages](errors.md).

Dragging a region across a page-break line moves nothing else; the region simply belongs to the page
it is now on. Wires between components follow their components while you drag.

## Things to know

- **There is no undo yet.** Esc during the drag is your safety net while the button is held down.
  After you drop, the move cannot be taken back with a keystroke, so save first if you are unsure.
- Positions are saved in the `.lsheet` file as before; nothing about the file changes. Regions are
  stored in calculation order, so after a move the order inside the file may differ.
- Things that already react to a press keep priority over moving: a plot's resize handle resizes
  the plot, an output terminal on a component starts a wire, and a press on empty canvas places the
  red cross and starts a selection rectangle.
- You cannot place a region off the grid.
