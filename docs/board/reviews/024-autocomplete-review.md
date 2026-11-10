# Review: spec 024 function autocomplete (tester, 2026-11-10)

Tests: tests/test_spec024_review.py (76 tests: 72 pass, 4 strict xfail). Full suite: 2894 passed, 1 skipped, 14 xfailed.
Environment note: `.venv` files carried the macOS `hidden` flag again, so Qt could not load any platform plugin
(every GUI test aborted at QApplication). Fixed locally with `chflags -R nohidden .venv`; the flag comes back whenever
the venv is rebuilt.

## Defects

### D1 (high): Tab never accepts a completion in the real app
`QGraphicsTextItem.sceneEvent` hands Tab/Backtab straight to the text control when `tabChangesFocus` is False, so
the key never reaches `_Editor.keyPressEvent` / `handle_key`. The developer tests call `keyPressEvent` directly and
therefore miss it. `focusNextPrevChild` is not the problem.
Repro (offscreen): add a math region, start editing, type `me` (popup open), then
`scene.sendEvent(region.editor, QKeyEvent(KeyPress, Key_Tab, NoModifier, "\t"))`.
Expected `mean(` (spec G2). Actual `me\t` and the popup closes. Same through `QTest.keyClick(view.viewport(), Key_Tab)`.
Down/Esc through scene events work. Suggested fix: override `sceneEvent` in `_Editor` to route Tab/Backtab to `keyPressEvent`
(or when `popup_open`). Tests: `test_real_tab_through_view`, `test_real_typed_keys_through_view`,
`test_scene_sendevent_tab_accepts` (strict xfail; remove marker once fixed).

### D2 (medium): tests/conftest.py does not isolate MainWindow's QSettings
`QSettings("LiveSheet", "LiveSheet")` (main_window.py:119) uses the native format regardless of
`setDefaultFormat`, so it still points at `~/Library/Preferences/com.livesheet.LiveSheet.plist`. Observed: after a full
suite run `defaults read com.livesheet.LiveSheet recent` lists the new pytest-NNN temp paths
(test_editing_spec_live_update, test_save_open_roundtrip). The fixture only protects bare `QSettings()`.
Fix idea: tests patch `MainWindow.settings`/monkeypatch `QSettings` ctor, or MainWindow takes a settings factory.
Test: `test_mainwindow_settings_isolated` (strict xfail).
(My own probe briefly wrote one key to the real plist; I removed it with `defaults delete`.)

## Spec inconsistencies / notes (not defects)
- E3 says `complete("Int", 3)` is None, but case-insensitive matching rightly offers `integrate`. Spec text should say
  `Integer` is absent. Same as the developer's deviation.
- Esc then Backspace below 2 chars then retyping reopens the popup (the word ended). Spec "closed for the rest of that
  word" is ambiguous here; accepted.
- No 2-letter prefix has more than 6 builtin matches, so the 8-row scroll window is only reachable with user names;
  PageUp/Down and scroll-follow tested with 20 user variables and pass.
- G13 painting check is weak (offscreen pixel comparison); printing guard was read in code, not proven by pixels.

## Passed (black box)
E1-E12 (registry-driven, stats/matrix present, exclusions, ranking incl. max before Max, hints and drift, numbers,
min length, mid-word, exact name, accept variants, user names incl. defined-below, global/malformed, user before builtin,
case-insensitivity, unicode, out-of-range caret, no PySide6 import). GUI: open/refresh on type/Backspace/Delete,
Down/Up wrap, PageUp/Down, Esc, Enter commits (also after navigation), programmatic insert and insert_token and Greek
shortcut action never open/close it, Greek words silent, Gam->Gamma(, pretty output equals hand-typed, closers
( space + , . :, Left/Right/Home/End, leave edit, delete region, region switch, click other region, mid-word, number context,
Text region, mouse row pick keeps editing, zoom, placement inside viewport, 150 regions typing < 1.5 s, drag-move (023)
still works with a popup open elsewhere, popup item not left in scene.

## Real-app GUI check
Not done: no computer-use tools were available in this session. Tab on macOS is covered only by the offscreen
real-event repro above, which already fails (D1); a native check should repeat it after the fix.

## IP
No red flags: names come from the registry, hints are own wording, popup is generic list chrome.
