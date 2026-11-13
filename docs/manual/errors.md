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
| `<name> is not defined` (e.g. `Y is not defined`) | A Function(s) row or the Variable(s) field uses a name that isn't defined anywhere earlier on the sheet. If the name is defined further along, the message continues with the 'defined later' hint (see [Undefined names](#the-defined-later-hint)). | Define that name above the plot, or fix the typo. |
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
| `<name> is not defined` | A cell's expression uses a name that isn't defined anywhere earlier on the sheet (surfaces once the matrix is committed, with the numeric `=` display). If the name is defined further along, the message continues with the 'defined later' hint (see [above](#the-defined-later-hint)). | Define that name above the matrix, or fix the typo. |
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
| `<name> is not defined` (e.g. `x is not defined`; `x, y are not defined` for more than one) | A `nodes`/`elements`/`area`/`modulus`/`support`/`load` expression uses a name that isn't defined anywhere earlier on the sheet. If the name is defined further along, the message continues with the 'defined later' hint (see [above](#the-defined-later-hint)). | Define that name above the truss region, or fix the typo. |

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
| `<name> is not defined` (e.g. `F is not defined`) | The expression has no digit and consists only of unit names you have not defined yourself (`F/A`, `F =`, `V*A =`, `sigma := F/A`). LiveSheet takes this to be a formula whose variables you forgot. The name shown is the first one. The message is also shown for a line that depends on such a line (for example `W is not defined`). If the name is defined further along, the message continues with the 'defined later' hint (see below). | Define the name before the formula (`F := 10 N`), or, if you meant the unit, write a number before it (`5 F`). |
| `<names> are not defined` (e.g. `Ac, P are not defined`; `Is, R are not defined`) | A formula, such as one inserted from a formula tab, uses several names that are not defined. The names are listed in alphabetical order. If a name is defined further along, the message continues with the 'defined later' hint (see above). | Define each listed name above the formula, or rename it to one you defined. |
| `<name> is not defined` for a unit alias (e.g. `u := m/s` gives `m is not defined`, then `u is not defined` wherever `u` is used) | A definition whose right side is only unit names. The alias idiom is no longer accepted. | Include a number: `u := 1 m/s`. |
| `<name> is not defined` for a bare conversion (e.g. `m = mm`) | A conversion written with no quantity in front. | Write a quantity: `1 m = mm` (gives `= 1000 mm`). |
| `g is not defined` / unexpected result with `g` | `g` is standard gravity, not grams. A bare `g =` or `x := g` is rejected, and `28.97 g/mol` is a gravity-per-mole, not a molar mass. | Use `gm` for grams (`28.97 gm/mol`). |

### The 'defined later' hint

If a name is reported as not defined but the sheet does define it further along in the calculation
order, the message gets one more sentence:

`<name> is not defined. A definition must come before its use (left to right, then top to bottom); defined later: <name>.`

With several undefined names, the sentence lists only the ones that are defined later, in
alphabetical order, for example `q, x are not defined. A definition must come before its use (left to
right, then top to bottom); defined later: x.` The first part of the message is unchanged.

Example: you write `y := 2*x =` and, to its right or lower on the page, `x := 4`. The first region
shows the message above with `x`. Fix it by moving `x := 4` to the left of, or above, the line that
uses it. Or make it a global definition, `x ≡ 4`, which is visible everywhere on the sheet and needs
no particular position.

The hint is not added when:

- the name is defined nowhere on the sheet (a typo), or only in the same region (`x := x + 1`);
- the name is defined only earlier in the order (then the order is fine and the earlier line
  carries the real error);
- the name is a global definition, a unit, a built-in, or a variable from imported data.

See [Moving regions](moving-regions.md) and [Pages and page breaks](pages.md) for how the order is
decided.

Not caught, by design: `m^2` on its own, `P/A` when only `P` is defined, expressions containing a
digit (`F^2/A`), and unit names inside function calls. These give a number built from the unit
values instead of an error, so define your variables first.

## Statistics

These appear on the line that uses the function. `<f>` stands for the function's own name (for
example `mean`, `normal_pdf`). See [Statistics](statistics.md).

| Message | Cause | Fix |
|---|---|---|
| `<f>() needs a vector` (e.g. `mean() needs a vector`) | The list argument is a matrix with more than one row and more than one column. | Pass a single column or single row (or one number). |
| `<f>() needs a scalar` | A distribution function got a vector or matrix where one number is expected. | Pass a single number. |
| `<f>() needs real numbers` | An entry or argument isn't a real number (for example complex). | Use real numbers only. |
| `<f>() needs at least 2 values` (e.g. `variance() needs at least 2 values`; also `stdev`, `covariance`, `correlation`) | The list has fewer than 2 values. | Supply at least 2 values, or use `population_variance`/`population_stdev`, which accept 1. |
| `p must be between 0 and 1` | `quantile`, `uniform_quantile`, or the `p` of a binomial distribution is outside 0 to 1. | Use a value from 0 to 1 inclusive. |
| `q must be between 0 and 1` | The `q` of `binomial_quantile` is outside 0 to 1. | Use a value from 0 to 1 inclusive. |
| `q must be at least 0 and less than 1` | The `q` of `poisson_quantile` is below 0 or is 1 or more. | Use a value from 0 up to, but not including, 1. |
| `p must be strictly between 0 and 1` | `normal_quantile` was given exactly 0 or 1, or a value outside. | Use a value greater than 0 and less than 1. |
| `<f>() is undefined when a vector is constant` (e.g. `correlation() is undefined when a vector is constant`; also `covariance`) | All entries of one of the two lists are equal. | Use data that varies. |
| `Vectors must have the same length (<m> and <n>)` (e.g. `(2 and 3)`) | The two lists given to `covariance`, `correlation`, `fit_linear`, `fit_poly` or `r_squared` (its `x` and `y`) differ in length. | Make both lists the same length. |
| `Units do not match` | A list has entries with different kinds of unit, or a display unit you asked for doesn't fit the result. | Use one kind of unit throughout, or a matching display unit. |
| `<name> is not defined` | A list entry or argument uses a name not defined earlier on the sheet. If the name is defined further along, the message continues with the 'defined later' hint (see [above](#the-defined-later-hint)). | Define it above, or fix the typo. |
| `<f>() does not accept a unit in this version` (e.g. `normal_pdf() does not accept a unit in this version`) | A distribution or sampling function, or the `p` of `quantile`, was given a value with a unit. | Pass plain numbers; remove the unit (see the notes in [Statistics](statistics.md)). |
| `sigma must be positive` | The `sigma` of a normal function is zero or negative. | Use a positive spread. |
| `a must be less than b` | A uniform function was given bounds with `a` not below `b`. | Put the lower bound first and make it smaller. |
| `lambda_ must be positive` | The rate of a Poisson function is zero or negative. | Use a rate above 0. |
| `k must be a non-negative integer` | The `k` of a binomial or Poisson function is negative or not a whole number. | Use a whole number of 0 or more. |
| `n_trials must be a non-negative integer` | `n_trials` of a binomial function is negative or not a whole number. | Use a whole number of 0 or more. |
| `n must be a positive integer` | The `n` (number of draws) of a `..._sample` function is zero, negative or not a whole number. | Use a whole number of 1 or more. |
| `n is too large (max 10000)` | More than 10000 draws were requested. | Ask for 10000 or fewer. |
| `seed must be a non-negative integer` | The `seed` of a `..._sample` function is negative or not a whole number. | Use a whole number of 0 or more. |
| `fit_linear() needs at least 2 points` | `fit_linear` was given fewer than 2 points (or a single number). | Supply at least 2 `(x, y)` pairs. |
| `degree must be a positive integer` | The `degree` of `fit_poly` is 0, negative, fractional, or a matrix. | Use a whole number of 1 or more, for example `2`. |
| `degree <d> needs at least <d+1> points, has <n>` (e.g. `degree 5 needs at least 6 points, has 4`) | `fit_poly` was asked for a degree that is not smaller than the number of points. | Lower the degree below the number of points, or add data. |
| `Matrix does not have full column rank` | The fit cannot be settled: for example all `x` values are the same, or there are too few different `x` values for the degree. | Use data with more distinct `x` values, or lower the degree. |
| `predict() needs a vector of coefficients` | The first argument of `predict` (or `r_squared`) is a single number or a matrix with several rows and columns. | Pass the vector returned by `fit_linear`/`fit_poly`, or a single column or row of coefficients, constant term first. |
| `predict() needs a scalar or vector x` | The `x` given to `predict` is a matrix with several rows and columns. | Pass a single number or a single row or column. |
| `r_squared() is undefined when y is constant` | Every value in `y` is the same, so there is no variation for the fit to explain. | Use `y` data that varies. |
| `Units do not match` (regression) | `predict`'s `x` is not the same kind of unit as the `x` you fitted with, or `r_squared`'s predicted values and `y` are different kinds of unit. | Give `x` in the unit you fitted with (or one of the same kind); check that `y` has the unit the coefficients were fitted for. |

### Hypothesis tests

These appear on the `sample`/`expected`/`claim`/`level`/`verdict` line itself. `<name>` is the
test's `in <name>` tag. See [Hypothesis tests](statistics.md#hypothesis-tests). Some are shown at
the line that is wrong, as soon as you type it; the rest appear on the `verdict` line.

| Message | Cause | Fix |
|---|---|---|
| `No sample declared for hypothesis test "<name>"` | `verdict` ran but no `sample` line above it has that tag. | Add a `sample <list> in <name>` line above `verdict`, or fix the tag's spelling. |
| `hypothesis test "<name>" has <k> sample lines, expected 1 or 2` | Three or more `sample` lines share one tag. | Keep one `sample` line (one-sample or chi-square) or two (Welch). |
| `claim "<claim>" needs one sample line, found <k>` / `claim "<claim>" needs two sample lines, found <k>` (e.g. `claim "mean1 == mean2" needs two sample lines, found 1`) | The number of `sample` lines doesn't suit the claim. | One `sample` line for `mean`/`fits` claims; two for `mean1 ... mean2`. |
| `No claim declared for hypothesis test "<name>"` | There is no `claim` line for that tag. | Add a `claim ... in <name>` line. |
| `Claim already declared for hypothesis test "<name>"` | Two `claim` lines share one tag. | Keep exactly one. |
| `Level already declared for hypothesis test "<name>"` | Two `level` lines share one tag. | Keep at most one. |
| `Expected values already declared for hypothesis test "<name>"` | Two `expected` lines share one tag. | Keep at most one. |
| `Use "claim mean == <value>" ("<" or ">" for one-sided), "claim mean1 == mean2", or "claim fits"` | The `claim` text isn't one of the accepted forms (for example `claim mean <= 7`, `claim mean1 == 7`, or a misspelling). | Use one of the three forms; `==`, `<` and `>` are the only comparisons. |
| `claim "fits" needs an expected line` | `claim fits` without an `expected` line. | Add `expected <list> in <name>`. |
| `claim "<claim>" does not use an expected line` | An `expected` line is present, but the claim is a `mean` claim. | Remove the `expected` line, or change the claim to `claim fits`. |
| `expected has <m> values but sample has <n>` (e.g. `expected has 3 values but sample has 4`) | The `expected` list and the `sample` list differ in length. | Make both lists the same length. |
| `expected values must be positive` | An `expected` value is zero or negative. | Use values above 0 (even if the matching observed count is 0). |
| `expected values must be dimensionless` | An `expected` value has a unit. | Remove the unit. |
| `expected must be a vector` / `sample must be a vector` | The `expected` or `sample` expression is a matrix with several rows and columns. | Give a single column or row (or one number). |
| `level must be a number between 0 and 1` | The `level` is a value with a unit, or isn't a plain number. | Write a plain number such as `0.05`. |
| `level must be between 0 and 1` | The `level` is 0, 1 or outside that range. | Use a value greater than 0 and less than 1. |
| `claimed mean must be a single value` | The value after `claim mean ==` (or `<`, `>`) is a vector or matrix. | Give one number. |
| `claimed mean must be a real number` | The claimed value isn't a real number (for example complex). | Give a real number. |
| `Units do not match` | The claimed value's unit differs from the sample's (for example `claim mean == 12` for a sample in mm), or the two Welch samples have different kinds of unit. | Use the same kind of unit everywhere (or none). |
| `Units do not match: sample counts must be dimensionless` | A chi-square `sample` has a unit. | Use plain counts. |
| `"<name>" needs at least 2 values per sample` | A t-test sample, or a chi-square sample, has fewer than 2 values. | Supply at least 2 values in each sample. |
| `"<name>" sample has zero variance; the t statistic is undefined` (Welch: `"<name>" samples have zero variance; ...`) | All values in the sample (for Welch, in both samples) are equal, so there is no spread to measure. | Use data that varies. |
| `"<name>" sample counts must not all be zero` | Every chi-square sample count is 0. | Supply real counts. |
| `Result too large` | The numbers are so large that the test cannot be computed. | Use smaller values or a different unit. |
| `verdict takes no expression` | Text was written between `verdict` and `in <name>`. | Write `verdict in <name>` and nothing else. |
| `No result region for hypothesis test "<name>" below this region` | A `sample`/`expected`/`claim`/`level` line is tagged `in <name>`, but no `verdict` line for that tag is below it. | Add a `verdict in <name>` line below every line of that test. |
| `<name> is not defined` | A `sample`, `expected`, `claim` value or `level` uses a name not defined earlier on the sheet. If the name is defined further along, the message continues with the 'defined later' hint (see [above](#the-defined-later-hint)). | Define it above, or fix the typo. |

## Optimization (solve models)

See [Optimization](optimization.md). `<...>` stands for text from your sheet.

| Message | Cause | Fix |
|---|---|---|
| `accuracy must be a positive number below 1` | The `accuracy` value is zero, negative, 1 or more. | Use a value such as `1e-8`. |
| `steps must be a whole number of at least 1` | The `steps` value is not a whole number, or is below 1. | Use a whole number such as `200`. |
| `"<x>" is declared twice in model "<m>"` | The same unknown is named in two `vary` lines or twice in one. | Declare each unknown once. |
| `Starting guess for "<x>" must be a real number` | The guess is not a real number. | Give a real number, with a unit if needed. |
| `Starting guess for "<x>" must be finite` | The guess is infinite or undefined. | Use an ordinary number. |
| `No unknowns declared for model "<m>"` | A result line has no `vary` line with the same name. | Add `vary ... in <m>`, and check the names match. |
| `<name> is not defined` | An equation or limit uses a name not defined above. If the name is defined further along, the message continues with the 'defined later' hint (see [above](#the-defined-later-hint)). | Define it above or fix the typo. |
| `Cannot evaluate at the starting guess: ...` | The equations cannot be calculated at your guess (for example a division by zero), or the result is not finite. | Try a different starting guess. |
| `Constraint "<line>" does not involve any unknown` | An equation or limit mentions none of the declared unknowns. | Include an unknown, or remove the line. |
| `Objective "<expr>" does not involve any unknown` | The `least`/`most` expression mentions no unknown. | Use an expression with an unknown. |
| `Units do not match in constraint "<line>"` | Both sides of an equation or limit have different dimensions. | Fix the units. |
| `No constraints declared for this model` | A `settle` line has no equation or limit. | Add at least one equation or limit. |
| `Not converged: stopped after N function evaluations (steps limit S), largest violation V (try another starting guess or raise steps)` | The solver ran out of steps. | Change the starting guess or raise `steps`. |
| `No solution found: the objective has no optimum within the constraints (unbounded or the solver did not converge)` | `least`/`most` has no bounded answer. | Add limits that bound the problem. |
| `No solution found: closest point violates "<line>" by V` | No point satisfies all lines at once. | Check for contradicting equations or limits, or try another guess. |
| `Solving needs the scipy package` | The solving library is not installed. | Install the SciPy package. |

## Pages and page breaks

This message appears in the status bar at the bottom left of the window (not on a region). See
[Pages and page breaks](pages.md).

| Message | Cause | Fix |
|---|---|---|
| `This position is already the top of a page.` | You chose Insert > Page Break while the cursor sits exactly at the top of the sheet or exactly at an existing page break. A break there would only make an empty page, so nothing is changed. | Click lower down on the page, where you want the new page to begin, and insert the break there. |

A related message that is not an error: after a successful break, the status bar reads
`Page break inserted; moved N regions down by D units.` (for example `moved 2 regions down by 720
units`). It tells you how much content was pushed down.

## Moving regions

Moving regions adds no messages of its own. After a drag or nudge, a region that now sits before
the definition it needs shows `<name> is not defined`, followed by the 'defined later' hint (see
[The 'defined later' hint](#the-defined-later-hint)). Move the definition or the
region back, or place the definition further left or higher up in the same column. See
[Moving regions](moving-regions.md).

## The Statistics, Optimization and Outline tabs

These tabs add no error messages of their own. The Statistics and Optimization buttons only insert
text; problems show when the sheet recalculates, under [Statistics](#statistics) or
[Optimization (solve models)](#optimization-solve-models). The Outline tab only lists headings; an
empty list is a hint, not an error. See [The main window](main-window.md#the-outline-tab).

## Calculus templates

The Calculus and root buttons only insert text, so they add no messages of their own. See
[Calculus and root templates](main-window.md#calculus-and-root-templates).

| Message | Cause | Fix |
|---|---|---|
| `Invalid limits given: (x, 0, 3)` (the bracket shows your bounds) | The bounds were written flat, as `integrate(x^2, x, 0, 3)`, or the bounds bracket has too many parts. | Write the bounds in one bracket with the variable: `integrate(x^2, (x, 0, 3))`. |
| `<name> is not defined` (e.g. `b is not defined`) | A bound or the integrand uses a name that has no definition, for example a template whose `a`, `b` or `f` you did not replace, evaluated with `=`. If the name is defined further along, the message continues with the 'defined later' hint (see [above](#the-defined-later-hint)). | Replace the stand-in or define the name above. With `→` an undefined bound is kept as a symbol instead. |
| An error about a number where a variable is expected (SymPy wording) | The integration variable has a definition on your sheet (for example `x := 5`), so `integrate(x^2, x)` integrates over a number. | Use an integration variable that you have not defined. |

## Autocomplete

Autocomplete adds no error messages of its own. If the list does not appear, check that you have
typed at least two letters, that the caret is at the end of the word, that you are in a math region,
and that you have not pressed Esc for this word. A name you accepted but is then reported as `<name>
is not defined` simply is not defined on the sheet (the list also offers built-in names); see
[Undefined names and bare units](#undefined-names-and-bare-units). See
[Autocomplete](autocomplete.md).

## Importing data

These appear in red in the **Import data** window (OK stays greyed out until they are gone), in a
message box after Refresh, Rename or Remove, on the region that uses imported data, or when you open
a file. `<...>` stands for text from your file or sheet. See [Importing data](data-import.md).

### Reading the file

| Message | Cause | Fix |
|---|---|---|
| `Choose a file to import.` | The **File** box is empty. | Click Browse... or type a path. |
| `Cannot open '<path>': file not found.` | The path does not exist (also shown by Refresh when the original file has moved or been deleted; the dataset then stays as it was). | Correct the path, or move the file back. |
| `Cannot read '<path>': <reason>.` | The file exists but the system refused to read it (for example no permission). | Fix the file's permissions, or choose another file. |
| `'<path>' is not valid UTF-8 text; try the Latin-1 encoding option.` | The file contains bytes that UTF-8 cannot decode. | Set **Encoding** to Latin-1. |
| `The text cannot be split into fields: <reason>.` | The file's quoting is broken, so a line cannot be split into cells. | Fix the quotes in the file, or try another delimiter. |
| `The file has no data rows.` | Nothing is left after skipped lines, blank lines and the header row. | Check **Skip first N lines** and **First row is a header**, or choose another file. |
| `Line <n> has <k> field(s), but the first line has <m>.` (for one cell: `Line 3 has 1 field, but the first line has 2.`) | A line has a different number of cells than the first line. | Fix the file, or choose the delimiter that really separates the cells. Line numbers count from the top of the file, including skipped lines. |
| `The file has no numeric column.` | Every column contains something that is not a number. | Check **Decimal mark** and the delimiter; a column with one stray word becomes text. |
| `Column '<name>' has an empty value at line <n>; fill it in or choose to skip incomplete rows.` | A number column has an empty cell and **Incomplete rows** is set to Report an error. | Fill in the cell, or set **Incomplete rows** to Skip them. |
| `No complete rows left.` | **Incomplete rows** is Skip them, but every row had an empty cell. | Fix the data, or check the delimiter and header options. |
| `The file has <n> rows; LiveSheet reads at most 20000.` | More than 20,000 data rows. | Use a smaller file or a part of it. |
| `The file has <n> columns; LiveSheet reads at most 100.` | More than 100 columns. | Use a file with fewer columns. |
| `The file has <n> numeric cells; LiveSheet reads at most 200000.` | Rows times number columns exceeds 200,000. | Remove columns or rows. |
| `The value '<text>...' is too large to read as a decimal number.` | A number written with a decimal point or exponent is too large to be stored. | Correct the value. |
| `Column '<name>': '<unit>' is not a known unit.` | A header's `[unit]`, or a unit typed in the **Unit** cell, is not a unit LiveSheet knows (or contains a number, a sum or a difference). | Fix the unit text, for example `mm`, `N/m`, `kg*m/s^2`, or clear the cell. |

### Option values

These come from the options themselves and normally cannot occur through the window's own fields,
except the first.

| Message | Cause | Fix |
|---|---|---|
| `The delimiter must be a single character other than a quote.` | **Delimiter** is Other and the box is empty, holds more than one character, or holds a quote. | Type exactly one character (not `"`). |
| `The delimiter and the decimal mark must differ.` | For example Comma as delimiter with Comma as decimal mark. | Change one of them. |
| `The decimal mark must be '.' or ','.` / `The number of lines to skip must be 0 or more.` / `Unsupported encoding '<name>'.` / `Unknown handling of incomplete rows '<name>'.` | An option holds a value the window does not offer. | Pick one of the offered choices. |

### Warnings (grey text, import still works)

| Message | Meaning |
|---|---|
| `Column '<name>' is read as text because line <n> holds '<cell>'.` | One cell is not a number under the chosen **Decimal mark**, so the whole column became text and cannot be used in formulas. Change the option or fix the cell if you wanted numbers. |
| `Skipped <n> rows with missing values.` | **Incomplete rows** is Skip them; that many rows were dropped. |
| `Column '<name>' is text; its unit '<unit>' is ignored.` | The header gave a unit to a text column. |
| `Columns changed: removed '<a>'; added '<b>'.` | Shown after **Refresh** when the file's columns are not the same as before. |

### Dataset names

| Message | Cause | Fix |
|---|---|---|
| `'<name>' is not a valid name: use letters, digits and _, not starting with a digit.` | The name is empty or has other characters, or starts with a digit. | Rename it, for example `run2` instead of `2run`. |
| `'<name>' is not a valid name: at most 40 characters.` | The name is longer than 40 characters. | Shorten it. |
| `A dataset named '<name>' already exists.` | Another dataset in the sheet has this name (names are case-sensitive). | Choose a different name. |
| `'<name>' is already a unit name; choose another dataset name.` | For example `m`. | Choose a different name. |
| `'<name>' is already a function name; choose another dataset name.` / `'<name>' is already a constant name; choose another dataset name.` | For example `sin` or `mean`; `pi`. | Choose a different name. |
| `Variable '<v>' would be defined by both dataset '<a>' and dataset '<b>'.` | Two datasets would produce the same variable (for example dataset `a` with column `b_c`, and dataset `a_b` with column `c`). Shown in the import window, or in a message box after Rename. | Rename a dataset (or change a column name in the file). |

### Refresh, Rename and Remove

| Message | Cause | Fix |
|---|---|---|
| `Refresh failed` (message box title, with the reason from the first table) | The file could not be read again. The dataset is unchanged. | Fix the cause shown, then Refresh again. |
| `This dataset has no source file to refresh from.` | The dataset was stored without a file name. | Import the file again instead. |
| `There is no dataset named '<name>'.` | The dataset was removed before the command ran. | Select an existing dataset. |
| `Rename failed` (message box title, with a dataset-name message from above) | The new name was refused. | Choose another name. |

### In your formulas and when opening a file

| Message | Cause | Fix |
|---|---|---|
| `'<name>' is a dataset column and cannot be redefined; rename the variable or the dataset.` (for example `'run1_t' is a dataset column ...`) | A region defines (`:=`, `≡` or a range) a name that a dataset provides. Other regions are not affected. | Use another name for your variable, or rename the dataset. |
| `<name> is not defined` (for example `run1 is not defined`, `run1_F is not defined`) | The dataset was removed or renamed, a refreshed file no longer has that column, a text column was used, or you used the combined matrix `run1` of a dataset whose number columns have different units (the Data tab says "No combined matrix (columns have different units)"). See also [Undefined names and bare units](#undefined-names-and-bare-units). | Use a column that exists, or re-import with the units set the same. |
| `This file was made with a newer LiveSheet version` | The sheet holds datasets (file format version 5) and this LiveSheet build is older, or the file otherwise uses a newer format. | Open it with a newer LiveSheet. |
| `Invalid dataset in file: <reason>` (for example `columns of dataset 'run1' have unequal lengths`, `duplicate name 'run1'`) | The dataset stored in the file is damaged or inconsistent. The file is not opened, so no data is silently lost. | Restore the file from a backup, or fix the file's contents. |

## The toolbar

The larger Standard toolbar adds no error messages. If you cannot see the names on the buttons,
the window is narrow: the toolbar shows pictures only, with the name in the tooltip. See
[The main window](main-window.md#how-the-toolbar-looks).

## 3-D surface plots

These appear in the plot frame of a `surface` region. `<...>` stands for text from your sheet. See
[3-D surface plots](surface-plots.md). Messages about axis units, limits and labels are the same as
for 2-D plots (see [Plots](#plots)), with `x`, `y` or `z` as the axis name, for example
`zunit given but z has no unit` or `lower limit must be below upper limit`.

| Message | Cause | Fix |
|---|---|---|
| `Unknown 3-D plot option '<word>'` | A line starts with a word the 3-D plot does not know (for example `colour`). | Use only `over`, `across`, `show`, `draw`, `view`, `xunit`, `yunit`, `zunit`, `xlim`, `ylim`, `zlim`, `title`, `xlabel`, `ylabel`, `zlabel`. |
| `surface needs an 'over' line` / `surface needs an 'across' line` / `surface needs a 'show' line` | One of the three required lines is missing. | Add the missing line. |
| `surface takes exactly one 'show' line` | Two or more `show` lines. | Keep a single `show` line. |
| `only one '<word>' line is allowed` (e.g. `only one 'over' line is allowed`) | The same option is written twice. | Keep one line of that kind. |
| `show needs an expression` | The `show` line has nothing after it. | Write the height expression. |
| `over needs 'NAME from A to B [points N]'` (also for `across`) | The line is not a name, nor a range variable or vector, nor the sampling form. | Write `over x from 0 to 1 points 25`, or name a range variable or vector. |
| `over needs a name before 'from'` (also for `across`) | The sampling form has no valid name before `from`. | Start with a name, for example `x from 0 to 1`. |
| `over needs a range variable or a vector` (also for `across`) | The line names a single value. | Name a range variable or a vector. |
| `over needs a vector (one row or one column)` (also for `across`) | A matrix with several rows and columns was given as an axis. | Give a single row or column. |
| `over and across need different names` | Both axes use the same name. | Give each axis its own name. |
| `points must be between 2 and 100` | `points` is not a whole number from 2 to 100. | Use a whole number from 2 to 100, or leave it out (25). |
| `over has more than 100 values for a 3-D plot` (also for `across`) | A vector axis has over 100 entries. | Use a shorter vector. |
| `range has more than 100 values for a 3-D plot` | An axis range variable has over 100 values. | Use a range with at most 100 values. |
| `Sampling limits must be finite real numbers` | A `from` or `to` value is infinite or undefined. | Use ordinary finite numbers. |
| `Units do not match: sampling limits have different units` | `from` and `to` are in different kinds of unit. | Use the same kind of unit on both. |
| `draw must be mesh or wire` | `draw` was followed by another word. | Write `draw mesh` or `draw wire`. |
| `view needs two numbers: azimuth and elevation` | `view` has fewer or more than two values. | Write `view 40 30`. |
| `view needs two plain numbers` | A `view` value is not a plain number (for example `view 40 m`). | Use plain numbers, in degrees. |
| `elevation must be between -90 and 90` | The second `view` number is outside that range. | Use an elevation from -90 to 90. |
| `no finite values to plot` | Every height is undefined (for example `sqrt(x - 10)` over 0 to 2), or an axis value is not finite. | Change the expression or the ranges so at least one height is a real number. |
| `show '<text>' needs a single value` | The `show` expression gives a vector or matrix. | Give an expression that is one number per grid point. |
| `<name> is not defined` | An axis or the `show` expression uses a name defined nowhere earlier. If it is defined further along, the 'defined later' hint is added (see [above](#the-defined-later-hint)). | Define it above the plot, or fix the typo. |
| `Units do not match` | A `zunit`/`xunit`/`yunit` or a limit has a different kind of unit than its axis, or the `show` expression mixes units. | Use the matching kind of unit. |

## LaTeX formulas in text regions

These appear as a red line under a text region (starting with `LaTeX:`), as the region's tooltip and
as a dotted underline in the formula. The line has the form `LaTeX: <message> (formula N, character
C)`, where N counts the formulas in the region and C is the character of the formula where the
problem begins; with more than one wrong formula it ends `(+N more)`. See
[LaTeX formulas in text regions](latex-text.md). `\cmd` stands for the command as you typed it.

| Message | Cause | Fix |
|---|---|---|
| `unknown command \cmd` | The command is not in the supported list. | Check the spelling, or see the supported list in the manual page. |
| `unsupported: \cmd` | A command that LiveSheet does not do at all (for example `\newcommand`, `\color`, `\label`, `\usepackage`), or `\\` outside a table. | Leave it out. For numbered equations or `align`, use `$$` with `aligned`. |
| `unsupported: &` | An `&` outside a table environment. | Write `\&` for a literal ampersand, or put the formula in a `matrix`/`aligned`. |
| `unsupported character <c>` | A plain character that has no meaning in math. | Remove it or write it with `\text{...}`. |
| `% is not supported` | A percent sign inside a formula. | Write `\%`. |
| `stray $` | A single `$` inside a display formula. | Remove it, or write `\$`. |
| `\cmd needs an argument` / `\cmd needs two arguments` (e.g. `\frac needs two arguments`) | A command is missing its `{...}` part(s). | Supply them: `\frac{a}{b}`. |
| `\cmd needs a delimiter` | `\left`, `\right` or `\big` was not followed by a bracket. | Follow it with `(`, `[`, `\{`, `|`, `.` and so on. |
| `\cmd needs an environment name` | `\begin` or `\end` has no `{name}`. | Write `\begin{pmatrix}`. |
| `incomplete command at end of formula` | The formula ends with a lone `\`. | Remove it or finish the command. |
| `missing closing }` / `unexpected }` / `missing closing ]` | Braces (or the `[...]` index of `\sqrt`) do not pair up. | Add the missing bracket, or remove the extra one. |
| `missing \right for \left` / `\right without \left` | `\left` and `\right` do not pair up. | Add the other one (use `\right.` for no visible bracket). |
| `missing \end{env}` / `\begin{env} is not supported` / `\end{env} does not match \begin{other}` / `unexpected \end` | A table environment is not closed, is not one of the supported ones, or closes with the wrong name. | Match each `\begin{...}` with its `\end{...}`, using only the supported environments. |
| `\begin{array} needs a column specification` / `array column specification may only use l, c and r` / `array row has more cells than its column specification` | The `array` has no column letters, uses letters other than l, c, r, or a row has more cells than letters. | Write for example `\begin{array}{lcr}` and keep every row within its letters. |
| `matrix too large (limit 50 x 50)` | A table has more than 50 rows or columns. | Make it smaller. |
| `double superscript` / `double subscript` | `x^2^3` or `x_1_2`. | Group it: `x^{2^3}`. |
| `\cmd must be at the start of a group` / `\cmd must follow a big operator` | `\displaystyle` or `\textstyle` is not at the start of a group, or `\limits`/`\nolimits` is not right after a big operator such as `\sum`. | Move it. |
| `\operatorname needs an argument` / `\operatorname needs a plain name` / `\text needs an argument` | `\operatorname` or `\text` has no name, or the name holds more than letters. | Write `\operatorname{rank}` or `\text{words}`. |
| `formula too deeply nested (limit 32)` | More than 32 levels of braces and structures. | Simplify the formula. |
| `formula too long (limit 2000 characters)` | One formula is over 2000 characters. | Split it into several. |
| `too many formulas in this region (limit 200)` | A text region has more than 200 formulas; the extra ones stay as plain text. | Split the text into several regions. |
| `internal error in formula` | An unexpected fault while typesetting that one formula. | Simplify or rewrite the formula; your text is not changed. |

## Mechanical engineering functions

These appear on the line that calls the function. `<fn>` is the function's own name and `<arg>` the
name of an argument as listed in [Mechanical engineering functions](mechanical-library.md).

| Message | Cause | Fix |
|---|---|---|
| `<fn>: <arg> needs a unit of <kind>, for example <unit>` (e.g. `rect_area: b needs a unit of length, for example 1 mm`) | A number with no unit was given where a length, force, pressure and so on is needed. This includes a literal zero such as `0 m`, which loses its unit. | Write the unit, for example `50 mm`; use a small positive value in place of 0 where zero is not allowed. |
| `<fn>: <arg> must be a <kind>, not <unit>` (e.g. `rect_area: h must be a length, not kg`) | The argument has the wrong kind of unit. | Give it a unit of the right kind. |
| `<fn>: <arg> must be dimensionless` | A plain-number argument (such as `K`) was given a unit. | Remove the unit. |
| `<fn>: <arg> must be greater than zero` (e.g. `circle_inertia: d must be greater than zero`) | A length, area, modulus, thickness or `K` is zero or negative. | Use a positive value. |
| `<fn>: <arg> must be larger than <arg2>` (e.g. `ring_inertia: do must be larger than di`) | The outer diameter is not larger than the inner. | Swap the two, or fix the values. |
| `<fn>: <arg> must be a real number` | The argument is complex or not a number. | Use a real number. |
| `<fn>: <arg> has inconsistent units (...)` | The argument itself mixes incompatible units. | Make the units of that argument consistent. |
| `Wrong number of arguments` | The function was called with too few or too many arguments. | Match the argument list in the manual page. |
| `<name> is not defined` | An argument uses a name that is not defined earlier. If it is defined further along, the 'defined later' hint is added (see [above](#the-defined-later-hint)). | Define it above the call. |
| `Units do not match: result is <unit>` | You asked for a display unit of a different kind from the result (for example `= kN` on a moment). A zero result also loses its unit, so a requested unit then fails. | Ask for a unit of the right kind, or use a bare `=` for a zero. |

## Electrical engineering functions

The same patterns apply as for the mechanical functions; the unit kinds here are `voltage`,
`current` and `resistance`. See [Electrical engineering functions](electrical-library.md).

| Message | Cause | Fix |
|---|---|---|
| `<fn>: <arg> needs a unit of <kind>, for example <unit>` (e.g. `voltage_divider: Vin needs a unit of voltage, for example 1 V`; `R1 needs a unit of resistance, for example 1 ohm`) | A number with no unit where a voltage, current or resistance is needed. This also appears for `0 ohm`, whose unit is lost. | Write the unit; use a positive value instead of zero. |
| `<fn>: <arg> must be a <kind>, not <unit>` (e.g. `voltage_divider: R2 must be a resistance, not A`) | The argument has the wrong kind of unit. | Give it the right kind. |
| `<fn>: <arg> must be an angle in radians, not <unit>` (e.g. `average_power: phi must be an angle in radians, not V`) | The angle was given with a unit other than a plain number, `rad` or `deg`. | Write a number, a `pi` expression, `rad` or `deg`. |
| `<fn>: <arg> must be a plain number of turns, not <unit>` | A winding count (`Np`, `Ns`) was given a unit. | Write the count as a plain number. |
| `<fn>: <arg> must be greater than zero` (e.g. `resistors_parallel: R must be greater than zero`, `transformer_secondary_voltage: Np must be greater than zero`) | A resistance, RMS or peak value, or turns count is zero or negative. | Use a positive value. |
| `<fn>: R must be a vector` (e.g. `resistors_series: R must be a vector`) | The list of resistances is a table with several rows and columns. | Use one column (`[10 ohm; 22 ohm]`) or one comma-separated row. |
| `<fn>: needs at least one resistance` | The list of resistances is empty. | Give at least one resistance. |
| `<fn>: R must be a resistance, not <odd unit>` with a strange unit such as `kg²·m⁴/(s⁶·A⁴)` | A row was written with spaces only, for example `[10 ohm 22 ohm]`, which reads as one product. | Separate entries with commas, `[10 ohm, 22 ohm]`, or semicolons. |
| `<fn>: <arg> must be a real number` / `<fn>: <arg> has inconsistent units (...)` | The argument is complex or mixes incompatible units. | Use a real number with consistent units. |
| `Wrong number of arguments` | The wrong count of arguments. | Match the argument list in the manual page. |
| `<name> is not defined` | An argument uses an undefined name. If it is defined further along, the 'defined later' hint is added. | Define it above the call. |
| `Units do not match: result is <unit>` (e.g. `Units do not match: result is dimensionless`) | A display unit of another kind was requested, or the result is exactly zero (it then has lost its unit, for example `average_power(230 V, 10 A, pi/2) = W`). | Use a matching unit, or a bare `=` for a zero result, which shows `= 0`. |
