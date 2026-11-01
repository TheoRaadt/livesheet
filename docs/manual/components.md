# Components and wiring

A component is a small, self-contained calculation box you place on the sheet and connect to
other components with wires, instead of writing one long formula. LiveSheet works out the order
to calculate them in from how they're wired together, not from where you happened to drop them on
the page.

Components live on the same canvas as your math, text and plot regions — there's no separate
"wiring mode" to switch into. A sheet with no components on it behaves exactly as it always has.

## Placing a component

Choose **Insert > Component…**. The **Add Component** dialog opens:

1. Pick a **Kind**:
   - **Value** — a single output named `value`, computed from one expression you type in
     **Expression:**. For example, typing `9.81 m/s^2` gives an output of `9.81 m/s^2`.
   - **Formula** — one or more named inputs (type them comma-separated in **Input names
     (comma-separated):**, e.g. `a, b`) and a single output named `result`, computed from an
     **Expression:** written in terms of those input names (e.g. `a + b`).
   - **CAD profile (DXF)** — reads a cross-section outline out of a `.dxf` drawing file and
     outputs its area, centroid, second moments of area and section moduli. See
     [CAD profile import (DXF)](cad-profiles.md) for the file path/layer/unit fields and a worked
     example.
2. Give it a **Name:** (must start with a letter, and contain only letters, digits and
   underscores).
3. Click **OK** to place it at the crosshair; **Cancel** creates nothing.

A component's output depends only on its own configuration and whatever is currently on its own
input ports — never on anything else on the sheet. Components don't read or write ordinary sheet
variables defined in math regions, and math regions can't see a component's output by name
either; the only way a value gets from one component to another is a wire.

## Connecting components with wires

A wire always runs from one component's output port to another component's input port. You can
create one two ways:

- **Drag** from an output port's small terminal (on the right edge of the box) to an input port's
  terminal (on the left edge of another box), and release.
- **Right-click** a component and choose **Connect…**. This opens a small dialog listing every
  compatible port on the sheet; pick one and click **OK**. Right-clicking lands on the nearest
  port terminal if you're close enough to one, or otherwise defaults to that component's first
  port — you don't need to click the exact tiny terminal to reach this dialog.

Rules, checked the moment you try to create a wire:

- **One wire per input.** An input port that's already connected rejects a second wire; disconnect
  the existing one first (select the wire and delete it).
- **One output can feed many inputs.** There's no limit on how many input ports one output can
  feed.
- **No circular connections.** A wire that would make a component depend on itself, directly or
  through a chain of other components, is rejected outright — nothing is created.
- Wires aren't type-checked when you draw them; if the value actually produced turns out to be
  unusable by the component on the receiving end, that shows up as an ordinary error on the
  receiving component once it's evaluated (see Errors below).

Deleting a component (select it, press Delete/Backspace) also removes every wire attached to it.
Deleting just a wire (select the wire itself, press Delete/Backspace) leaves both components it
was connected to untouched.

## A worked example

1. **Insert > Component…**, Kind "Value", Name `V1`, Expression `12 m/s`. Click OK.
2. **Insert > Component…**, Kind "Value", Name `V2`, Expression `3 m/s`. Click OK.
3. **Insert > Component…**, Kind "Formula", Name `F1`, Input names `a, b`, Expression `a + b`.
   Click OK. Because neither input is wired yet, `F1` shows an error ("Input 'a' is not
   connected.") and has no output.
4. Drag from `V1`'s `value` output port to `F1`'s `a` input port.
5. Drag from `V2`'s `value` output port to `F1`'s `b` input port.

`F1` now shows no error, and its `result` output is `15 m/s` (12 m/s + 3 m/s). If you later delete
`V1`, the wire into `F1.a` disappears with it and `F1` goes back to showing "Input 'a' is not
connected." until you wire something else into it.

## Reading a component's state on the sheet

Each box shows its name and kind in the header, a one-line summary of its configuration, and its
ports as small labelled terminals along its left (inputs) and right (outputs) edges. A component
currently in an error state is filled with the same error colour used for a math region with a
problem, and hovering over it shows the error message as a tooltip. A wire whose destination is
currently in an error state is drawn in that same error colour; it returns to its normal colour
the moment the error clears.

## Errors

See [Error messages](errors.md#components-and-wiring) for the exact wording of every message a
component or the "Add Component"/"Connect…" dialogs can show you, what causes it, and how to fix
it.
