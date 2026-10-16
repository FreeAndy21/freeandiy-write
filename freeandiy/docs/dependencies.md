<!-- Modified-by: FreeANDIY (Free Andy Agency), 2026. New file, not part of upstream. Shared by all FreeANDIY apps. -->
# Upstream's git dependencies

Upstream's `Cargo.toml` files pin a few crates by git commit on github.com/storytold. We leave
those lines as upstream wrote them (so syncs stay conflict-free) and fetch the same commits from
our mirrors instead. The FreeANDIY workflows set this up with git `insteadOf` rules (the `env:` block
at the top of `.github/workflows/freeandiy*.yml`); any other storytold URL fails the build.

| Upstream URL | Mirror on FreeAndy21 | Licence | Used by |
|---|---|---|---|
| storytold/craft-libs | freeandiy-craft-libs (fork) | MIT OR Apache-2.0 | most apps (craft-ui, craft-print) |
| storytold/winprint.rs | freeandiy-winprint (fork) | BSD-3-Clause; gdi crate MIT OR Apache-2.0 | craft-print, PDF |
| storytold/pdfcraft | freeandiy-pdf | MIT OR Apache-2.0 | Layout (hayro) |
| storytold/filmcraft | freeandiy-film | MIT OR Apache-2.0 | Effects (codecs) |

To build locally the same way (otherwise cargo fetches from storytold):

```sh
export CARGO_NET_GIT_FETCH_WITH_CLI=true
git config --global url.https://github.com/FreeAndy21/freeandiy-craft-libs.insteadOf https://github.com/storytold/craft-libs
git config --global url.https://github.com/FreeAndy21/freeandiy-winprint.insteadOf https://github.com/storytold/winprint.rs
git config --global url.https://github.com/FreeAndy21/freeandiy-pdf.insteadOf https://github.com/storytold/pdfcraft
git config --global url.https://github.com/FreeAndy21/freeandiy-film.insteadOf https://github.com/storytold/filmcraft
```

## After an upstream sync

A pinned commit must be reachable from a branch or tag of the mirror:

```sh
gh repo sync FreeAndy21/freeandiy-craft-libs     # forks: bring main up to date
gh repo sync FreeAndy21/freeandiy-winprint
grep -ho 'git+https://github.com/storytold/[^"]*' Cargo.lock | sort -u   # what is pinned now
```

For a commit that only exists on an upstream side branch (as Effects' filmcraft pin did), push it
to the mirror as a tag: `git push origin <sha>:refs/tags/deps/<app>-<repo>-<short sha>`.
A new storytold repository in that list needs a new mirror and a new `insteadOf` pair in both
workflows (and here).
