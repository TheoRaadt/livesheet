# 016 3-D graphing and animation — feasibility research note

**Status: research/feasibility note, requested by Theo 2026-10-30, NOT an approved spec.** Follows
the shape of docs/board/specs/012-cad-import-and-fem-research.md: no acceptance criteria, no
phase sized to the project's usual "~1-3 days" slice yet, scope still open. This is the input the
manager and Theo need before any real spec is written; nothing here should be implemented from
directly. Extends backlog M1 item 5 / spec 004 (2-D plotting) and spec 006 (plot dialog); sits
alongside backlog M3 item 13 (interactive sliders, not yet specced) without depending on it (see
section 4).

I tried to reach gui-specialist directly (SendMessage) for a second opinion on rotate/zoom/pan and
play/pause/scrub conventions, same as the task suggested; it was not reachable (same experience
spec 009/012 record for this agent). I give my own IP read on both in section 3/4 instead, flagged
explicitly rather than assumed.

---

## 1. What "3-D plot" should mean — types and vocabulary

Source: general, decades-old descriptive-geometry / scientific-visualization vocabulary, the same
category of generic concept spec 004's own "trace", "axis", "tick" vocabulary drew on; cross-
checked against Wikipedia's "Surface plot" and "Wireframe model" articles (public, general
reference, accessed 2026-10-30) for naming only, nothing copied. No vendor product's docs were
read for this section.

Three candidate 3-D plot types, in the generic vocabulary used across essentially every plotting
tool and every computer-graphics textbook (not one vendor's naming):

1. **Surface** (`z = f(x, y)`): a rectangular grid of `(x, y)` samples, each with a computed `z`;
   drawn either as a **wireframe** (just the grid lines, no fill — cheapest to draw and depth-sort)
   or a **mesh/shaded surface** (the quads between grid lines filled, optionally shaded by a simple
   face-normal-vs-light-direction brightness — classic flat shading, 1970s computer graphics, not
   tied to any one product). **Contour-on-surface** (colouring or iso-lines by `z` height) is a
   real, separate feature on top of the same grid data — recommend explicitly deferring it (see
   open question 4), the same way spec 004 deferred log axes/legends/markers into its own phase B.
2. **3-D parametric / space curve** (`x(t), y(t), z(t)` over a swept parameter `t`): the direct
   3-D generalisation of spec 004's existing "sampling mode" trace, just three expressions instead
   of one. Drawn as a connected polyline in 3-D, then projected and depth-sorted like everything
   else.
3. **3-D scatter / point cloud** (three equal-length vectors `X, Y, Z`, one point per index, no
   connectivity): the direct 3-D generalisation of spec 004's existing "vector mode". My own
   recommendation: **include it in the first slice**. Once the projection/depth-sort machinery
   exists for curves and surfaces, drawing unconnected dots instead of connected lines/faces is
   nearly free (no new projection math, no new sampling grammar beyond reusing 2-D's existing
   vector-mode option), and it is a real, common need (plotting discrete measured 3-D data, not
   just a formula).

All three share one projection/rendering pipeline (section 2) and one axis/unit/limit model
(extending spec 004's existing `nice_axis`, `xlim`/`ylim`/`xunit`/`yunit` machinery with a third,
`z`, axis — same rule, one more dimension, no new concept).

---

## 2. Renderer — the central open question

### 2.1 What was checked, and why it matters
Spec 004's own explicit, Theo-confirmed decision was QPainter directly, specifically to avoid a
new dependency and to get one drawing code path for screen, PDF (vector) and PNG. For 3-D the same
question reopens because 3-D interactive rendering is a materially bigger ask than 2-D line charts,
and because PySide6 itself ships 3-D-capable Qt modules as **optional add-on wheels** that are
easy to reach for without reading their fine print — so I checked the fine print directly, per the
task's explicit instruction not to assume.

### 2.2 QtDataVisualization / Qt Charts — checked and ruled out
Checked 2026-10-30 via PySide6-Addons' own PyPI metadata, Qt's own module source-header licence
blocks (via code.qt.io), a Qt Company forum moderator's direct statement, and Riverbank
Computing's own statement about the equivalent PyQt module (cross-checked across independent
sources, not relying on one page):
- PySide6-Addons' PyPI page gives **one blanket licence classifier for the whole wheel**
  ("LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only"), which is the licence of *most* of what's in
  that wheel, not a per-module guarantee.
- Looking at the module itself: Qt's own `qtdatavis3d` (QtDataVisualization) source-header licence
  blocks offer only a **commercial licence or GPLv3** — no LGPL option — confirmed independently by
  a Qt Company forum moderator ("Qt Charts and Qt Data Visualization are not available under
  LGPLv3. They are only available under GPLv3 or a commercial license") and by Riverbank's own
  PyQt-DataVisualization page making the identical statement about the PyQt equivalent.
- **Conclusion: QtDataVisualization (and Qt Charts) is excluded.** Shipping it under GPLv3 would
  violate CLAUDE.md's hard "no GPL/AGPL dependencies" rule outright; the only other option is a
  paid commercial Qt licence, which is not what "permissive dependency" means in this project's
  rules. This is true even though PySide6 itself (the base package LiveSheet already depends on)
  is fine under LGPL — the *specific module* QtDataVisualization is not covered by that, and the
  wheel's blanket PyPI classifier is misleading on this point if read on its own. (QtGraphs, Qt
  6.6+'s newer charting/3-D module and QtDataVisualization's eventual successor, was not checked in
  as much depth but is very likely the same GPL-or-commercial situation, being the direct successor
  to Qt Charts/QtDataVisualization — not recommended either without a further explicit check if it
  ever becomes relevant.)

### 2.3 Qt3D — checked, genuinely LGPL-available, but not recommended for this project's scale
Same checking method: Qt3D's own module source-header licence blocks (via a 2015 Qt blog post
announcing Qt 3D's licensing terms for Qt 5.5, cross-checked against a current SUSE package
licence field and a Qt mailing-list thread about a 2021 installer-metadata bug on this exact point)
confirm Qt3D genuinely ships under **LGPLv3 or GPLv2+ or commercial**, i.e. the LGPL option is real
for Qt3D specifically, unlike QtDataVisualization. It ships inside the same PySide6-Addons wheel
LiveSheet would already be pulling in it needed any add-on module, under the same dynamic-linking
LGPL terms the project already relies on for PySide6 itself — so, unlike QtDataVisualization, using
Qt3D would **not** break the no-GPL/AGPL rule.

Even so, I do **not** recommend it for this feature, for reasons specific to LiveSheet's own
architecture and scale, not a licensing objection:
- **No vector PDF path.** Qt3D (and any OpenGL-backed renderer) draws into a raster framebuffer.
  Spec 004's PDF export is explicitly vector (lines and text, not a bitmap) through the same
  `paint_plot(painter, ...)` function used on screen — a 3-D plot rendered via Qt3D would need an
  entirely separate, raster-only export path, breaking the "identical drawing on screen/PDF/image"
  property spec 004 built and that a future unified `paint_plot` would otherwise keep for 3-D too.
- **Headless-test risk.** CLAUDE.md requires the whole suite to run under
  `QT_QPA_PLATFORM=offscreen pytest -q`. A hand-rolled QPainter renderer needs nothing beyond what
  spec 004's 2-D renderer already proved works offscreen. Qt3D needs a working OpenGL context;
  under the offscreen QPA platform this can depend on the host's software-GL stack (Mesa llvmpipe
  on Linux, a different and less certain story on macOS) — a real risk of flaky or unrunnable tests
  that spec 004's approach simply does not have.
- **Scale mismatch.** Qt3D is built for real-time, large-scene 3-D applications (games, CAD
  viewports with large meshes). LiveSheet's own scale here is a small worksheet chart — a surface
  grid in the tens-by-tens, a few thousand points at most (see 2.4) — well within what a plain
  software rasteriser can do responsively; Qt3D's much larger API surface (entity-component scene
  graph, QML-adjacent concepts) would be a disproportionate amount of new code and new concepts for
  what this feature actually needs.
- Qt3D's own long-term standing inside Qt itself is not entirely settled (Qt has signalled Qt Quick
  3D as a newer direction in some contexts); not a blocking concern today, but one more reason not
  to make it the backbone of a LiveSheet feature right now.

### 2.4 Recommendation: hand-rolled QPainter 3-D projection, same precedent as spec 004
Recommend the same approach spec 004 took for 2-D, carried one dimension further: **do our own
3-D-to-2-D projection and drawing with `QPainter`, no new dependency.** All of the needed technique
is standard, decades-old computer-graphics material, not tied to any vendor or product category:
- A **camera** (viewpoint, look-at point, up vector) and a choice of **orthographic** or
  **perspective** projection matrix — textbook linear algebra (any computer-graphics course/
  textbook covers both derivations identically; this is the same category of "generic, textbook
  technique" spec 012 already used this session for Green's-theorem section properties and
  direct-stiffness-method FEM).
- **Painter's algorithm** depth sorting: sort the surface's quads (or the curve's segments, or the
  scatter's points) back-to-front by their camera-space depth and draw in that order, so nearer
  geometry correctly overdraws farther geometry — the standard, simplest correct technique for a
  single non-self-intersecting-in-a-pathological-way scene of modest size; well short of a full
  z-buffer renderer, and not needed at this scale.
- Rotating the camera is just re-applying the same rotation matrix to every vertex before
  projecting — no new per-frame cost category versus a single static render, which is what makes a
  live drag-to-rotate interaction tractable without a GPU.
- Flat shading for a mesh surface (face normal dotted with a fixed light direction, mapped to a
  brightness level within the existing 8-ish-colour-family palette spec 004 already uses) is cheap
  cross-product/dot-product arithmetic, not a new rendering concept.

**Performance at LiveSheet's scale**: recommend a default surface grid resolution in the same
spirit as spec 004's `points` default/cap (e.g. a default like 30x30 = 900 quads, a cap well under
spec 004's 10000-points-per-trace precedent — concrete numbers are an open question, section 8,
not decided here). At a few hundred to a couple of thousand quads, a Python-level sort-and-draw
pass is well within "redraws smoothly on mouse-drag" territory on ordinary hardware; this is
materially smaller than spec 004's own proven "2 traces x 1000 points under 1 second" requirement.
A generic, well-known mitigation if a future larger mesh ever becomes slow mid-drag: draw a cheaper
preview (wireframe only, or a decimated grid) while the mouse button is held, and the full
shaded mesh once it is released — a standard level-of-detail idea, not something new, and not
needed for a first slice's default sizes.

**Conclusion: recommend hand-rolled QPainter projection, no new dependency**, consistent with spec
004's own precedent and because it is the only option here that keeps the vector-PDF property, the
offscreen-testability property, and the Qt-free-engine property all unbroken at once. Qt3D is noted
as a real, licence-clean *future* option only if a later need genuinely outgrows a software
rasteriser (large, dense meshes, true real-time lighting) — not recommended now.

---

## 3. Rotate / zoom / pan interaction

### 3.1 The generic convention
Click-drag to rotate/orbit the camera around a focus point, scroll-wheel to zoom (dolly the camera
or narrow the field of view), and a modifier-held or different-button drag to pan (shift the focus
point) is the same interaction convention found identically across CAD viewports, 3-D games, generic
3-D file viewers, and every general-purpose 3-D graphics toolkit's example/demo code going back
decades — it is not particular phrasing or workflow invented by any one engineering-calculation
product; it is closer to "how a mouse operates a 3-D camera" than to any one application's design.

### 3.2 IP read, done explicitly rather than assumed
Checked explicitly against the exact concern the task raised (the same "patent-sensitive,
product-category-specific on-canvas technique" flag spec 005 hit): spec 005's rejected design was
not "interaction on a chart" in general — it was specifically *typing an expression or picking a
variable into a placeholder slot drawn live on a chart's own axes*, i.e. a data-entry technique
tied to engineering-calculation worksheets specifically (the same style flagged in
.claude/skills/mathcad-concepts' patent-risk note). Rotate/drag/zoom/pan is a different kind of
thing entirely: it never edits data or expressions, it only changes the *viewing camera* of an
already-computed picture, and it is the default manipulation convention of essentially all 3-D
software regardless of domain (a CAD viewport, a game, a generic point-cloud viewer, a 3-D chart in
a spreadsheet tool all rotate/zoom/pan the same way). My own conclusion: **plain rotate/zoom/pan on
a 3-D viewport is not the kind of worksheet-category-specific technique spec 005 hit, and does not
need the same caution** — it is squarely in the "boring, generic, decades-old cross-product
convention" category this project's IP policy treats as safe (the same category spec 009's drag-
output-to-input-terminal wiring gesture was judged to fall into, per Theo's own 2026-10-29
decision). Flagging this conclusion explicitly for the manager/Theo to confirm rather than treating
it as self-evident, as asked.

### 3.3 gui-specialist input
Attempted via SendMessage; gui-specialist was not reachable (same outcome spec 009/012 record for
this agent). Proceeding on my own IP read above; recommend the manager loop gui-specialist in
again, if reachable in a future session, specifically on the *GUI mechanics* (which mouse button
does what, cursor feedback, whether a visible on-screen gizmo/axis indicator is wanted) once this
note is far enough along to become a real spec — that is a GUI design question, not an IP one, and
does not block this research note's own conclusions.

---

## 4. Animation — what it should mean, and its relation to sliders (backlog 13)

### 4.1 Proposed meaning
**Animation = machine-driven playback over time of an existing plot (2-D or 3-D), where one
declared free parameter sweeps across a range and the plot recomputes and redraws once per frame**,
with **play / pause / scrub** transport controls (the same generic media-player convention used by
every video/audio player and every animation tool, decades old, not tied to this product category
— same IP conclusion as section 3.2's reasoning: controlling playback of an already-computed
sequence of frames is not a worksheet-specific technique). A scrub control (a slider the user can
drag to jump to an arbitrary frame while paused) looks superficially like backlog 13's "slider
bound to a variable", which is exactly why section 4.2 spells out the distinction explicitly rather
than leaving it implicit.

### 4.2 Relation to backlog 13 (sliders)
These are genuinely two different features that happen to share one underlying primitive:
- **A slider (backlog 13)** is **user-driven and instantaneous**: the user drags a widget, a named
  sheet variable's value changes immediately to whatever the slider reads, and the whole sheet
  re-evaluates once with that new value — conceptually a GUI front-end for editing an ordinary
  `:=` definition, nothing about "frames" or "time" or a declared range-to-sweep.
- **Animation** is **machine-driven playback over a pre-declared range**: a timer (e.g. a Qt
  `QTimer`) advances a frame index on its own schedule; at each tick, one parameter's value is
  computed from the current frame (same arithmetic shape as spec 004's own sampling-mode range:
  `A + k*(B-A)/(N-1)`) and the plot is rebuilt and redrawn with that value substituted in, with no
  user action required to keep it moving. The scrub control is just a way to *also* let the user
  jump the frame index directly, functioning like a slider over the frame index specifically (not
  over an arbitrary sheet variable) while playback is paused.
- **Shared primitive, not a shared feature**: both ultimately need "take one named value, override
  it for one evaluation pass, recompute, show the result" — in the engine this is the same shape of
  operation spec 004's own plot builder already does once per sampled point (build a modified
  `env` copy with one name rebound, then evaluate). Recommend that whoever eventually specs either
  feature keep this shared shape in mind (e.g. a single small "evaluate the sheet/a plot with one
  override" helper that both could call), but recommend **not** making animation depend on backlog
  13 shipping first: animation's "sweep a declared range, driven by a timer" is self-contained and
  does not need a slider widget to exist, any more than spec 004's own sampling-mode `over` needed
  one. **Animation should ship independently of sliders**, in whichever order the backlog ends up
  preferring; the two can converge later (e.g. "drive an animation's current frame from a slider
  instead of a timer" is a natural, cheap follow-up once both exist) without either blocking the
  other.

### 4.3 What the animated parameter actually is, versus a plot's existing `over`
A plot already has one swept variable (`over`, spec 004) that *is* the x-axis (2-D) or defines the
sampling grid (3-D surface). The animated parameter in a first slice should be a **second,
independent, outer-loop** variable — e.g. a plot of `sin(k*x)` where `x` is `over`'s own per-point
sweep (drawn along the axis) and `k` is a separate declared range that advances once per animation
frame (the whole curve's *shape* changes frame to frame). Recommend a new line inside the existing
plot spec text, something in the shape of `animate NAME from A to B [frames N] [fps F]` (own
keyword, same style as spec 004's `over ... from ... to ... points ...`), which:
- binds `NAME` as an ordinary scalar inside the plot's expressions for the duration of one frame
  (same "rebind one name in an `env` copy" mechanism `_slow`/`_sampling` in `plotting.py` already
  use for the x sweep, just applied once per *frame* instead of once per *x point*);
- is independent of whether the plot is 2-D or 3-D — an animated 2-D line chart and an animated 3-D
  surface use exactly the same `animate` mechanism, only the thing being redrawn differs.
This is a real design fork worth the manager/Theo's attention rather than a given — an alternative
would be a wholly separate new region/statement kind ("an animation that wraps a plot") instead of
one more line inside the existing plot spec; recommend the inside-the-plot-spec reading (keeps
today's "one region = one chart" model, avoids inventing a new region kind, and composes directly
with 3-D without a second new mechanism) but flag it explicitly as open question 6.

### 4.4 Export (image sequence / GIF)
Recommend **explicitly deferred**, not in scope for a first slice. Reasoning: an on-screen play/
pause/scrub loop needs nothing beyond what the renderer already produces per frame; a GIF or image-
sequence *file* export is a materially separate feature (GIF encoding specifically would need either
a new dependency — e.g. Pillow, itself permissively licensed [PIL/MIT-like], but still a new
dependency decision Theo has not been asked about — or a hand-rolled encoder, extra scope either
way) that does not block shipping on-screen playback at all. Flag as a clean follow-up once
playback itself exists and only if Theo wants it, the same way spec 004 deferred "export a single
plot as PNG/SVG" into its own open question/backlog extra rather than building it into phase A.

---

## 5. Sizing and recommended phase split

3-D plotting and animation are sized very differently and, per section 4.2, are not dependent on
each other — recommend treating them as **two separate tracks within backlog item 37**, each its
own sequence of specs (mirroring spec 012's own recommendation to split DXF import and FEM into
separate specs even though they were asked about together), rather than one combined spec:

**Track 1 — 3-D plotting** (bigger; recommend four phases, closer to spec 009's multi-phase shape
than to a typical single 2-day spec 004/006-style phase):
- **G1 (3-D engine core, ~2-3 days)**: extend `plotting.py`'s option/builder machinery with a third
  (`z`) axis; add surface-grid sampling (nested `x`/`y` sweep, reusing the existing per-point `env`-
  copy/measure idiom twice), 3-D parametric-curve sampling (direct extension of today's sampling
  mode to three expressions), and 3-D vector/scatter mode (direct extension of today's vector
  mode to three equal-length vectors). No rendering, no document-format change yet. Text-only
  spec, like spec 004 phase A1.
- **G2 (QPainter 3-D projection + static rendering, ~2 days)**: camera/projection matrices,
  painter's-algorithm depth sort, wireframe/shaded-mesh/curve/scatter drawing to any `QPainter`
  (screen/PDF/image, same `paint_plot`-style single function spec 004 already proved out), a fixed
  default camera angle (no interaction yet).
- **G3 (rotate/zoom/pan interaction, ~1-1.5 days)**: mouse handlers updating camera
  orientation/distance/focus and triggering a redraw; mostly GUI-side, good candidate for
  gui-specialist review of the exact mechanics once reachable (section 3.3).
- **G4 (text-spec keywords + GUI region plumbing, ~1.5-2 days)**: new plot-spec keywords for 3-D
  (surface/curve/scatter mode, z-axis unit/limit/label lines — exact wording an open question,
  section 8), wired into the existing `PlotRegion`/`Engine.evaluate` pass the same way spec 004
  phase A2 did. Recommend deferring a dialog-based 3-D configuration UI (spec 006's equivalent for
  3-D) to its *own*, later spec, mirroring the 004-then-006 sequencing precedent exactly — ship
  text-spec editing for 3-D first, a dialog later if wanted.
- Rough total: **~7-8.5 days**, bigger than this project's usual 1-3-day slice; recommend at least
  G1 and {G2+G3} as separately IP-reviewed specs, with G4 possibly folded into G2+G3's spec if the
  manager prefers fewer, larger approved specs (specialist's call deferred to whoever actually
  writes the real spec).

**Track 2 — Animation** (smaller, independent of Track 1 — recommend shipping against 2-D plots
first since it's self-contained and ships value sooner, then verifying it composes with 3-D once
Track 1 lands, rather than waiting for 3-D):
- **H1 (engine: `animate` line + per-frame evaluation, ~1.5 days)**: the `animate NAME from A to B
  [frames N] [fps F]` keyword, per-frame `env` override reusing `plotting.py`'s existing rebind
  idiom, a small `PlotAnimation`-style sequence-of-`PlotData` or a frame-index-to-`PlotData`
  callable (engine API detail for the real spec to pin down).
- **H2 (GUI: play/pause/scrub controls, live redraw, ~1.5-2 days)**: a small transport-control strip
  under/beside the plot region (generic, same chrome category as any media player, per section
  4.1), driven by a `QTimer`, calling into H1's frame evaluation and repainting via the existing
  `paint_plot` path per frame.
- Rough total: **~3-4 days**, a normal multi-phase spec size, not a 012/009-sized one.

---

## 6. Fit with today's architecture

- **Reused as-is**: `plotting.py`'s statement-recognition pattern (a text block whose first line
  names its kind), `_split_top` sub-grammar splitter, `nice_axis` (applied per-axis, unchanged —
  a z-axis needs nothing new from it), the unit-measuring/`_axis_unit`/`_limit` helpers, the
  `StatementError`/`UnitError` vocabulary, and the per-point `env`-copy-and-rebind idiom the x-sweep
  already uses (both the surface's nested x/y sweep and animation's per-frame override are the same
  idiom applied again, not a new mechanism).
- **New engine code needed, not a trivial extension**: a nested two-variable sweep for surface
  sampling (today's builder only ever rebinds one name per point); 3-D vertex/face data structures
  (`PlotTrace3D`-style: for a surface, a grid of `(x, y, z)` vertices plus the quad connectivity; for
  a curve, a polyline of 3-D points; for scatter, a flat point list) — genuinely new dataclasses,
  not a trivial reshape of today's 2-D `PlotTrace`.
- **New GUI code needed**: the projection/depth-sort/draw pipeline (section 2.4) is entirely new —
  spec 004's `plotview.py`/`paint_plot` has no 3-D concept at all today; the camera/rotation state
  and its mouse handlers are new; the animation transport strip is new.
- **`.lsheet` format**: recommend **not** a new region `kind`. A 3-D plot is still fundamentally
  "a region whose text compiles to a chart" — the same `"plot"` region kind spec 004 already
  defined, with its text's first line distinguishing 3-D (e.g. `plot3d` instead of `plot`, mirroring
  exactly how spec 004's parser already recognises `plot` by its own first line) rather than a
  parallel `kind: "plot3d"` region type needing its own GUI region class, resize handling, deletion
  rule, etc. duplicated from `PlotRegion`. This means **no `FORMAT_VERSION` bump beyond what spec
  004 already did** (version 2 is already written "when the sheet contains at least one plot
  region" — a 3-D plot is still a plot region). The one genuinely new, small, backward-compatible
  field worth adding: **persisted camera orientation/zoom** (e.g. `rx`, `ry`, `zoom` numeric fields
  on the region, present only for a 3-D plot, defaulting to a fixed starting view when absent) —
  recommend persisting this, mirroring exactly how spec 004 added `w`/`h` only for plot regions,
  because a user who spent time orienting a 3-D view would reasonably expect it saved with the
  sheet. Animation's current frame/playing-or-paused state is explicitly **not** persisted (matches
  spec 004's "plot results are never stored, recomputed on load" principle) — reopening a saved
  sheet with an animated plot shows frame 0, paused.
- **Engine stays Qt-free**: the 3-D projection/depth-sort/draw code lives in `livesheet/gui/`
  (likely a new `plotview3d.py` or an extended `plotview.py`), exactly mirroring where spec 004 put
  `paint_plot` — `plotting.py` only ever produces display-unit numbers and 3-D vertex/face data, it
  never computes a projection or knows about a camera.

---

## 7. IP check (overall, for this note)

Pass, with the open questions below flagged rather than silently resolved, mirroring spec 012's own
framing. No vendor name, icon, file-format, or 1:1 keyword set is proposed anywhere above. The
vocabulary used (surface/wireframe/mesh/space curve/scatter/point cloud) is generic, decades-old,
cross-product scientific-visualization terminology, not any one vendor's feature naming. The
renderer recommendation (hand-rolled QPainter projection, perspective/orthographic matrices,
painter's-algorithm depth sort, flat shading) is standard, textbook computer-graphics technique,
the same category of "generic, well-established method" spec 012 already used this session for
Green's-theorem section properties and the direct-stiffness FEM method — not patented, not tied to
any engineering-calculation product. Section 2's licence findings (QtDataVisualization excluded as
GPL-or-commercial-only; Qt3D genuinely LGPL-available but not recommended for architecture reasons)
were checked directly against Qt's own module licence headers and independent forum/vendor
statements, not assumed from the misleading blanket PyPI wheel classifier — consistent with the
task's explicit instruction to verify rather than assume. Section 3's IP read (plain rotate/zoom/pan
is not the kind of worksheet-category-specific technique spec 005 hit) is my own assessment, flagged
explicitly for the manager/Theo to confirm rather than treated as self-evident, per the task's
instruction. No part of this note proposes an on-canvas data-entry technique of the kind spec 005
was rejected for; animation's playback controls and 3-D's camera controls only ever change *how an
already-computed result is viewed*, never how data or expressions are entered. Not legal advice.

---

## 8. Open questions for the manager

1. **Renderer** (section 2): confirm hand-rolled QPainter 3-D projection (recommended) over Qt3D
   (licence-clean but raster-only/heavier/offscreen-test risk, not recommended now) and over
   QtDataVisualization (excluded outright — GPL-or-commercial-only per the module's own licence,
   not the blanket wheel classifier). No new non-Qt dependency is recommended or seen as needed.
2. **3-D scatter in the first slice** (section 1): include (recommended — cheap once curve/mesh
   projection exists) or defer to a later phase?
3. **Default/max mesh resolution** (section 2.4): no concrete numbers proposed yet (unlike spec
   004's own `nice_axis`/101-points/400x260 defaults, which were concrete); recommend a
   mathcad-specialist/developer pass once this becomes a real spec, picking numbers with the same
   "default modest, cap well short of trouble" shape as spec 004's `points`/`MAX_TRACES`.
4. **Contour-on-surface** (section 1): explicitly deferred to a later phase (recommended, mirrors
   spec 004's own phase-A/phase-B split) — confirm.
5. **3-D keyword set**: proposing, tentatively, `plot3d` as the plot-spec's first line (distinguishing
   a 3-D plot the same way `plot`'s own first line is recognised today), plus z-axis equivalents of
   today's `xunit`/`xlim`/`xlabel` (`zunit`/`zlim`/`zlabel`), and a `mode` word choosing
   surface/curve/scatter (reusing spec 004 phase B2's existing `mode` keyword shape rather than
   inventing a new one) — needs the same pre-1.0 notation review pass every other spec's keywords
   have gone through; not finalised here.
6. **Animation keyword and scope** (section 4.3): proposing `animate NAME from A to B [frames N]
   [fps F]` as one more line inside the existing plot spec (recommended — keeps "one region = one
   chart", composes directly with both 2-D and 3-D) rather than a new wrapping region/statement
   kind. This is a genuine design fork, not a given; please confirm the inside-the-plot-spec
   reading or redirect.
7. **GIF/image-sequence export** (section 4.4): explicitly deferred for the first slice (recommend);
   confirm, and confirm whether Pillow (MIT-adjacent PIL licence, permissive) would even be an
   acceptable new dependency if/when this is revisited, or whether a hand-rolled encoder is
   preferred to avoid the question entirely.
8. **Camera-state persistence** (section 6): recommend persisting a 3-D plot's last rotation/zoom as
   new optional region fields (mirroring `w`/`h`'s precedent), defaulting to a fixed starting view
   when absent; confirm.
9. **Phase split and sequencing** (section 5): confirm treating 3-D plotting (4 phases, ~7-8.5 days,
   likely 2+ separately-IP-reviewed specs) and animation (2 phases, ~3-4 days, one spec, 2-D first)
   as two independent tracks within backlog item 37, rather than one combined spec — and confirm
   whether Theo wants animation sequenced before or after 3-D plotting (they do not block each
   other technically, per section 4.2, so this is purely a priority call).
10. **gui-specialist review of rotate/zoom/pan mechanics** (section 3.3): not reachable this
    session (same outcome as spec 009/012); recommend the manager loop them in on the *GUI design*
    specifics (button/modifier mapping, any on-screen orientation gizmo) once this note is far
    enough along to become a real spec — my own IP read on the *category* of interaction
    (section 3.2) does not depend on their input and is not blocked by this.

---

## Sources consulted
- Wikipedia, "Surface plot" and "Wireframe model" (general reference, vocabulary/naming check
  only, accessed 2026-10-30).
- PySide6-Addons' own PyPI page (module list and blanket wheel licence classifier, accessed
  2026-10-30).
- Qt's own `qtdatavis3d` source-header licence blocks (via code.qt.io), a Qt Company forum
  moderator's direct statement on QtDataVisualization/Qt Charts licensing, and Riverbank
  Computing's equivalent statement about PyQt-DataVisualization (all accessed 2026-10-30,
  cross-checked against each other) — QtDataVisualization licensing.
- A 2015 Qt company blog post announcing Qt 3D's Qt 5.5 licensing terms, a current SUSE package
  licence field, and a 2021 Qt mailing-list thread about an installer-metadata bug on this exact
  point (all accessed 2026-10-30, cross-checked against each other) — Qt3D licensing.
- docs/board/specs/004-plots.md, 005-plot-placeholders.md, 006-plot-dialog.md, 009-component-
  wiring-core.md, 012-cad-import-and-fem-research.md, and docs/board/decisions.md (this project's
  own prior art and precedent, not external sources).
- No vendor engineering-calculation product's documentation, UI, workflow, or branding was read
  for this note.
