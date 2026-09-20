use crate::paper::store::{directory_at, entry_exists, open_at, read_at};
use crate::paper::{Error, Result};
use serde_json::Value;
use std::ffi::CString;
use std::fs::{File, OpenOptions};
use std::io::Write;
use std::os::fd::AsRawFd;
use std::os::unix::fs::{MetadataExt, OpenOptionsExt};
use std::path::{Component, Path, PathBuf};

pub struct Private {
    home: File,
    relative: PathBuf,
    dir: File,
}

impl Private {
    pub fn open(path: &Path) -> Result<Self> {
        let home_path = PathBuf::from(std::env::var_os("HOME").ok_or_else(invalid)?);
        let canonical = home_path.canonicalize()?;
        let relative = path
            .strip_prefix(&home_path)
            .or_else(|_| path.strip_prefix(&canonical))
            .map_err(|_| invalid())?
            .to_path_buf();
        let home = OpenOptions::new()
            .read(true)
            .custom_flags(libc::O_NOFOLLOW | libc::O_DIRECTORY)
            .open(canonical)?;
        let mut dir = open_at(&home, ".", libc::O_RDONLY | libc::O_DIRECTORY)?;
        for component in relative.components() {
            let Component::Normal(name) = component else {
                return Err(invalid());
            };
            let name = name.to_str().ok_or_else(invalid)?;
            if !entry_exists(&dir, name)? {
                let c = CString::new(name).map_err(|_| invalid())?;
                if unsafe { libc::mkdirat(dir.as_raw_fd(), c.as_ptr(), 0o700) } != 0 {
                    return Err(std::io::Error::last_os_error().into());
                }
            }
            dir = open_at(&dir, name, libc::O_RDONLY | libc::O_DIRECTORY)?;
        }
        Ok(Self {
            home,
            relative,
            dir,
        })
    }

    fn guard(&self) -> Result<()> {
        let current = directory_at(&self.home, &self.relative)?.metadata()?;
        let held = self.dir.metadata()?;
        if (current.dev(), current.ino()) != (held.dev(), held.ino()) {
            return Err(invalid());
        }
        Ok(())
    }

    pub fn read(&self) -> Result<Option<Value>> {
        self.guard()?;
        if !entry_exists(&self.dir, "state.json")? {
            return Ok(None);
        }
        let bytes = read_at(&self.dir, "state.json")?.0;
        self.guard()?;
        serde_json::from_slice(&bytes)
            .map(Some)
            .map_err(|_| invalid())
    }

    pub fn export_copy(&self, bytes: &[u8], extension: &str) -> Result<PathBuf> {
        self.guard()?;
        let name = format!("export-{}.{}", uuid::Uuid::new_v4(), extension);
        let mut file = open_at(
            &self.dir,
            &name,
            libc::O_WRONLY | libc::O_CREAT | libc::O_EXCL,
        )?;
        file.write_all(bytes)?;
        file.sync_all()?;
        self.dir.sync_all()?;
        if read_at(&self.dir, &name)?.0 != bytes {
            return Err(invalid());
        }
        self.guard()?;
        Ok(PathBuf::from(std::env::var_os("HOME").ok_or_else(invalid)?)
            .join(&self.relative)
            .join(name))
    }

    pub fn write(&self, value: &Value) -> Result<()> {
        self.guard()?;
        // ponytail: one atomic private journal; split per draft if measured write cost grows.
        let bytes = serde_json::to_vec(value).map_err(|_| invalid())?;
        let name = format!("{}.tmp", uuid::Uuid::new_v4());
        let mut file = open_at(
            &self.dir,
            &name,
            libc::O_WRONLY | libc::O_CREAT | libc::O_EXCL,
        )?;
        file.write_all(&bytes)?;
        file.sync_all()?;
        self.guard()?;
        let from = CString::new(name).map_err(|_| invalid())?;
        let to = c"state.json";
        // Only the app-private journal is replaced. Paper publication uses Core CAS.
        if unsafe {
            libc::renameat(
                self.dir.as_raw_fd(),
                from.as_ptr(),
                self.dir.as_raw_fd(),
                to.as_ptr(),
            )
        } != 0
        {
            return Err(std::io::Error::last_os_error().into());
        }
        self.dir.sync_all()?;
        self.guard()?;
        if read_at(&self.dir, "state.json")?.0 != bytes {
            return Err(invalid());
        }
        Ok(())
    }
}
fn invalid() -> Error {
    Error::new("recovery_unavailable", "private_state_unavailable")
}
