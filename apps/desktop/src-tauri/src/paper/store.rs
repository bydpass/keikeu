use super::{comparison_key, parse, render, Error, Paper, Result};
use sha2::{Digest, Sha256};
use std::ffi::{CStr, CString};
use std::fs::{self, File, Metadata};
use std::io::{Read, Write};
use std::os::fd::{AsRawFd, FromRawFd, IntoRawFd};
use std::os::unix::fs::{MetadataExt, OpenOptionsExt};
use std::path::{Path, PathBuf};

#[derive(Debug, Clone)]
pub struct Snapshot {
    pub path: String,
    pub paper: Paper,
    pub bytes: Vec<u8>,
    identity: (u64, u64),
}

impl Snapshot {
    pub fn digest(&self) -> String {
        format!("{:x}", Sha256::digest(&self.bytes))
    }
}

pub struct Vault {
    home: File,
    anchor_path: PathBuf,
    coordinated_paths: Option<Vec<String>>,
    acknowledged: std::collections::HashMap<String, String>,
    relative: PathBuf,
    root: File,
}

#[derive(Debug)]
pub enum Reconcile {
    Committed(Snapshot),
    NotCommitted(Option<Snapshot>),
    Stale,
}

fn invalid() -> Error {
    Error::new("validation_failed", "unsafe_paper_path")
}
fn stale() -> Error {
    Error::new("stale_snapshot", "file_or_directory_changed")
}
fn unknown() -> Error {
    Error::new(
        "commit_unknown",
        "both_versions_preserved_reconcile_read_only",
    )
}
fn identity(m: &Metadata) -> (u64, u64) {
    (m.dev(), m.ino())
}
fn cstring(s: &str) -> Result<CString> {
    CString::new(s).map_err(|_| invalid())
}

pub(crate) fn open_at(dir: &File, name: &str, flags: i32) -> Result<File> {
    let name = cstring(name)?;
    let fd = unsafe {
        libc::openat(
            dir.as_raw_fd(),
            name.as_ptr(),
            flags | libc::O_CLOEXEC | libc::O_NOFOLLOW,
            0o600,
        )
    };
    if fd < 0 {
        return Err(std::io::Error::last_os_error().into());
    }
    Ok(unsafe { File::from_raw_fd(fd) })
}

fn mkdir_at(parent: &File, name: &str) -> Result<()> {
    let name = cstring(name)?;
    if unsafe { libc::mkdirat(parent.as_raw_fd(), name.as_ptr(), 0o700) } != 0 {
        return Err(std::io::Error::last_os_error().into());
    }
    parent.sync_all()?;
    Ok(())
}

pub(crate) fn directory_at(dir: &File, path: &Path) -> Result<File> {
    let mut current = open_at(dir, ".", libc::O_RDONLY | libc::O_DIRECTORY)?;
    for component in path.components() {
        let std::path::Component::Normal(name) = component else {
            return Err(invalid());
        };
        current = open_at(
            &current,
            name.to_str().ok_or_else(invalid)?,
            libc::O_RDONLY | libc::O_DIRECTORY,
        )?;
    }
    Ok(current)
}

fn names(dir: &File) -> Result<Vec<String>> {
    let fd = open_at(dir, ".", libc::O_RDONLY | libc::O_DIRECTORY)?.into_raw_fd();
    let stream = unsafe { libc::fdopendir(fd) };
    if stream.is_null() {
        unsafe {
            libc::close(fd);
        }
        return Err(invalid());
    }
    let mut result = Vec::new();
    let failed;
    loop {
        #[cfg(any(target_os = "macos", target_os = "ios"))]
        unsafe {
            *libc::__error() = 0;
        }
        let item = unsafe { libc::readdir(stream) };
        if item.is_null() {
            failed = std::io::Error::last_os_error().raw_os_error().unwrap_or(0) != 0;
            break;
        }
        let name = unsafe { CStr::from_ptr((*item).d_name.as_ptr()) };
        match name.to_str() {
            Ok("." | "..") => (),
            Ok(s) => result.push(s.to_owned()),
            Err(_) => {
                failed = true;
                break;
            }
        }
    }
    unsafe {
        libc::closedir(stream);
    }
    if failed {
        return Err(invalid());
    }
    result.sort();
    Ok(result)
}

pub(crate) fn read_at(parent: &File, name: &str) -> Result<(Vec<u8>, (u64, u64))> {
    let mut file = open_at(parent, name, libc::O_RDONLY | libc::O_NONBLOCK)?;
    let before = file.metadata()?;
    if !before.is_file() {
        return Err(invalid());
    }
    let mut bytes = Vec::new();
    file.read_to_end(&mut bytes)?;
    let after = file.metadata()?;
    let fingerprint = |m: &Metadata| {
        (
            identity(m),
            m.len(),
            m.mtime(),
            m.mtime_nsec(),
            m.ctime(),
            m.ctime_nsec(),
        )
    };
    if fingerprint(&before) != fingerprint(&after) {
        return Err(stale());
    }
    Ok((bytes, identity(&after)))
}

pub(crate) fn entry_exists(dir: &File, name: &str) -> Result<bool> {
    let name = cstring(name)?;
    let mut stat = std::mem::MaybeUninit::<libc::stat>::uninit();
    if unsafe {
        libc::fstatat(
            dir.as_raw_fd(),
            name.as_ptr(),
            stat.as_mut_ptr(),
            libc::AT_SYMLINK_NOFOLLOW,
        )
    } == 0
    {
        return Ok(true);
    }
    let e = std::io::Error::last_os_error();
    if e.kind() == std::io::ErrorKind::NotFound {
        Ok(false)
    } else {
        Err(e.into())
    }
}

fn rename(parent: &File, from: &str, to: &str, exclusive: bool) -> Result<()> {
    #[cfg(any(target_os = "macos", target_os = "ios"))]
    {
        let from = cstring(from)?;
        let to = cstring(to)?;
        let flags = if exclusive {
            libc::RENAME_EXCL
        } else {
            libc::RENAME_SWAP
        };
        if unsafe {
            libc::renameatx_np(
                parent.as_raw_fd(),
                from.as_ptr(),
                parent.as_raw_fd(),
                to.as_ptr(),
                flags,
            )
        } != 0
        {
            return Err(std::io::Error::last_os_error().into());
        }
        Ok(())
    }
    #[cfg(not(any(target_os = "macos", target_os = "ios")))]
    {
        let _ = (parent, from, to, exclusive);
        Err(Error::new(
            "unsupported_platform",
            "atomic_exchange_required",
        ))
    }
}

fn unlink_owned(parent: &File, name: &str, expected: &[u8], owned: (u64, u64)) -> Result<()> {
    let (bytes, id) = read_at(parent, name)?;
    if bytes != expected || id != owned {
        return Err(unknown());
    }
    let name = cstring(name)?;
    if unsafe { libc::unlinkat(parent.as_raw_fd(), name.as_ptr(), 0) } != 0 {
        return Err(unknown());
    }
    Ok(())
}

fn supported(path: &str) -> Result<(PathBuf, &str)> {
    let parts: Vec<_> = path.split('/').collect();
    if !matches!(parts.len(), 2 | 3)
        || parts[0] != "cache"
        || parts
            .iter()
            .any(|p| p.is_empty() || *p == "." || *p == "..")
    {
        return Err(invalid());
    }
    if parts.len() == 3
        && (parts[1].trim() != parts[1]
            || parts[1].starts_with('.')
            || parts[1].contains(':')
            || [
                "cache",
                ".trash",
                "keikeu_index.json",
                "全部 paper",
                "未归类",
                "trash",
            ]
            .contains(&comparison_key(parts[1]).as_str())
            || parts[1].chars().count() > 200
            || parts[1]
                .chars()
                .any(|c| c.is_control() || matches!(c, '\u{2028}' | '\u{2029}')))
    {
        return Err(invalid());
    }
    let filename = parts[parts.len() - 1];
    if !filename.ends_with(".md") || filename == ".md" {
        return Err(invalid());
    }
    Ok((parts[..parts.len() - 1].iter().collect(), filename))
}

impl Vault {
    /// Resolve response loss by inspecting bytes only. Never retries the original mutation.
    pub fn reconcile(
        &self,
        path: &str,
        baseline_digest: Option<&str>,
        submitted: &Paper,
    ) -> Result<Reconcile> {
        let proposed = render(submitted)?;
        let (relative, name) = supported(path)?;
        let parent = directory_at(&self.root, &relative)?;
        self.guard(&relative, &parent)?;
        if !entry_exists(&parent, name)? {
            return Ok(if baseline_digest.is_none() {
                Reconcile::NotCommitted(None)
            } else {
                Reconcile::Stale
            });
        }
        self.unique(&submitted.code, Some(path))?;
        let current = self.read(path)?;
        if current.paper.code != submitted.code
            || current.paper.created != submitted.normalized()?.created
        {
            return Ok(Reconcile::Stale);
        }
        if current.bytes == proposed {
            return Ok(Reconcile::Committed(current));
        }
        if baseline_digest.is_some_and(|digest| current.digest() == digest) {
            return Ok(Reconcile::NotCommitted(Some(current)));
        }
        Ok(Reconcile::Stale)
    }
    /// Open an existing Home-contained sandbox root without following author-controlled symlinks.
    pub fn open(root: &Path) -> Result<Self> {
        let home_path = PathBuf::from(std::env::var_os("HOME").ok_or_else(invalid)?);
        let canonical_home = home_path.canonicalize()?;
        let relative = root
            .strip_prefix(&home_path)
            .or_else(|_| root.strip_prefix(&canonical_home))
            .map_err(|_| invalid())?;
        if root
            .to_str()
            .is_none_or(|s| s.split('/').any(|p| p == "." || p == ".."))
        {
            return Err(invalid());
        }
        let home = fs::OpenOptions::new()
            .read(true)
            .custom_flags(libc::O_DIRECTORY | libc::O_NOFOLLOW)
            .open(&canonical_home)?;
        let directory = directory_at(&home, relative)?;
        directory_at(&directory, Path::new("cache"))?;
        Ok(Self {
            home,
            anchor_path: canonical_home,
            coordinated_paths: None,
            acknowledged: Default::default(),
            relative: relative.into(),
            root: directory,
        })
    }

    /// The host alone supplies an Apple-returned container; never pass a frontend path here.
    /// Initialization is called only inside native coordination after explicit cloud selection.
    pub(crate) fn open_apple_container(
        container: &Path,
        relative: &Path,
        initialize: bool,
    ) -> Result<Self> {
        let raw = relative.to_str().ok_or_else(invalid)?;
        let parts: Vec<_> = raw.split('/').collect();
        if parts.len() != 2
            || parts[0] != "Documents"
            || parts[1].is_empty()
            || parts[1].starts_with('.')
            || parts[1].contains(':')
        {
            return Err(invalid());
        }
        let anchor_path = container.canonicalize()?;
        let home = fs::OpenOptions::new()
            .read(true)
            .custom_flags(libc::O_DIRECTORY | libc::O_NOFOLLOW)
            .open(&anchor_path)?;
        if initialize && !entry_exists(&home, "Documents")? {
            mkdir_at(&home, "Documents")?;
        }
        let documents = directory_at(&home, Path::new("Documents"))?;
        if initialize && !entry_exists(&documents, parts[1])? {
            let temporary = format!(".keikeu-init-{}", uuid::Uuid::new_v4());
            mkdir_at(&documents, &temporary)?;
            let root = directory_at(&documents, Path::new(&temporary))?;
            mkdir_at(&root, "cache")?;
            root.sync_all()?;
            rename(&documents, &temporary, parts[1], true)?;
            documents.sync_all()?;
        }
        // Never add cache to an unknown pre-existing directory.
        let root = directory_at(&home, relative)?;
        directory_at(&root, Path::new("cache"))?;
        let result = Self {
            home,
            anchor_path,
            relative: relative.into(),
            root,
            coordinated_paths: Some(vec![]),
            acknowledged: Default::default(),
        };
        result.guard(Path::new(""), &result.root)?;
        Ok(result)
    }

    pub(crate) fn set_coordinated_paths(&mut self, mut paths: Vec<String>) -> Result<()> {
        if self.coordinated_paths.is_none() {
            return Err(invalid());
        }
        for path in &paths {
            supported(path)?;
        }
        paths.sort();
        paths.dedup();
        self.coordinated_paths = Some(paths);
        Ok(())
    }

    fn guard(&self, parent_path: &Path, parent: &File) -> Result<()> {
        let anchor = fs::OpenOptions::new()
            .read(true)
            .custom_flags(libc::O_DIRECTORY | libc::O_NOFOLLOW)
            .open(&self.anchor_path)
            .map_err(|_| stale())?;
        if identity(&anchor.metadata()?) != identity(&self.home.metadata()?) {
            return Err(stale());
        }
        let root = directory_at(&self.home, &self.relative).map_err(|_| stale())?;
        if identity(&root.metadata()?) != identity(&self.root.metadata()?) {
            return Err(stale());
        }
        let current = directory_at(&root, parent_path).map_err(|_| stale())?;
        if identity(&current.metadata()?) != identity(&parent.metadata()?) {
            return Err(stale());
        }
        Ok(())
    }

    fn require_coordinated(&self, path: &str) -> Result<()> {
        if self
            .coordinated_paths
            .as_ref()
            .is_some_and(|paths| !paths.iter().any(|p| p == path))
        {
            return Err(Error::new("not_downloaded", "native_discovery_required"));
        }
        Ok(())
    }

    pub(crate) fn read_raw_optional(&self, path: &str) -> Result<Option<Vec<u8>>> {
        self.require_coordinated(path)?;
        let (relative, name) = supported(path)?;
        let parent = directory_at(&self.root, &relative)?;
        self.guard(&relative, &parent)?;
        if entry_exists(&parent, name)? {
            self.read_raw(path).map(Some)
        } else {
            Ok(None)
        }
    }

    /// Read a bounded active-area file verbatim for an explicit repair export.
    pub fn read_raw(&self, path: &str) -> Result<Vec<u8>> {
        self.require_coordinated(path)?;
        let (relative, name) = supported(path)?;
        let parent = directory_at(&self.root, &relative)?;
        self.guard(&relative, &parent)?;
        let (bytes, _) = read_at(&parent, name)?;
        self.guard(&relative, &parent)?;
        Ok(bytes)
    }

    pub fn read(&self, path: &str) -> Result<Snapshot> {
        self.require_coordinated(path)?;
        let (relative, name) = supported(path)?;
        let parent = directory_at(&self.root, &relative)?;
        self.guard(&relative, &parent)?;
        let (bytes, id) = read_at(&parent, name)?;
        let paper = parse(&bytes)?;
        if name != format!("{}.md", paper.code) {
            return Err(Error::format("filename_code_mismatch"));
        }
        self.guard(&relative, &parent)?;
        Ok(Snapshot {
            path: path.into(),
            paper,
            bytes,
            identity: id,
        })
    }

    /// Scan one supported folder level; isolate invalid Papers, never mutate the Index or sources.
    pub fn list(&self) -> Result<(Vec<Snapshot>, Vec<(String, Error)>)> {
        let root = directory_at(&self.root, Path::new("cache"))?;
        self.guard(Path::new("cache"), &root)?;
        let mut errors = Vec::new();
        let paths = if let Some(paths) = &self.coordinated_paths {
            paths.clone()
        } else {
            let mut paths = Vec::new();
            for name in names(&root)? {
                if name.ends_with(".md") {
                    paths.push(format!("cache/{name}"));
                } else if let Ok(folder) = directory_at(&root, Path::new(&name)) {
                    for child in names(&folder)? {
                        if child.ends_with(".md") {
                            paths.push(format!("cache/{name}/{child}"));
                        }
                    }
                }
            }
            paths
        };
        let mut papers = Vec::new();
        for path in paths {
            if self.coordinated_paths.is_some() {
                let (relative, name) = supported(&path)?;
                let parent = directory_at(&self.root, &relative)?;
                self.guard(&relative, &parent)?;
                if !entry_exists(&parent, name)? {
                    continue;
                }
            }
            match self.read(&path) {
                Ok(p) => papers.push(p),
                Err(e) => errors.push((path, e)),
            }
        }
        self.guard(Path::new("cache"), &root)?;
        Ok((papers, errors))
    }

    pub fn search(&self, query: &str) -> Result<(Vec<Snapshot>, Vec<(String, Error)>)> {
        let (papers, errors) = self.list()?;
        let needle = comparison_key(query);
        Ok((
            papers
                .into_iter()
                .filter(|s| {
                    let p = &s.paper;
                    let mut fields = vec![p.code.as_str(), p.display_name.as_deref().unwrap_or("")];
                    fields.extend(p.tags.iter().map(String::as_str));
                    for page in &p.pages {
                        fields.extend([
                            page.name.as_deref().unwrap_or(""),
                            &page.content,
                            page.r#type.as_deref().unwrap_or(""),
                        ]);
                        fields.push(match page.r#type.as_deref() {
                            Some("summary") => "总结",
                            Some("snapshot") => "高光",
                            Some("whisper") => "碎碎念",
                            _ => "",
                        });
                    }
                    comparison_key(&fields.join("\0")).contains(&needle)
                })
                .collect(),
            errors,
        ))
    }

    pub(crate) fn acknowledge_preserved(
        &mut self,
        copies: std::collections::HashMap<String, String>,
    ) {
        self.acknowledged = copies;
    }
    fn unique(&self, code: &str, excluding: Option<&str>) -> Result<()> {
        if let Some(enlisted) = &self.coordinated_paths {
            // A file appearing after discovery must be enlisted in a new native batch before reading.
            let cache = directory_at(&self.root, Path::new("cache"))?;
            for name in names(&cache)? {
                let paths = if name.ends_with(".md") {
                    vec![format!("cache/{name}")]
                } else if let Ok(folder) = directory_at(&cache, Path::new(&name)) {
                    names(&folder)?
                        .into_iter()
                        .filter(|n| n.ends_with(".md"))
                        .map(|n| format!("cache/{name}/{n}"))
                        .collect()
                } else {
                    vec![]
                };
                if paths.iter().any(|path| !enlisted.contains(path)) {
                    return Err(Error::new("stale_snapshot", "rediscover_new_cloud_items"));
                }
            }
            self.guard(Path::new("cache"), &cache)?;
        }
        let (papers, errors) = self.list()?;
        let key = comparison_key(code);
        let paths = papers
            .iter()
            .map(|s| &s.path)
            .chain(errors.iter().map(|(path, _)| path));
        for path in paths {
            if Some(path.as_str()) == excluding {
                continue;
            }
            let bytes = self.read_raw(path)?;
            if self
                .acknowledged
                .get(path)
                .is_some_and(|digest| *digest != format!("{:x}", Sha256::digest(&bytes)))
            {
                return Err(Error::new("conflict_required", "preserved_sibling_changed"));
            }
            let same_code = parse(&bytes).is_ok_and(|p| comparison_key(&p.code) == key)
                || Path::new(path)
                    .file_stem()
                    .and_then(|s| s.to_str())
                    .is_some_and(|s| comparison_key(s) == key);
            if same_code
                && self.acknowledged.get(path) != Some(&format!("{:x}", Sha256::digest(&bytes)))
            {
                return Err(Error::new("duplicate_code", "provider_sibling_preserved"));
            }
        }
        Ok(())
    }

    /// Explicit raw recovery only: the host has durably preserved the active bytes and this copy.
    pub(crate) fn promote_raw(
        &self,
        path: &str,
        proposed: &[u8],
        expected_digest: Option<&str>,
    ) -> Result<Snapshot> {
        self.require_coordinated(path)?;
        let paper = parse(proposed)?;
        let (relative, name) = supported(path)?;
        if name != format!("{}.md", paper.code) {
            return Err(invalid());
        }
        let parent = directory_at(&self.root, &relative)?;
        self.guard(&relative, &parent)?;
        let expected = if entry_exists(&parent, name)? {
            let value = read_at(&parent, name)?;
            if expected_digest != Some(format!("{:x}", Sha256::digest(&value.0)).as_str()) {
                return Err(stale());
            }
            Some(value)
        } else {
            if expected_digest.is_some() {
                return Err(stale());
            }
            None
        };
        self.publish(
            path,
            proposed.to_vec(),
            expected.as_ref().map(|(bytes, id)| (bytes.as_slice(), *id)),
            || {},
        )
    }

    pub fn save(&self, path: &str, paper: &Paper, expected: Option<&Snapshot>) -> Result<Snapshot> {
        self.require_coordinated(path)?;
        self.save_before_publish(path, paper, expected, || {})
    }

    fn save_before_publish(
        &self,
        path: &str,
        paper: &Paper,
        expected: Option<&Snapshot>,
        before_publish: impl FnOnce(),
    ) -> Result<Snapshot> {
        let proposed = render(paper)?;
        parse(&proposed)?; // Never publish bytes that our strict reader cannot reopen.
        let (_, name) = supported(path)?;
        if name != format!("{}.md", paper.code)
            || expected.is_some_and(|s| {
                s.path != path || s.paper.code != paper.code || s.paper.created != paper.created
            })
        {
            return Err(invalid());
        }
        self.publish(
            path,
            proposed,
            expected.map(|s| (s.bytes.as_slice(), s.identity)),
            before_publish,
        )
    }

    fn publish(
        &self,
        path: &str,
        proposed: Vec<u8>,
        expected: Option<(&[u8], (u64, u64))>,
        before_publish: impl FnOnce(),
    ) -> Result<Snapshot> {
        let paper = parse(&proposed)?;
        let (relative, name) = supported(path)?;
        let parent = directory_at(&self.root, &relative)?;
        self.guard(&relative, &parent)?;
        self.unique(&paper.code, expected.map(|_| path))?;
        if let Some(old) = expected {
            let (bytes, id) = read_at(&parent, name)?;
            if bytes != old.0 || id != old.1 {
                return Err(stale());
            }
        } else if entry_exists(&parent, name)? {
            return Err(Error::new("duplicate_code", "paper_target_exists"));
        }
        let temporary = format!(".{}.tmp", uuid::Uuid::new_v4());
        let mut file = open_at(
            &parent,
            &temporary,
            libc::O_WRONLY | libc::O_CREAT | libc::O_EXCL,
        )?;
        let proposed_id = identity(&file.metadata()?);
        if file
            .write_all(&proposed)
            .and_then(|_| file.sync_all())
            .is_err()
        {
            // Incomplete private temporary bytes are kept for diagnosis; no author target was touched.
            return Err(Error::new("operation_failed", "temporary_write_failed"));
        }
        before_publish();
        if let Err(e) = self
            .guard(&relative, &parent)
            .and_then(|_| rename(&parent, &temporary, name, expected.is_none()))
        {
            unlink_owned(&parent, &temporary, &proposed, proposed_id)?;
            return Err(e);
        }
        if let Some(old) = expected {
            let displaced = read_at(&parent, &temporary);
            let verified = displaced
                .as_ref()
                .is_ok_and(|(bytes, id)| *bytes == old.0 && *id == old.1)
                && self.guard(&relative, &parent).is_ok();
            if !verified {
                let (previous_bytes, previous_id) = displaced.map_err(|_| unknown())?;
                let (current_bytes, current_id) = read_at(&parent, name).map_err(|_| unknown())?;
                if current_id != proposed_id || current_bytes != proposed {
                    return Err(unknown());
                }
                rename(&parent, &temporary, name, false).map_err(|_| unknown())?;
                let (restored, id) = read_at(&parent, name).map_err(|_| unknown())?;
                if id != previous_id || restored != previous_bytes {
                    return Err(unknown());
                }
                unlink_owned(&parent, &temporary, &proposed, proposed_id)?;
                return Err(stale());
            }
            unlink_owned(&parent, &temporary, old.0, old.1)?;
        }
        // A post-publication failure must not invite replay, even if bytes appear committed.
        parent.sync_all().map_err(|_| unknown())?;
        self.guard(&relative, &parent).map_err(|_| unknown())?;
        self.unique(&paper.code, Some(path))
            .map_err(|_| unknown())?;
        let result = self.read(path).map_err(|_| unknown())?;
        if result.bytes != proposed {
            return Err(unknown());
        }
        Ok(result)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::os::unix::fs::symlink;

    #[test]
    fn apple_anchor_and_enlisted_paths_reject_escape_and_replacement() {
        let base = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../../../tests/test-vault")
            .canonicalize()
            .unwrap()
            .join(format!("apple-anchor-{}", uuid::Uuid::new_v4()));
        fs::create_dir_all(base.join("container")).unwrap();
        let container = base.join("container");
        assert!(
            Vault::open_apple_container(&container, Path::new("Documents/../escape"), true)
                .is_err()
        );
        let mut vault =
            Vault::open_apple_container(&container, Path::new("Documents/keikeu"), true).unwrap();
        let corpus: serde_json::Value = serde_json::from_str(include_str!(
            "../../../../../tests/fixtures/paper-v4-golden.json"
        ))
        .unwrap();
        let paper: Paper = serde_json::from_value(corpus["cases"][0]["paper"].clone()).unwrap();
        let path = format!("cache/{}.md", paper.code);
        assert_eq!(
            vault.save(&path, &paper, None).unwrap_err().code,
            "not_downloaded"
        );
        vault.set_coordinated_paths(vec![path.clone()]).unwrap();
        vault.save(&path, &paper, None).unwrap();
        assert_eq!(vault.list().unwrap().0.len(), 1);
        let snapshot = vault.read(&path).unwrap();
        fs::write(
            container.join("Documents/keikeu/cache/newly-arrived.md"),
            b"unlisted bytes",
        )
        .unwrap();
        assert_eq!(
            vault
                .save(&path, &paper, Some(&snapshot))
                .unwrap_err()
                .reason,
            "rediscover_new_cloud_items"
        );
        assert_eq!(vault.read(&path).unwrap().bytes, snapshot.bytes);
        let unknown = container.join("Documents/unknown");
        fs::create_dir(&unknown).unwrap();
        assert!(
            Vault::open_apple_container(&container, Path::new("Documents/unknown"), true).is_err()
        );
        assert!(!unknown.join("cache").exists());
        symlink(
            base.join("outside"),
            container.join("Documents/keikeu/cache/link.md"),
        )
        .unwrap();
        vault
            .set_coordinated_paths(vec!["cache/link.md".into()])
            .unwrap();
        assert!(vault.read_raw("cache/link.md").is_err());
        assert!(vault
            .set_coordinated_paths(vec!["cache/../../escape.md".into()])
            .is_err());
        fs::rename(&container, base.join("held-container")).unwrap();
        fs::create_dir_all(container.join("Documents/keikeu/cache")).unwrap();
        assert_eq!(vault.list().unwrap_err().code, "stale_snapshot");
    }

    #[test]
    fn save_reopen_search_cas_and_escape() {
        let base = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../../../tests/test-vault")
            .canonicalize()
            .unwrap();
        let root = base.join(format!("rust-core-{}", uuid::Uuid::new_v4()));
        fs::create_dir_all(root.join("cache")).unwrap();
        let alias = base.join(format!("alias-{}", uuid::Uuid::new_v4()));
        symlink(&root, &alias).unwrap();
        assert!(Vault::open(&alias).is_err());
        let vault = Vault::open(&root).unwrap();
        let corpus: serde_json::Value = serde_json::from_str(include_str!(
            "../../../../../tests/fixtures/paper-v4-golden.json"
        ))
        .unwrap();
        let paper: Paper = serde_json::from_value(corpus["cases"][0]["paper"].clone()).unwrap();
        let path = format!("cache/{}.md", paper.code);
        let first = vault.save(&path, &paper, None).unwrap();
        assert_eq!(vault.read(&path).unwrap().bytes, first.bytes);
        assert_eq!(vault.search("STRASSE É").unwrap().0.len(), 1);
        assert_eq!(vault.search("高光").unwrap().0.len(), 1);
        assert_eq!(super::super::comparison_key("Ა"), "ა"); // post-Unicode-9 case folding
        assert!(vault.save(&path, &paper, None).is_err());
        let mut edited = paper.clone();
        edited.pages[1].content = "edited second page".into();
        let second = vault.save(&path, &edited, Some(&first)).unwrap();
        // Treat the successful response as lost: reconciliation only reads the submitted bytes.
        assert!(matches!(
            vault
                .reconcile(&path, Some(&first.digest()), &edited)
                .unwrap(),
            Reconcile::Committed(_)
        ));
        assert!(matches!(
            vault
                .reconcile(&path, Some(&second.digest()), &paper)
                .unwrap(),
            Reconcile::NotCommitted(Some(_))
        ));
        assert_eq!(
            vault.read(&path).unwrap().paper.pages[1].content,
            "edited second page"
        );
        assert!(vault.save(&path, &paper, Some(&first)).is_err());
        assert_eq!(vault.read(&path).unwrap().bytes, second.bytes);
        let mut invalid_paper = paper.clone();
        invalid_paper.pages[0].content = "bare\rcarriage".into();
        assert!(vault.save(&path, &invalid_paper, Some(&second)).is_err());
        assert_eq!(vault.read(&path).unwrap().bytes, second.bytes);
        let sibling = root.join("cache/provider-renamed.md");
        fs::write(&sibling, &second.bytes).unwrap();
        assert_eq!(
            vault.save(&path, &paper, Some(&second)).unwrap_err().code,
            "duplicate_code"
        );
        assert_eq!(fs::read(&sibling).unwrap(), second.bytes);
        fs::rename(&sibling, root.join("preserved-sibling.bytes")).unwrap();
        let foreign = b"external writer bytes";
        let result = vault.save_before_publish(&path, &paper, Some(&second), || {
            fs::write(root.join(&path), foreign).unwrap();
        });
        assert_eq!(result.unwrap_err().code, "stale_snapshot");
        assert_eq!(fs::read(root.join(&path)).unwrap(), foreign);
        assert!(vault.save("cache/../escape.md", &paper, None).is_err());
        symlink(&base, root.join("cache/escape")).unwrap();
        assert!(vault
            .save(&format!("cache/escape/{}.md", paper.code), &paper, None)
            .is_err());
        assert!(!base.join(format!("{}.md", paper.code)).exists());
        let outside = base.join(format!("outside-{}", uuid::Uuid::new_v4()));
        fs::write(&outside, b"untouched sentinel").unwrap();
        let mut another = paper.clone();
        another.code = "K-20260907-002".into();
        let link_path = format!("cache/{}.md", another.code);
        symlink(&outside, root.join(&link_path)).unwrap();
        assert!(vault.save(&link_path, &another, None).is_err());
        assert_eq!(fs::read(&outside).unwrap(), b"untouched sentinel");
        let collision_path = root.join("cache/blocked");
        fs::create_dir(&collision_path).unwrap();
        assert!(vault
            .save("cache/blocked/not-code.md", &paper, None)
            .is_err());
        let replacement = base.join(format!("replacement-{}", uuid::Uuid::new_v4()));
        fs::rename(root.join("cache"), &replacement).unwrap();
        fs::create_dir(root.join("cache")).unwrap();
        // The old snapshot belongs to a different directory; it cannot recreate the file silently.
        assert!(vault.save(&path, &paper, Some(&second)).is_err());
    }
}
