<!-- Modified-by: FreeANDIY (Free Andy Agency), 2026. Replaces upstream WordCraft's README. -->
<p align="center">
  <img src="assets/app-icon/freeandiy-write-1024.png" width="128" alt="FreeANDIY Write icon">
</p>

<h1 align="center">FreeANDIY Write</h1>

<p align="center">
  <b>A free, open-source word processor. Native Rust, runs on macOS, Windows, Linux and in the browser.</b><br>
  Part of <a href="https://freeandiy.freeandy.agency">FreeANDIY</a>, free creative and office apps by Free Andy Agency.
</p>

---

## About

FreeANDIY Write is a word processor with a ribbon interface: styles, tables, pictures, shapes,
references and citations, review and track changes, mail merge, and DOCX, ODT, RTF, PDF and
Markdown import and export. It is a native egui app (no webview), and the web version is the same
Rust code compiled to WebAssembly.

Every action is a command, so the app can be driven from a CLI (`freeandiy-write-cli`), a JSON
control channel or an MCP server.

**FreeANDIY Write is based on the open-source project
[WordCraft](https://github.com/storytold/wordcraft) (© ArtCraft Team and contributors,
MIT/Apache-2.0). FreeANDIY is not affiliated with the ArtCraft team.** The editor itself is their
work; FreeANDIY adds its own branding, packaging and translations, and follows upstream closely.

## Download

Builds for macOS, Windows and Linux are published on the
[Releases](https://github.com/FreeAndy21/freeandiy-write/releases) page as
`freeandiy-write-<version>-<os>-<arch>.*`.

## Build from source

Requires Rust (see `rust-version` in `Cargo.toml`).

```sh
cargo run --release -p wordcraft                         # desktop app (binary: freeandiy-write)
cargo run --release -p wordcraft-cli -- --help           # CLI (binary: freeandiy-write-cli)
cd apps/wordcraft-web && trunk build --release           # web build (WebAssembly)
```

The crate names keep upstream's `wordcraft-*`, so upstream changes merge cleanly. The developer documentation in `docs/` is
upstream's and still says WordCraft.

## How this fork is made

Everything FreeANDIY changes lives in [`freeandiy/`](freeandiy/): the brand definition
(`branding.toml`, `app.toml`), assets, a handful of small patches and text rules. All other files
are regenerated from upstream WordCraft by `freeandiy/scripts/regenerate.sh`, so updates from
upstream never conflict. See [`freeandiy/docs/upstream-sync.md`](freeandiy/docs/upstream-sync.md).

Issues with FreeANDIY builds go to
[our tracker](https://github.com/FreeAndy21/freeandiy-write/issues), not to upstream.

## License

The code is licensed, like upstream, under either of [MIT](LICENSE-MIT) or
[Apache-2.0](LICENSE-APACHE) at your option. See [`NOTICE`](NOTICE) and [`ATTRIBUTION.md`](ATTRIBUTION.md)
for third-party material.

The FreeANDIY and Free Andy Agency names, the angel Andy, logos and app icons are © Free Andy
Agency and **not** covered by the code license; see
[`freeandiy/assets/brand/LICENSE-brand.txt`](freeandiy/assets/brand/LICENSE-brand.txt).

<sub>Microsoft and Word are trademarks or registered trademarks of Microsoft Corporation in the United
States and/or other countries. FreeANDIY Write is an independent, open-source project and is not
affiliated with, sponsored by or endorsed by Microsoft Corporation; these names are used only to describe the
workflows it is compatible with.</sub>
