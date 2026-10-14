// Modified-by: FreeANDIY (Free Andy Agency), 2026. New file, not part of upstream.
//! Apply the FreeANDIY branding to a pristine upstream checkout.
//!
//!     cargo run --manifest-path freeandiy/tools/rebrand/Cargo.toml -- apply [ROOT]
//!     cargo run --manifest-path freeandiy/tools/rebrand/Cargo.toml -- vars [ROOT]
//!
//! ROOT (default: the current directory) must be an upstream tree plus our `freeandiy/`
//! directory, with nothing else changed: `apply` is not idempotent on its own output. Use
//! `freeandiy/scripts/regenerate.sh`, which builds that tree in a temporary worktree.
//!
//! Steps, in order (all driven by `freeandiy/rules.toml`, values from `freeandiy/branding.toml`):
//!   1. delete      remove upstream paths (files or directories)
//!   2. patches     `git apply` every `freeandiy/patches/*.patch`, sorted by name
//!   3. drop_lines  delete lines matching a regex
//!   4. replace     literal or regex text replacements, each with a minimum match count so
//!                  upstream drift fails loudly instead of silently leaving the old brand
//!   5. rename      rename files (path substring replacement)
//!   6. copy        copy our files (icons, overlay) into the tree
//!   7. templates   render `{{key}}` placeholders in the copied files listed as templates
//!
//! `{{key}}` placeholders work in every string of rules.toml. `vars` prints the known keys.

use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

use anyhow::{Context, Result, anyhow, bail};
use globset::{Glob, GlobSet, GlobSetBuilder};
use regex::Regex;
use serde::Deserialize;

#[derive(Deserialize, Default)]
#[serde(deny_unknown_fields)]
struct Rules {
    #[serde(default)]
    delete: Vec<String>,
    #[serde(default)]
    drop_lines: Vec<DropLines>,
    #[serde(default)]
    replace: Vec<Replace>,
    #[serde(default)]
    rename: Vec<Rename>,
    #[serde(default)]
    copy: Vec<Copy>,
    #[serde(default)]
    templates: Vec<String>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct DropLines {
    include: Vec<String>,
    #[serde(default)]
    exclude: Vec<String>,
    regex: String,
    #[serde(default)]
    min: usize,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Replace {
    /// Short description, shown in errors and the summary.
    name: String,
    include: Vec<String>,
    #[serde(default)]
    exclude: Vec<String>,
    /// Literal text to find (exactly one of `find` / `regex`).
    find: Option<String>,
    regex: Option<String>,
    replace: String,
    /// Fail when fewer matches than this are found (0 = optional rule).
    #[serde(default = "one")]
    min: usize,
    /// Leave lines alone whose first non-blank text starts with one of these (e.g. "//"), so
    /// code comments keep describing upstream's work truthfully.
    #[serde(default)]
    skip_comments: Vec<String>,
}

fn one() -> usize {
    1
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Rename {
    include: Vec<String>,
    find: String,
    replace: String,
    #[serde(default = "one")]
    min: usize,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Copy {
    /// File or directory, relative to the root.
    from: String,
    to: String,
}

/// Flatten branding.toml (shared by every FreeANDIY repository) and app.toml (this repository:
/// `app = "<id>"` and its build settings) into `section.key` strings, plus derived values.
fn variables(root: &Path) -> Result<BTreeMap<String, String>> {
    let mut vars = BTreeMap::new();
    for name in ["branding.toml", "app.toml"] {
        let path = root.join("freeandiy").join(name);
        if name == "app.toml" && !path.exists() {
            continue;
        }
        let text = fs::read_to_string(&path).with_context(|| format!("reading {}", path.display()))?;
        let doc: toml::Table = text.parse().with_context(|| format!("parsing {}", path.display()))?;
        flatten(&doc, &mut vars);
    }
    finish_variables(vars)
}

fn flatten(doc: &toml::Table, vars: &mut BTreeMap<String, String>) {
    fn walk(prefix: &str, t: &toml::Table, out: &mut BTreeMap<String, String>) {
        for (k, v) in t {
            let key = if prefix.is_empty() { k.clone() } else { format!("{prefix}.{k}") };
            match v {
                toml::Value::Table(sub) => walk(&key, sub, out),
                toml::Value::String(s) => {
                    out.insert(key, s.clone());
                }
                other => {
                    out.insert(key, other.to_string());
                }
            }
        }
    }
    walk("", doc, vars);
}

fn finish_variables(mut vars: BTreeMap<String, String>) -> Result<BTreeMap<String, String>> {
    let app = vars.get("app").cloned().ok_or_else(|| anyhow!("app.toml: missing `app`"))?;
    // `this.*` = the [apps.<app>] entry of this repository.
    let this: Vec<(String, String)> = vars
        .iter()
        .filter_map(|(k, v)| k.strip_prefix(&format!("apps.{app}.")).map(|rest| (format!("this.{rest}"), v.clone())))
        .collect();
    if this.is_empty() {
        bail!("branding.toml: no [apps.{app}] section");
    }
    vars.extend(this);
    let get = |k: &str| vars.get(k).cloned().ok_or_else(|| anyhow!("branding.toml: missing {k}"));
    let prefix = get("brand.id_prefix")?;
    let owner = get("brand.github_owner")?;
    let repo = get("this.repo")?;
    let website = get("brand.website")?;
    // `this.upstream_slug` = upstream's repository (and crate/binary) name, e.g. "photocraft".
    let upstream = get("this.upstream")?;
    let slug = upstream.rsplit('/').next().unwrap_or(&upstream).to_string();
    vars.insert("this.upstream_slug".into(), slug);
    vars.insert("this.key".into(), app.clone());
    vars.insert("this.app_id".into(), format!("{prefix}.{app}"));
    vars.insert("this.github".into(), format!("https://github.com/{owner}/{repo}"));
    vars.insert("this.issues".into(), format!("https://github.com/{owner}/{repo}/issues"));
    vars.insert("this.releases".into(), format!("https://github.com/{owner}/{repo}/releases"));
    vars.insert("this.page".into(), format!("{}/{app}", website.trim_end_matches('/')));
    // `rgb.<colour>` = "r, g, b" for Color32::from_rgb; `rgba.<colour>` for 8-digit colours.
    let colours: Vec<(String, String)> = vars.iter().filter_map(|(k, v)| k.strip_prefix("colors.").map(|c| (c.to_string(), v.clone()))).collect();
    for (name, hex) in colours {
        let h = hex.trim_start_matches('#');
        let byte = |i: usize| u8::from_str_radix(h.get(i..i + 2).unwrap_or("00"), 16);
        let (r, g, b) = (byte(0)?, byte(2)?, byte(4)?);
        vars.insert(format!("rgb.{name}"), format!("{r}, {g}, {b}"));
        let a = if h.len() == 8 { byte(6)? } else { 255 };
        vars.insert(format!("rgba.{name}"), format!("{r}, {g}, {b}, {a}"));
    }
    Ok(vars)
}

/// Replace `{{key}}` with its value; unknown keys are an error.
fn expand(s: &str, vars: &BTreeMap<String, String>) -> Result<String> {
    let re = Regex::new(r"\{\{\s*([A-Za-z0-9_.]+)\s*\}\}").expect("static regex");
    let mut missing = Vec::new();
    let out = re
        .replace_all(s, |c: &regex::Captures| match vars.get(&c[1]) {
            Some(v) => v.clone(),
            None => {
                missing.push(c[1].to_string());
                String::new()
            }
        })
        .into_owned();
    if !missing.is_empty() {
        bail!("unknown placeholder(s): {}", missing.join(", "));
    }
    Ok(out)
}

fn globs(patterns: &[String]) -> Result<GlobSet> {
    let mut b = GlobSetBuilder::new();
    for p in patterns {
        b.add(Glob::new(p).with_context(|| format!("bad glob {p}"))?);
    }
    Ok(b.build()?)
}

/// Files tracked by git (the upstream tree), excluding our own directory.
fn tracked(root: &Path) -> Result<Vec<String>> {
    let out = Command::new("git").arg("-C").arg(root).args(["ls-files", "-z"]).output().context("running git ls-files")?;
    if !out.status.success() {
        bail!("git ls-files failed: {}", String::from_utf8_lossy(&out.stderr));
    }
    Ok(out
        .stdout
        .split(|b| *b == 0)
        .filter(|p| !p.is_empty())
        .map(|p| String::from_utf8_lossy(p).into_owned())
        .filter(|p| !p.starts_with("freeandiy/"))
        .collect())
}

fn select<'a>(files: &'a [String], include: &[String], exclude: &[String]) -> Result<Vec<&'a String>> {
    let inc = globs(include)?;
    let exc = globs(exclude)?;
    Ok(files.iter().filter(|f| inc.is_match(f.as_str()) && !exc.is_match(f.as_str())).collect())
}

/// Text content, or None for binary / non-UTF-8 files and files that no longer exist.
fn read_text(path: &Path) -> Option<String> {
    let bytes = fs::read(path).ok()?;
    if bytes.contains(&0) {
        return None;
    }
    String::from_utf8(bytes).ok()
}

/// Replace every match of `re` in `text`, except on lines starting with a `skip` prefix (only
/// whole-line comments; with no prefixes the text is replaced as one string, so regexes may span
/// lines). Returns the new text and the number of replacements.
fn replace_text(text: &str, re: &Regex, with: &str, skip: &[String]) -> (String, usize) {
    if skip.is_empty() {
        let count = re.find_iter(text).count();
        return (re.replace_all(text, with).into_owned(), count);
    }
    let mut count = 0;
    let mut out = String::with_capacity(text.len());
    for line in text.split_inclusive('\n') {
        let trimmed = line.trim_start();
        if skip.iter().any(|p| trimmed.starts_with(p.as_str())) {
            out.push_str(line);
        } else {
            count += re.find_iter(line).count();
            out.push_str(&re.replace_all(line, with));
        }
    }
    (out, count)
}

fn copy_path(from: &Path, to: &Path) -> Result<usize> {
    if from.is_dir() {
        let mut n = 0;
        for entry in fs::read_dir(from).with_context(|| format!("reading {}", from.display()))? {
            let entry = entry?;
            n += copy_path(&entry.path(), &to.join(entry.file_name()))?;
        }
        Ok(n)
    } else {
        if let Some(parent) = to.parent() {
            fs::create_dir_all(parent)?;
        }
        fs::copy(from, to).with_context(|| format!("copying {} -> {}", from.display(), to.display()))?;
        Ok(1)
    }
}

fn apply(root: &Path) -> Result<()> {
    let vars = variables(root)?;
    let rules_text = fs::read_to_string(root.join("freeandiy/rules.toml")).context("reading freeandiy/rules.toml")?;
    let rules: Rules = toml::from_str(&expand(&rules_text, &vars)?).context("parsing freeandiy/rules.toml")?;
    let mut failures = Vec::new();

    // 1. delete
    for p in &rules.delete {
        let path = root.join(p);
        if path.is_dir() {
            fs::remove_dir_all(&path)?;
        } else if path.exists() {
            fs::remove_file(&path)?;
        } else {
            failures.push(format!("delete: {p} does not exist upstream any more"));
        }
    }
    println!("deleted {} path(s)", rules.delete.len());

    // 2. patches
    let mut patches: Vec<PathBuf> = fs::read_dir(root.join("freeandiy/patches"))
        .map(|d| d.filter_map(|e| e.ok().map(|e| e.path())).filter(|p| p.extension().is_some_and(|e| e == "patch")).collect())
        .unwrap_or_default();
    patches.sort();
    for p in &patches {
        let st = Command::new("git").arg("-C").arg(root).args(["apply", "--whitespace=nowarn"]).arg(p).status()?;
        if !st.success() {
            failures.push(format!("patch {} no longer applies: refresh it against the new upstream", p.display()));
        }
    }
    println!("applied {} patch(es)", patches.len());

    let files = tracked(root)?;

    // 3. drop_lines
    for d in &rules.drop_lines {
        let re = Regex::new(&d.regex).with_context(|| format!("bad regex {}", d.regex))?;
        let mut n = 0;
        for f in select(&files, &d.include, &d.exclude)? {
            let path = root.join(f);
            let Some(text) = read_text(&path) else { continue };
            let kept: Vec<&str> = text.split_inclusive('\n').filter(|l| !re.is_match(l)).collect();
            let out = kept.concat();
            if out.len() != text.len() {
                n += text.split_inclusive('\n').count() - kept.len();
                fs::write(&path, out)?;
            }
        }
        if n < d.min {
            failures.push(format!("drop_lines /{}/: {n} line(s), expected at least {}", d.regex, d.min));
        }
        println!("drop_lines /{}/: {n} line(s)", d.regex);
    }

    // 4. replace
    for r in &rules.replace {
        let re = match (&r.find, &r.regex) {
            (Some(f), None) => Regex::new(&regex::escape(f))?,
            (None, Some(x)) => Regex::new(x).with_context(|| format!("replace {:?}: bad regex", r.name))?,
            _ => bail!("replace {:?}: give exactly one of `find` or `regex`", r.name),
        };
        let mut n = 0;
        for f in select(&files, &r.include, &r.exclude)? {
            let path = root.join(f);
            let Some(text) = read_text(&path) else { continue };
            let (out, count) = replace_text(&text, &re, &r.replace, &r.skip_comments);
            if count > 0 {
                n += count;
                fs::write(&path, out)?;
            }
        }
        if n < r.min {
            failures.push(format!("replace {:?}: {n} match(es), expected at least {}", r.name, r.min));
        }
        println!("replace {:<48} {n:>5}", r.name);
    }

    // 5. rename
    let files = tracked(root)?;
    for r in &rules.rename {
        let mut n = 0;
        for f in select(&files, &r.include, &[])? {
            if !f.contains(&r.find) || !root.join(f).exists() {
                continue;
            }
            let to = root.join(f.replace(&r.find, &r.replace));
            if let Some(parent) = to.parent() {
                fs::create_dir_all(parent)?;
            }
            fs::rename(root.join(f), &to)?;
            n += 1;
        }
        if n < r.min {
            failures.push(format!("rename {:?}: {n} file(s), expected at least {}", r.find, r.min));
        }
        println!("rename {} -> {}: {n} file(s)", r.find, r.replace);
    }

    // 6. copy
    for c in &rules.copy {
        let n = copy_path(&root.join(&c.from), &root.join(&c.to))?;
        println!("copy {} -> {}: {n} file(s)", c.from, c.to);
    }

    // 7. templates
    for t in &rules.templates {
        let path = root.join(t);
        let text = fs::read_to_string(&path).with_context(|| format!("template {t}"))?;
        fs::write(&path, expand(&text, &vars).with_context(|| format!("template {t}"))?)?;
    }
    println!("rendered {} template(s)", rules.templates.len());

    if !failures.is_empty() {
        eprintln!("\nrebrand: {} problem(s):", failures.len());
        for f in &failures {
            eprintln!("  - {f}");
        }
        bail!("upstream changed in ways the rules don't cover yet");
    }
    Ok(())
}

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let root = PathBuf::from(args.get(1).map(String::as_str).unwrap_or("."));
    match args.first().map(String::as_str) {
        Some("apply") => apply(&root),
        Some("vars") => {
            for (k, v) in variables(&root)? {
                println!("{k} = {v}");
            }
            Ok(())
        }
        Some("get") => {
            // `rebrand get KEY [ROOT]`: one value, for shell scripts; an unknown key is an error.
            let key = args.get(1).ok_or_else(|| anyhow!("usage: rebrand get KEY [ROOT]"))?;
            let root = args.get(2).map(PathBuf::from).unwrap_or_else(|| PathBuf::from("."));
            let vars = variables(&root)?;
            println!("{}", vars.get(key.as_str()).ok_or_else(|| anyhow!("unknown key {key}"))?);
            Ok(())
        }
        _ => {
            eprintln!("usage: rebrand apply|vars [ROOT] | get KEY [ROOT]");
            std::process::exit(2);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn expand_fills_known_and_rejects_unknown_keys() {
        let vars = BTreeMap::from([("a.b".to_string(), "X".to_string())]);
        assert_eq!(expand("1{{a.b}}2{{ a.b }}", &vars).unwrap(), "1X2X");
        assert!(expand("{{nope}}", &vars).is_err());
    }

    #[test]
    fn skip_comments_leaves_comment_lines() {
        let re = Regex::new("PhotoCraft").unwrap();
        let text = "// PhotoCraft's own\nlet a = \"PhotoCraft\";\n  /// PhotoCraft doc\n";
        let (out, n) = replace_text(text, &re, "X", &["//".to_string()]);
        assert_eq!(n, 1);
        assert_eq!(out, "// PhotoCraft's own\nlet a = \"X\";\n  /// PhotoCraft doc\n");
        assert_eq!(replace_text(text, &re, "X", &[]).1, 3);
    }
}
