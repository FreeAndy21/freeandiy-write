<!-- Modified-by: FreeANDIY (Free Andy Agency), 2026. New file, not part of upstream. Shared by all FreeANDIY apps. -->
# Keeping a FreeANDIY app in sync with its upstream

## The model

| Branch / place | What it is |
|---|---|
| `upstream` remote | the `upstream` repository of this app in `freeandiy/branding.toml` |
| `upstream-main` | a mirror of upstream's default branch, never edited |
| `main` | the product: `upstream-main` + everything in `freeandiy/`, applied by the rebrand |
| `freeandiy/` | **the only place we edit**: brand, assets, patches, rules, scripts, our docs |

Every file outside `freeandiy/` on `main` is **generated**:
`freeandiy/scripts/regenerate.sh` checks out pristine upstream in a temporary worktree, copies
`freeandiy/` into it, runs `freeandiy/tools/rebrand` (`apply`) and commits the result onto `main`.
When the upstream commit is new, that commit is a merge with upstream as second parent, so
history shows which upstream each build contains. Upstream changes therefore never conflict
with ours, and nothing is ever force-pushed. CI runs `regenerate.sh --check` to catch hand edits.

## Routine sync

```sh
git checkout main && git pull
freeandiy/scripts/sync-upstream.sh            # fetch, regenerate, check branding, build, test
freeandiy/scripts/sync-upstream.sh --push     # same, then push upstream-main and main
```

## When the rebrand stops

`rebrand apply` fails loudly instead of shipping half a rebrand. The message names the problem:

- **`patch 000N-....patch no longer applies`**: upstream changed lines one of our patches edits.
  Refresh it:
  ```sh
  git worktree add --detach ../fa-work upstream-main       # pristine upstream (--detach: never check the branch out)
  cd ../fa-work && git apply --3way ../<this repo>/freeandiy/patches/000N-*.patch
  # resolve the conflicts by hand, then:
  git diff -- <the patch's files> > ../<this repo>/freeandiy/patches/000N-....patch
  ```
- **`replace "...": N match(es), expected at least M`**: upstream renamed or removed text a rule
  looks for. Find where it went (`git log -S'<text>' upstream-main`), then fix the rule's
  `find`/`regex` or `include`, or lower `min` if the text is really gone.
- **`delete: <path> does not exist upstream any more`**: drop it from `delete`.

Commit the fix in `freeandiy/` (`brand: ...`) and run the sync again.

If `Cargo.lock` now pins a different commit of a storytold git dependency, update the mirror
first (see `dependencies.md`), or the build fails fetching it.

After a sync, also skim `git diff <old main> main` for new user-visible text containing
the upstream app name or links to ArtCraft services; `check-branding.sh` catches the known patterns.

## Changing the branding

1. Edit `freeandiy/` (e.g. `branding.toml`, a template, a rule, a patch). New code changes go in
   a patch made against pristine upstream, as above; keep patches small and grouped by topic.
2. `git commit -m "brand: ..."`, then `freeandiy/scripts/regenerate.sh` (commits the result).
3. `freeandiy/scripts/check-branding.sh`, build and test.

Shared files (branding.toml, scripts/, tools/, docs/, brand assets, icons, the workflows) come
from the meta repository FreeAndy21/freeandiy (`scripts/sync-common.sh` there): change them
there, not here. DMG background: `freeandiy/tools/make_dmg.py`, output in `freeandiy/assets/dmg/`.
