---
name: modeling-concepts
description: Conceptual map of generic, long-public-domain visual modeling/dataflow ideas (block diagrams, signal-flow graphs, spreadsheet dependency graphs, pipe-and-filter architecture) for LiveSheet's component-and-wiring feature. Use when writing specs for placing components on the sheet and wiring them together.
---
# Visual modeling / wiring concepts (generic, public-domain ideas only)

Use as a checklist of IDEAS, decades old and common to many fields (electrical
engineering, control theory, software architecture, spreadsheets), never traced
to one named commercial dataflow/wiring product. See decisions.md 2026-10-29:
Theo chose this generic-concepts route specifically so this feature needs no
new vendor entry in docs/IP-POLICY.md.

- Block diagram / signal-flow graph (control theory, long public domain):
  named boxes with input/output terminals, connected by directed lines; a
  box's output depends only on its own inputs, not on diagram position.
- Pipe-and-filter architecture (classic software-architecture pattern): each
  component is a small transform from input(s) to output(s); wiring is just
  composition, order of connection doesn't matter, only the dependency graph.
- Spreadsheet dependency graph (the idea underlying any spreadsheet, long
  public domain): a cell/component recomputes when something it depends on
  changes; cycles are detected and rejected, not silently looped.
- Component types as plain data sources/transforms, not a fixed vendor taxonomy:
  a file reader (CSV/other open tabular format), a nested sub-sheet (another
  .lsheet used as a reusable block with its own named inputs/outputs), a
  user-script transform (small input-to-output function, sandboxed — see
  decisions.md: QJSEngine, no filesystem/network access by default).
- Ports: named, typed-by-convention input/output points on a component, each
  wire connects exactly one output port to one input port; an unconnected
  required input is a visible error state on the component, not a silent
  default.
- Evaluation order: a topological sort of the wiring graph (compute a
  component only after everything it depends on), analogous to how the sheet
  already evaluates top-to-bottom/left-to-right today — this feature needs its
  own ordering rule since position on canvas no longer implies dependency
  order once wires exist.
- Visual conventions common across many unrelated diagramming tools (flowchart
  editors, circuit-diagram tools, generic node-graph editors): drag from an
  output port to an input port to create a wire; a wire highlights or shows an
  error color when types/units mismatch; deleting a component removes its
  wires; a component can be collapsed to show just its ports.

Sources: general, public-domain concepts from control theory, software
architecture and spreadsheet design (textbook-level ideas, not implementation
screenshots). No named commercial node-based/dataflow/wiring product's specific
layout, icon set, port-shape convention, color coding or wiring-gesture was
read or used as a source — see decisions.md for why that route was deliberately
avoided. Check every resulting spec against docs/IP-POLICY.md (see
ip-cleanroom); flag anything that starts to look distinctive to one product
rather than generic across the field.
