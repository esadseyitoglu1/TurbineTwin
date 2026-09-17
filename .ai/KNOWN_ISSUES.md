# TurbineTwin — Known Issues

- **`README.md` "Status" section is stale.** Still reads "Phase 1-4
  complete"; Phase 5 (MCP server) shipped in commit `389cf8e` but the
  README was never updated. Cosmetic, but misleading to an external
  reviewer skimming only the README. See NEXT.md.

- **Windows console can garble Turkish characters in printed output**
  (e.g. `"M. Aydın"` displayed as `"M. Ayd?n"` in a terminal). Confirmed
  via `ord(c)` that the underlying character is correctly `U+0131` and the
  JSON is valid UTF-8 — this is purely a Windows console code-page display
  limitation, not a data or API bug. Renders correctly in a browser.

- **`/api/stream?speed=100` measures closer to ~54x in practice**, not a
  true 100x, due to Windows timer resolution limits on `asyncio.sleep`
  with very small intervals. Documented, not fixed (acceptable for a
  dashboard demo; would matter for anything timing-sensitive).

- **Historical (resolved) finding, kept for context:** `uvicorn.exe` was
  once reported missing from PATH despite `import uvicorn` working from
  Python directly. Worked around by invoking uvicorn as a module. If this
  resurfaces, check the venv's `Scripts/` directory against `pip show uvicorn`.
