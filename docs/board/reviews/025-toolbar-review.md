# Review: spec 025 larger Standard toolbar

Tests: tests/test_spec025_review.py (34 tests, black-box from the spec; offscreen). Result: 34 passed;
developer file tests/test_toolbar_025.py: 9 passed. No defects found against criteria 1-10.

## Coverage
- Icons non-null for all 5 actions; icon edge rule (20 default, grows with font, 20..32 even); 19 px font case.
- Button sizeHint height >= 32 and >= tab height + 4; taller than every band QPushButton.
- Width 1000: TextBesideIcon, buttons inside toolbar rect, no extension button. Width 480: IconOnly, all visible,
  tooltips "Export PDF (...)" / "Recalculate (F9)", accessible names = plain labels (both styles).
- Hysteresis: exactly one flip down and one flip up over a sweep around the threshold; back to wide only at >= sum+24
  (`toolbar_styler.wide_width` used as the threshold; sanity-checked to be 250..900, spec says ~520).
- Min width: minimumSizeHint identical with toolbar shown vs hidden; no overlapping buttons at the smallest width.
- Same QAction objects and order/separators; real mouse click on Recalculate fires the action; icons hidden in menus.
- Movable / not floatable / object name / View toggle text unchanged. Left dock -> IconOnly, back to top -> wide.
  Hide/show recomputes style.
- Icons: 40x40 at DPR 2, DPR 1/1.5/3 sizes, non-blank, five glyphs pairwise different; light vs dark palette gives
  dark vs light dominant colour; Disabled mode uses the Disabled ButtonText colour.
- Settings isolation: module fixture switches QSettings to INI in a temp dir and asserts
  ~/Library/Preferences/com.livesheet.LiveSheet.plist is byte-identical before/after (passes). The plist did change
  during the session, but only when other agents' suites ran (md5 unchanged across my runs and the developer's file).

## Gaps / notes
- Not tested: real move between 1x/2x screens, runtime QApplication font change signal (only font set before window
  creation), extension ("more") menu contents (never shown at the smallest window width here: the window minimum
  was wide enough), real focus-ring rendering, pixel look of the glyphs.
- tests/test_toolbar_025.py (developer) does not isolate QSettings; it re-docks the toolbar on teardown which avoids
  persisting a bad layout, but MainWindow.close() still writes to the real settings. Recommend an autouse fixture.
- GUI run: no computer-use tools were available to this agent, so the real app was NOT launched. Needs a manual
  look by the manager/Theo (wide vs icon-only, dark mode, left dock).

## Environment finding (not a product defect)
Files under .venv have the macOS "hidden" flag (ls -lO shows `hidden`). Qt's plugin loader then sees an empty
platforms dir and aborts ("Could not find the Qt platform plugin offscreen in ''"), and the editable install .pth
is skipped ("No module named livesheet"). Plain `pytest` therefore crashes here. Workaround used (no repo change):
copy plugins to a scratch dir (cp drops the flag) and set QT_PLUGIN_PATH, QT_QPA_PLATFORM_PLUGIN_PATH, PYTHONPATH.
Permanent fix: `chflags -R nohidden .venv`.

## Full suite (with the workaround)
2639 passed, 10 xfailed, 5 failed, none in 025:
- spec 026 transients (sidepanel placeholder tabs now have buttons): test_spec011_side_panel_greek_blackbox
  criterion6 [Statistics], [Optimization]; test_spec022_tab_strip_review test_c15_placeholder_pages[3], [4].
  Expected to need updating when 026 lands.
- tests/test_spec023_review.py::test_open_hand_on_hover_arrow_on_empty_canvas: Arrow cursor instead of OpenHand
  in the full run (spec 023 area, not toolbar; could be order dependent; reported only).

## IP check
icons.py is original: QPainter lines, rects, polygons, one arc on a 20x20 grid; no files, no theme icons, no raster
loading (guarded by a test). Save glyph = notched square + shutter rect + filled label rect: generic, no tracing
evident. No vendor names/strings. Pass.
