# Error messages

Every message LiveSheet can show you while using the features documented in this manual, grouped
by feature area. This list only grows (new rows get added as features ship); it isn't reorganised
just because a newer feature arrives.

## Plots

These appear either next to the Plot dialog field they belong to, or as a banner above the
dialog's buttons when no single field is clearly at fault. See [Plots](plots.md).

| Message | Cause | Fix |
|---|---|---|
| `Variable(s) is required` | The Variable(s) field (existing name, or a sampling range's name/From/To) was left empty when you clicked OK/Apply. | Fill in an existing variable's name, or all of the sampling range's fields. |
| `At least one function is required` | Every Function(s) box was left blank. | Type at least one expression to plot. |
| `points must be between 2 and 10000` | The Points field (sampling mode) isn't a whole number, or is outside 2-10000. | Type a whole number of sample points in that range, or leave it blank for the default (101). |
| `lower limit must be below upper limit` | An axis's min box and max box are both filled with plain numbers in the same unit, and min isn't below max. | Swap or correct the two values. |
| `<name> is not defined` (e.g. `Y is not defined`) | A Function(s) row or the Variable(s) field uses a name that isn't defined anywhere earlier on the sheet. | Define that name above the plot, or fix the typo. |
| `Units do not match: traces have different units` | Two or more Function(s) rows produce values with different kinds of unit (e.g. one gives metres, another seconds). | Make every plotted expression resolve to the same kind of unit. |
| `Units do not match: limit is <unit or "dimensionless">` | An axis limit (X/Y min or max) is in a unit that doesn't match the data actually being plotted on that axis. | Use a limit in the same kind of unit as that axis's data, or leave it blank. |
| `Units do not match: sampling limits have different units` | In "Sample a new range" mode, the From and To values are in different kinds of unit. | Use the same kind of unit for From and To (or no unit on either). |
| `<axis>unit needs a unit` | The X unit or Y unit field was filled with something that isn't a recognised unit. | Type a valid unit, or leave the field blank. |
| `<axis>unit given but <axis> has no unit` | A display unit was given for an axis whose data has no unit at all (a plain number). | Remove the unit from that field. |
| `Axis limits must be finite real numbers` | An axis limit evaluated to something that isn't a finite real number (e.g. infinite or complex). | Use a plain finite value for that limit. |
| `show '<text>' needs a single value` | A Function(s) row produced more than one value (a vector) while the Variable(s) field is in "existing" mode with a single-value range variable. | Either plot an expression that gives one value per sample, or switch Variable(s) to a vector. |
| `show '<text>' needs a vector` | A Function(s) row produced a single value while Variable(s) is a vector. | Give that row an expression that produces one value per entry of the vector, or switch Variable(s) to a range variable. |
| `over needs a range variable or a vector` | The Variable(s) field (existing mode) names something that is neither a range variable nor a vector. | Point it at a range variable or a vector already defined above the plot. |

## Vectors and matrices

These appear either at the specific cell/field in the Matrix dialog, or on the committed region
itself once the text is actually evaluated. See [Vectors and matrices](matrices.md).

| Message | Cause | Fix |
|---|---|---|
| `Every cell must have a value` | A cell in the grid was left blank when you clicked OK. | Fill in every cell, or remove the row/column you don't need. |
| `A cell cannot contain ',' or ';'; use Add column/Add row instead` | A single cell's text has a top-level comma or semicolon (e.g. typing `1, 2` into one box). | Split the values into separate cells using Add column/Add row (a comma inside parentheses, like `f(a, b)`, is fine). |
| `Name is required` | "Define as" was chosen but the Name box was left blank. | Type a name, or switch back to "No name (insert as a value)". |
| `<name> is not defined` | A cell's expression uses a name that isn't defined anywhere earlier on the sheet (surfaces once the matrix is committed, with the numeric `=` display). | Define that name above the matrix, or fix the typo. |
| `Units do not match` | The numeric `=` display unit you asked for doesn't match the matrix's own entries. | Use a matching display unit, or leave the display unit blank. |
| `Nested matrices are not supported` | A cell contains its own bracket literal (e.g. `[1,2]` typed inside another cell). | Use a plain number or expression in that cell instead of a nested matrix. |

## Differential equations

These appear on the `ode`/`start`/`over`/`accuracy`/`steps`/`evolve` region itself, once it's
evaluated. See [Differential equations](odes.md).

| Message | Cause | Fix |
|---|---|---|
| `ode needs an equation` | An `ode` line has nothing after the word `ode` before its `in <name>` tag. | Write the equation between `ode` and `in <name>`. |
| `Write the highest derivative alone on the left: diff(name(t), t[, n]) == ...` | An `ode` line's left side isn't exactly one `diff(...)` call (e.g. `y(t) + diff(y(t), t) == 0`), or the line has more than one `==`. | Rearrange the equation so the highest derivative stands alone on the left of `==`. |
| `All equations of "<name>" must use the same independent variable` | Two `ode` lines sharing one tag differentiate with respect to different variable names (e.g. one uses `t`, another `s`). | Rewrite every equation of that tag in terms of one independent-variable name. |
| `No equations declared for ODE system "<name>"` | An `evolve`/`start`/`over` line is tagged `in <name>`, but no `ode` line exists anywhere for that tag. | Add at least one `ode ... in <name>` line, or fix the tag's spelling. |
| `Use "start f(point) == value" (optionally f'(point) == ..., ...)` | A `start` line's text doesn't match `f(point) == value` (comma-separated for several conditions). | Match that shape exactly; use `'`/`''` right after the function name for a first/second derivative's starting value. |
| `"<name>" is not an equation of ODE system "<name>"` (e.g. `"z" is not an equation of ODE system "m1"`) | A `start` or `over` line names a function that has no `ode` equation under that tag (typo, or it belongs to a different tag). | Fix the function name, or move the line to the right tag. |
| `"<f>" is declared twice in model "<name>"` (e.g. `"y"`, or `"y'"` for the first-derivative condition) | The same derivative order of the same function was given a starting value twice — on one `start` line, or across two. | Remove the duplicate; keep exactly one condition per order. |
| `"<name>" needs N initial condition(s) for <f>, has M` | A function whose equation has order N was given a number of conditions other than N. | Give exactly one condition for each order, 0 up to N-1. |
| `"<name>" needs one condition of each order 0..N-1 for <f>` | The right number of conditions were given, but with a gap (e.g. order 0 and order 2 given, order 1 missing). | Give one condition for every order from 0 up to N-1, with no gaps. |
| `All initial conditions of "<name>" must be given at the same point` | Two starting conditions (for the same tag, same or different functions) use different values of the independent variable. | Give every condition of one tag at the same point — two-point boundary conditions aren't supported. |
| `Units do not match: "<f>(<point>)" should have units <unit>, not <unit>` (e.g. `"y'(0)" should have units m/s, not s`) | Two starting conditions of the same function, at different derivative orders, use units that don't agree with each other once you account for how many times the independent variable's own unit must divide in. | Give the higher-order condition in the unit implied by the lower-order one divided by the independent variable's unit (raised to the right power) — e.g. if `y(0)` is in metres and `t` is in seconds, `y'(0)` must be in m/s. |
| `over needs 'NAME from A to B [points N]'` | An `over` line's text after `over` doesn't match the range shape. | Write `over t from 0 to 1` (optionally `points 101`). |
| `only one 'over' line is allowed` | Two `over` lines share the same tag. | Keep a single `over` line per tag. |
| `"over" must use the independent variable "<name>"` | An `over` line's variable name isn't the tag's own independent variable (e.g. `over tau ...` when the equations differentiate with respect to `t`). | Use the tag's actual independent-variable name in the `over` line. |
| `"over" must start at the shared initial point of "<name>"` | The `over` line's starting value doesn't match the point the `start` line's conditions are given at. | Start the `over` range at the same point as the initial conditions; the end can be anywhere. |
| `Units do not match: sampling limits have different units` | The `over` line's `from` and `to` values are in different kinds of unit. | Use matching (or no) units on both ends of the range. |
| `points must be a whole number of at least 2` | The `over` line's `points N` isn't a whole number of at least 2. | Use a whole number of 2 or more, or leave `points` out for the default (101). |
| `accuracy must be a positive number below 1` | An `accuracy` setting's value isn't a number strictly between 0 and 1. | Use a value like `1e-6`; smaller is stricter. Default is `1e-6`. |
| `steps must be a whole number of at least 1` | A `steps` setting's value isn't a whole number of at least 1. | Use a whole positive number. Default is `10000`. |
| `evolve takes 'symbolic', 'numeric' or nothing` | Something other than `symbolic` or `numeric` followed `evolve` (e.g. `evolve fast`). | Use plain `evolve`, `evolve symbolic`, or `evolve numeric`. |
| `No result region for ODE system "<name>" below this region` | An `ode`/`start`/`over`/`accuracy`/`steps` line is tagged `in <name>`, but no `evolve` line for that tag appears below it. | Add an `evolve ... in <name>` line below every region of that tag. |
| `No closed-form solution found for ODE system "<name>"` | `evolve symbolic` was used (or plain `evolve` tried an exact formula first) and no explicit formula could be found. | Use plain `evolve` (it then falls back to a numeric answer, given an `over` line), or `evolve numeric` directly. |
| `over <name> from ... to ... is needed to solve "<name>" numerically` | A numeric answer is needed (no exact formula was found, or you wrote `evolve numeric`) but the tag has no `over` line. | Add an `over <variable> from <start> to <end> in <name>` line. |
| `Not converged: stopped after N function evaluations (steps limit N)` | The numeric solver used up its `steps` budget before reaching the end of the `over` range. | Raise the `steps` setting, or shorten the `over` range. |
| `Not converged: <reason>` | The numeric solver reported failure for a reason other than the steps budget (e.g. the equation is numerically unstable for these inputs). | Check the equation and starting conditions; try a different `accuracy`/`steps`, or a shorter range. |
| `Cannot isolate the highest derivative of "<f>" in "<name>"` | A numeric answer was requested, but the highest derivative of `<f>` can't be isolated algebraically on its own (e.g. it's inside another function on both sides). | Rewrite the equation so the highest derivative appears alone once isolated; not every such equation can be solved numerically yet. |
| `"<equation>" uses a derivative this system cannot reduce to a first-order system` | After isolating the highest derivative, the equation still contains another unresolved derivative or function. | Simplify the equation so each `ode` line is a normal differential equation in one function and its derivatives. |
| `Units do not match: expected <unit>` | A numeric model's bound function was called later (`y(...)`, in a table, or in a plot) with a point whose unit doesn't match the independent variable's own unit for that model. | Call the function with a value in the same kind of unit as the model's `over` line (or no unit, if that model is dimensionless). |

## Components and wiring

These appear on the component box itself (as its error-state fill and as a tooltip), as a message
in the "Add Component" dialog, or as a message after a rejected wire-creation attempt. See
[Components and wiring](components.md).

| Message | Cause | Fix |
|---|---|---|
| `Input '<port>' is not connected.` | A component's required input port has no wire feeding it. | Wire something into that input (drag, or right-click > Connect…). |
| `Input '<port>': upstream component has an error.` | The component feeding this input is itself in an error state this pass. | Fix the upstream component's own error; this one clears automatically on the next recalculation. |
| `Input '<port>' on <Component> is already connected — disconnect it first.` | You tried to wire a second output into an input port that already has a wire. | Delete the existing wire (select it, press Delete) before wiring a new one. |
| `This connection would create a circular dependency.` | The wire you tried to create would make a component depend on itself, directly or through a chain of other components (including wiring a component into one of its own inputs). | Choose a different pair of ports; no wire is created. |
| `Part of a circular connection; this wire needs to be removed.` | A `.lsheet` file was loaded with a circular set of wires already present in it (normally impossible to create through the app itself). | Delete one of the wires in the cycle. |
| `Unknown component kind '<kind>'.` | The component's kind isn't recognised by this build of LiveSheet (for example, a file saved by a newer version). | Open the file with a LiveSheet build that supports that kind, or remove/replace the component. |
| `Units do not match` | A Formula component's expression combines inputs with incompatible units (e.g. adding metres to seconds). | Give the inputs feeding that component compatible units, or adjust the expression. |
| `Division by zero` | A Formula component's expression divides by zero with the current input values. | Change the inputs so the expression no longer divides by zero. |
| `A wire must run from an output port to an input port.` | A wire-creation attempt tried to connect two output ports or two input ports. | Connect an output port to an input port instead. |
| `Name is required` | The "Add Component" dialog's Name field was left blank. | Type a name for the component. |
| `Name must start with a letter and contain only letters, digits, underscore` | The component name you typed doesn't fit that pattern. | Start with a letter, then use only letters, digits and underscores. |
| `Expression is required` | The Value or Formula kind's Expression field was left blank. | Type an expression. |
| `At least one input name is required` | A Formula component's "Input names" field was left blank. | Type at least one input name. |
| `'<name>' is not a valid input name` | One of the comma-separated input names doesn't start with a letter, or contains something other than letters/digits/underscore. | Fix that input name. |
| `Input names must be unique` | The same input name was typed more than once. | Give each input a different name. |
| `No compatible ports available.` | The "Connect…" dialog has no other component with a port of the opposite kind to offer. | Add another component with a matching input/output port first. |

## Truss analysis

These appear on the `nodes`/`elements`/`area`/`modulus`/`support`/`load`/`resolve` region
itself, once it's evaluated. See [Truss analysis](truss.md).

| Message | Cause | Fix |
|---|---|---|
| `No node coordinates declared for truss model "<name>"` | A `support`/`load`/`resolve` (or other) line is tagged `in <name>`, but no `nodes` line exists for that tag. Same pattern for `No element connectivity declared ...`, `No cross-section area declared ...`, `No elastic modulus declared ...` (missing `elements`/`area`/`modulus`). | Add the missing `nodes <expr> in <name>` (or `elements`/`area`/`modulus`) line. |
| `Node coordinates already declared for truss model "<name>"` | A second `nodes` line was written for the same tag. Same pattern for `Element connectivity already declared ...`, `Cross-section area already declared ...`, `Elastic modulus already declared ...` (a second `elements`/`area`/`modulus` line). | Keep exactly one `nodes`/`elements`/`area`/`modulus` line per tag. |
| `node coordinates must be a matrix` | A `nodes` line's expression doesn't evaluate to a matrix at all. | Give `nodes` an Nx2 matrix of coordinates. |
| `node coordinates must have 2 columns (got <n>)` | A `nodes` matrix has some column count other than 2. | Use exactly 2 columns, `(x, y)`, one row per node. |
| `node coordinates must have at least 1 row` | A `nodes` matrix is empty. | Give at least one node. |
| `Units do not match: node coordinates must be a length` | A `nodes` matrix has no unit, or a unit that isn't a length. | Give `nodes` a length unit, e.g. `[0, 0; 4, 0] m`. |
| `element connectivity must be a matrix` | An `elements` line's expression doesn't evaluate to a matrix at all. | Give `elements` an Mx2 matrix of node numbers. |
| `element connectivity must have 2 columns (got <n>)` | An `elements` matrix has some column count other than 2. | Use exactly 2 columns, the two node numbers each bar connects. |
| `element connectivity must have at least 1 row` | An `elements` matrix is empty. | Give at least one element. |
| `Units do not match: element node index must be dimensionless` | A node number inside `elements` was given with a unit (e.g. `1 m`). | Use plain, unitless node numbers. |
| `Element <k>: node index must be a whole number` | A node number inside `elements` isn't a whole number. | Use a whole 1-based node number. |
| `Element <k>: node <n> is out of range 1..<N>` | An `elements` row refers to a node number that doesn't exist in `nodes` (too high, or 0/negative). | Use a node number between 1 and the number of rows in `nodes`. |
| `Element <k> has zero length (nodes <i> and <j> coincide)` | An element's two end nodes are the same node, or two different nodes placed at the exact same coordinates. | Fix the element's node numbers, or move the nodes apart. |
| `area must be a scalar or a vector` | An `area` line's expression isn't a single value or a plain list (e.g. it's a 2D matrix). Same pattern for `modulus must be a scalar or a vector`. | Give one value (applied to every element) or a list with one value per element. |
| `area has <n> values but there are <m> elements (use one value or exactly one per element)` | An `area` list's length isn't 1 and doesn't match the number of elements. Same pattern for `modulus has <n> values but there are <m> elements ...`. | Give exactly one value, or exactly one value per element, in the same row order as `elements`. |
| `Units do not match: cross-section area must be an area` | An `area` value has no unit, or a unit that isn't an area (e.g. a length). | Give `area` an area unit, e.g. `0.0005 m^2`. |
| `Units do not match: elastic modulus must be a pressure` | A `modulus` value has no unit, or a unit that isn't a pressure. | Give `modulus` a pressure unit, e.g. `200 GPa`. |
| `Units do not match: support node index must be dimensionless` | A `support` line's node expression was given with a unit. Same pattern for `Units do not match: load node index must be dimensionless`. | Use a plain, unitless node number. |
| `support node index must be a whole number` | A `support` line's node expression isn't a whole number. Same pattern for `load node index must be a whole number`. | Use a whole 1-based node number. |
| `support references node <n>, out of range 1..<N>` | A `support` line names a node number that doesn't exist in `nodes`. Same pattern for `load references node <n>, out of range 1..<N>`. | Use a node number between 1 and the number of rows in `nodes`. |
| `Node <n> has "<axis>" fixed twice in truss model "<name>"` | The same node and direction (`x` or `y`) was given a `fix` twice — on one `support` line, or across two. | Remove the duplicate; keep exactly one `fix` per node/direction. |
| `Units do not match: support value for "<axis>" must be a length` | A `support ... fix x = <value>` (or `y = <value>`) prescribed displacement isn't in a length unit. | Give the prescribed value a length unit, e.g. `x = 2 mm`. |
| `Node <n> is loaded by more than one "load" line in truss model "<name>"` | The same node number appears on two different `load` lines of the same tag. | Combine everything for that node into one `load` line (`fx`/`fy` together is fine on one line). |
| `Units do not match: load "fx" must be a force` | A `load` line's `fx` (or `fy`) value isn't in a force unit. | Give the load a force unit, e.g. `fx 1000 N`. |
| `Stiffness matrix is singular: truss model "<name>" is unstable or underconstrained` | The structure can still move or rotate freely even with every given `support`/`load` applied — not enough supports, a disconnected/unconnected node, or a node with neither a support nor any element reaching it. | Add enough `support` lines to stop every possible rigid-body movement; check every node is actually used in `elements` or supported directly. |
| `resolve takes no expression` | Text was written after the word `resolve` (before its `in <name>` tag). | Write `resolve in <name>` with nothing in between. |
| `Use "support <node> fix x, y" (optionally "x = <value>")` | A `support` line's text after `support` doesn't match that shape. | Match the shape exactly: a node, then `fix`, then `x`/`y` (optionally `= <value>`), comma-separated. |
| `Use "load <node> fx <value>, fy <value>" (either or both)` | A `load` line's text after `load` doesn't match that shape. | Match the shape exactly: a node, then `fx <value>` and/or `fy <value>`, comma-separated. |
| `"fx"/"fy" given twice on one load line` | The same `fx` or `fy` was written twice in one `load` line's comma-separated list. | Give each of `fx`/`fy` at most once per line. |
| `No result region for truss model "<name>" below this region` | A `nodes`/`elements`/`area`/`modulus`/`support`/`load` line is tagged `in <name>`, but no `resolve` line for that tag appears below it. | Add a `resolve in <name>` line below every region of that tag. |
| `Fix the errors in the regions of model "<name>" first` | Some other region of the same tag (above `resolve`) has its own error. | Fix that region's error first; `resolve` re-checks automatically once it's fixed. |
| `<name> is not defined` (e.g. `x is not defined`; `x, y are not defined` for more than one) | A `nodes`/`elements`/`area`/`modulus`/`support`/`load` expression uses a name that isn't defined anywhere earlier on the sheet. | Define that name above the truss region, or fix the typo. |

## CAD profile import (DXF)

These appear on the "CAD profile (DXF)" component box itself (as its error-state fill and as a
tooltip), or in the "Add Component" dialog. See [CAD profile import (DXF)](cad-profiles.md).

| Message | Cause | Fix |
|---|---|---|
| `File path is required` | The "Add Component" dialog's Path field was left blank when you clicked OK. | Type a path, or click Browse… and pick a `.dxf` file. |
| `No DXF file path set.` | The component's Path configuration is blank (normally caught by the dialog's own "File path is required" check before you get this far). | Set a Path. |
| `Could not open DXF file: <reason>.` | The Path points at a file that doesn't exist, or can't be opened (e.g. a permissions problem). | Check the path and that the file is readable. |
| `Could not read DXF file: not a valid DXF file.` | The file exists and opens, but isn't a well-formed DXF file (wrong format, truncated, corrupted). | Point Path at a genuine `.dxf` file, re-exported if needed. |
| `Drawing has no usable unit information; set 'unit' in this component's configuration, e.g. 'mm'.` | Unit is blank, and the file's own header doesn't declare a usable length unit (or doesn't declare one at all). | Type a unit into the Unit field, e.g. `mm`. |
| `Unknown length unit '<unit>'; use one of LiveSheet's existing length units, e.g. 'mm', 'm', 'inch'.` | The Unit field was filled in with something that isn't one of LiveSheet's own length units. | Use one of `mm`, `cm`, `m`, `km`, `um`, `nm`, `inch`, `ft`, `yd`, `mi`. |
| `No closed profile found (phase 1 supports one closed straight-sided polyline entity only).` | After the Layer filter, nothing on the drawing forms (or could form) a closed loop at all — e.g. an empty entity set, or only non-geometric entities like text. | Check the Layer filter and that the drawing actually has a closed outline on it. |
| `This profile uses curved segments or separate line segments, not yet supported by this component (phase 1 supports one closed straight-sided polyline entity only).` | After the Layer filter, there's a polyline that isn't marked closed, or an `ARC` that isn't a full circle, and nothing else on the filtered set forms a closed loop. | Close the polyline, or redraw a full-circle arc as an actual `CIRCLE` entity; or adjust the Layer filter. |
| `Could not assemble a single closed loop from LINE entities on this layer.` | The standalone `LINE` entities on the filtered set don't chain end-to-end into exactly one closed ring — a gap, a branch point, or a dangling loose end. | Check every `LINE` endpoint that's supposed to connect actually touches its neighbour; close any gap. |
| `Profile has zero area.` | A candidate loop has fewer than 3 distinct points, or its points are collinear (zero area) — including a degenerate zero-length or duplicated `LINE` that technically "closes" into a near-empty loop. | Fix the outline so it encloses a real, non-zero area. |
| `Loop winding does not match the outer/hole convention (outer counter-clockwise, inner clockwise); check this profile's winding direction.` | More than one closed loop was found, but either more than one is wound counter-clockwise, or the single largest loop is wound clockwise. | Make sure the outer boundary is wound counter-clockwise and every hole is wound clockwise. |
| `A hole loop extends outside the outer profile's boundary.` | A correctly clockwise-wound hole loop's bounding box isn't entirely inside the outer loop's bounding box. | Move the hole fully inside the outer boundary. |

## Undefined names and bare units

These appear on the line itself. See [Formula tabs](formula-tabs.md), section "Unit names on their
own".

| Message | Cause | Fix |
|---|---|---|
| `<name> is not defined` (e.g. `F is not defined`) | The expression has no digit and consists only of unit names you have not defined yourself (`F/A`, `F =`, `V*A =`, `sigma := F/A`). LiveSheet takes this to be a formula whose variables you forgot. The name shown is the first one. The message is also shown for a line that depends on such a line (for example `W is not defined`). | Define the name before the formula (`F := 10 N`), or, if you meant the unit, write a number before it (`5 F`). |
| `<names> are not defined` (e.g. `Ac, P are not defined`; `Is, R are not defined`) | A formula, such as one inserted from a formula tab, uses several names that are not defined. The names are listed in alphabetical order. | Define each listed name above the formula, or rename it to one you defined. |
| `<name> is not defined` for a unit alias (e.g. `u := m/s` gives `m is not defined`, then `u is not defined` wherever `u` is used) | A definition whose right side is only unit names. The alias idiom is no longer accepted. | Include a number: `u := 1 m/s`. |
| `<name> is not defined` for a bare conversion (e.g. `m = mm`) | A conversion written with no quantity in front. | Write a quantity: `1 m = mm` (gives `= 1000 mm`). |
| `g is not defined` / unexpected result with `g` | `g` is standard gravity, not grams. A bare `g =` or `x := g` is rejected, and `28.97 g/mol` is a gravity-per-mole, not a molar mass. | Use `gm` for grams (`28.97 gm/mol`). |

Not caught, by design: `m^2` on its own, `P/A` when only `P` is defined, expressions containing a
digit (`F^2/A`), and unit names inside function calls. These give a number built from the unit
values instead of an error, so define your variables first.

## Pages and page breaks

This message appears in the status bar at the bottom left of the window (not on a region). See
[Pages and page breaks](pages.md).

| Message | Cause | Fix |
|---|---|---|
| `This position is already the top of a page.` | You chose Insert > Page Break while the cursor sits exactly at the top of the sheet or exactly at an existing page break. A break there would only make an empty page, so nothing is changed. | Click lower down on the page, where you want the new page to begin, and insert the break there. |

A related message that is not an error: after a successful break, the status bar reads
`Page break inserted; moved N regions down by D units.` (for example `moved 2 regions down by 720
units`). It tells you how much content was pushed down.
