<!-- Modified-by: FreeANDIY (Free Andy Agency), 2026. New file, not part of upstream WordCraft. -->
# FreeANDIY Write: changes from upstream WordCraft

This file lists what the FreeANDIY fork changes in WordCraft (Apache-2.0 section 4(b)). The
exact changes are generated from `freeandiy/` (see `NOTICE`); `git diff upstream-main main`
shows every changed file.

## Unreleased

### Branding
- Product name **FreeANDIY Write** everywhere users see it: window title, ribbon, About, messages,
  all bundled translations, installers, desktop entries, the web page, the MCP server.
- Application id `agency.freeandy.write` (was `ai.storyteller.wordcraft`), so FreeANDIY builds
  install next to WordCraft.
- Executables `freeandiy-write` and `freeandiy-write-cli`; the cargo packages keep their names.
- New app icon set (the angel Andy, Free Andy Agency) and DMG background.
- Light and dark themes in FreeANDIY's paper-and-ink print look (no soft shadows, the stamp-rose
  accent); the area behind pages and the documents' own colours are unchanged.
- UI font IBM Plex Sans (OFL 1.1) on the desktop.

### Removed
- The ArtCraft name, wordmark and logos (`docs/brand/`), as their terms require of forks.
- The ArtCraft Discord button and links (title bar, ribbon Help tab, Backstage, key tips, About,
  the MCP server's instructions) and its Options switch.
- Upstream's release and platform workflows.

### Added
- About: attribution to upstream WordCraft and the Free Andy Agency seal; links to the FreeANDIY
  page and this repository.
- Slovak user interface (ribbon tabs and groups; the rest falls back to English for now).
- `NOTICE` section and `ATTRIBUTION.md` rows for FreeANDIY's assets and fonts; packages now ship
  `NOTICE`, `ATTRIBUTION.md`, the font licences and the brand terms.
