use super::*;
use sha2::{Digest, Sha256};

#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct ConflictCopy {
    pub path: String,
    pub origin: String,
    pub bytes: Vec<u8>,
    pub digest: String,
}
impl ConflictCopy {
    pub fn new(path: String, origin: &str, bytes: Vec<u8>) -> Self {
        let digest = format!("{:x}", Sha256::digest(&bytes));
        Self {
            path,
            origin: origin.into(),
            bytes,
            digest,
        }
    }
    pub(super) fn verify(&self) -> Result<()> {
        if format!("{:x}", Sha256::digest(&self.bytes)) != self.digest {
            return Err(Error::new(
                "recovery_unavailable",
                "conflict_copy_digest_changed",
            ));
        }
        Ok(())
    }
}
impl Session {
    pub(super) fn preserve_conflicts(&mut self, copies: Vec<ConflictCopy>) -> Result<()> {
        let mut next = self.journal.clone();
        for copy in copies {
            copy.verify()?;
            if !next.conflicts.values().any(|old| {
                old.path == copy.path && old.origin == copy.origin && old.digest == copy.digest
            }) {
                next.conflicts
                    .insert(uuid::Uuid::new_v4().to_string(), copy);
            }
        }
        self.persist(next)?;
        // Private::write already fsyncs and reads bytes back; also verify the decoded catalog.
        let restored: Journal = serde_json::from_value(self.private.read()?.ok_or_else(invalid)?)
            .map_err(|_| invalid())?;
        for (token, copy) in &self.journal.conflicts {
            let stored = restored.conflicts.get(token).ok_or_else(invalid)?;
            stored.verify()?;
            if stored.bytes != copy.bytes {
                return Err(invalid());
            }
        }
        Ok(())
    }
    pub(super) fn conflict_request(&self, method: &str, p: &Value) -> Result<Value> {
        if method == "host.conflict.list" {
            let mut copies = Vec::new();
            for (token, copy) in &self.journal.conflicts {
                copy.verify()?;
                let parsed = paper::parse(&copy.bytes);
                copies.push(
                    json!({"token":token,"path":copy.path,"origin":copy.origin,"digest":copy.digest,
                    "valid":parsed.is_ok(),"code":parsed.as_ref().ok().map(|p| &p.code)}),
                );
            }
            copies.sort_by(|a, b| {
                a["path"]
                    .as_str()
                    .cmp(&b["path"].as_str())
                    .then(a["digest"].as_str().cmp(&b["digest"].as_str()))
            });
            return Ok(json!({"copies":copies,"pending":self.journal.pending_promotion}));
        }
        if method == "host.conflict.export" {
            let copy = self
                .journal
                .conflicts
                .get(text(p, "token")?)
                .ok_or_else(invalid)?;
            copy.verify()?;
            let path = self.private.export_copy(&copy.bytes, "md")?;
            return Ok(json!({"native_export":{"method":"export","path":path}}));
        }
        Err(invalid())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn invalid_conflict_bytes_survive_restart_and_corruption_blocks_export() {
        let base = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../../../tests/test-vault")
            .canonicalize()
            .unwrap()
            .join(format!("conflicts-{}", uuid::Uuid::new_v4()));
        let mut session = Session::with_vault(None, &base, "en").unwrap();
        let bytes = vec![0xff, 0, 0xfe, b'\n'];
        session
            .preserve_conflicts(vec![ConflictCopy::new(
                "cache/conflict.md".into(),
                "native",
                bytes.clone(),
            )])
            .unwrap();
        drop(session);
        let mut session = Session::with_vault(None, &base, "en").unwrap();
        let list = session
            .conflict_request("host.conflict.list", &json!({}))
            .unwrap();
        assert_eq!(list["copies"][0]["valid"], false);
        let token = list["copies"][0]["token"].as_str().unwrap();
        assert_eq!(session.journal.conflicts[token].bytes, bytes);
        session
            .journal
            .conflicts
            .get_mut(token)
            .unwrap()
            .bytes
            .push(1);
        assert_eq!(
            session
                .conflict_request("host.conflict.export", &json!({"token":token}))
                .unwrap_err()
                .code,
            "recovery_unavailable"
        );
        std::fs::remove_dir_all(base).unwrap();
    }
}

#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Promotion {
    pub copy: String,
    pub path: String,
    pub baseline: Option<String>,
}
fn digest(bytes: &Option<Vec<u8>>) -> Option<String> {
    bytes
        .as_ref()
        .map(|bytes| format!("{:x}", Sha256::digest(bytes)))
}
impl Session {
    pub(super) fn promotion_path(&self, method: &str, p: &Value) -> Result<String> {
        if method == "host.conflict.reconcile" {
            return Ok(self
                .journal
                .pending_promotion
                .as_ref()
                .ok_or_else(invalid)?
                .path
                .clone());
        }
        if method == "host.conflict.promote" {
            return Ok(self
                .promotions
                .get(text(p, "inspection")?)
                .ok_or_else(invalid)?
                .path
                .clone());
        }
        let copy = self
            .journal
            .conflicts
            .get(text(p, "token")?)
            .ok_or_else(invalid)?;
        copy.verify()?;
        let paper = paper::parse(&copy.bytes)?;
        Ok(format!(
            "{}/{}.md",
            copy.path.rsplit_once('/').ok_or_else(invalid)?.0,
            paper.code
        ))
    }
    pub(super) fn promote_request(&mut self, method: &str, p: &Value) -> Result<Value> {
        let path = self.promotion_path(method, p)?;
        let current = self.vault()?.read_raw_optional(&path)?;
        if method == "host.conflict.inspect" {
            let token = uuid::Uuid::new_v4().to_string();
            let promotion = Promotion {
                copy: text(p, "token")?.into(),
                path: path.clone(),
                baseline: digest(&current),
            };
            self.promotions.insert(token.clone(), promotion);
            return Ok(json!({"inspection":token,"path":path,"active_digest":digest(&current)}));
        }
        if method == "host.conflict.reconcile" {
            let pending = self
                .journal
                .pending_promotion
                .as_ref()
                .ok_or_else(invalid)?;
            let copy = self
                .journal
                .conflicts
                .get(&pending.copy)
                .ok_or_else(invalid)?;
            copy.verify()?;
            let state = if current.as_ref() == Some(&copy.bytes) {
                "committed"
            } else if digest(&current) == pending.baseline {
                "not_committed"
            } else {
                "stale"
            };
            let mut next = self.journal.clone();
            next.pending_promotion = None;
            self.persist(next)?;
            return Ok(json!({"state":state,"path":path}));
        }
        if self.journal.pending_promotion.is_some()
            || self.journal.drafts.values().any(|d| d.submitted.is_some())
        {
            return Err(Error::new(
                "commit_unknown",
                "reconcile_pending_write_first",
            ));
        }
        let promotion = self
            .promotions
            .get(text(p, "inspection")?)
            .ok_or_else(invalid)?
            .clone();
        if digest(&current) != promotion.baseline {
            return Err(Error::new("stale_snapshot", "active_version_changed"));
        }
        let copy = self
            .journal
            .conflicts
            .get(&promotion.copy)
            .ok_or_else(invalid)?
            .clone();
        copy.verify()?;
        let selected = paper::parse(&copy.bytes)?;
        if let Some(bytes) = current {
            self.preserve_conflicts(vec![ConflictCopy::new(
                path.clone(),
                "before-promotion",
                bytes,
            )])?;
        }
        let mut next = self.journal.clone();
        let (papers, errors) = self.vault()?.list()?;
        for other in papers
            .iter()
            .map(|s| &s.path)
            .chain(errors.iter().map(|(path, _)| path))
        {
            if other == &path {
                continue;
            }
            let bytes = self.vault()?.read_raw(other)?;
            if paper::parse(&bytes).is_ok_and(|p| p.code == selected.code) {
                let hash = format!("{:x}", Sha256::digest(&bytes));
                let preserved = next
                    .conflicts
                    .values()
                    .any(|c| c.path == *other && c.digest == hash && c.bytes == bytes);
                if !preserved {
                    return Err(Error::new(
                        "conflict_required",
                        "preserve_all_siblings_first",
                    ));
                }
                next.acknowledged.insert(other.clone(), hash);
            }
        }
        next.pending_promotion = Some(promotion.clone());
        self.persist(next)?;
        let acknowledged = self.journal.acknowledged.clone();
        self.vault
            .as_mut()
            .ok_or_else(invalid)?
            .acknowledge_preserved(acknowledged);
        let snapshot =
            self.vault()?
                .promote_raw(&path, &copy.bytes, promotion.baseline.as_deref())?;
        Ok(json!({"state":"submitted","paper":self.opened(snapshot)}))
    }
}

#[cfg(test)]
mod promotion_tests {
    use super::*;
    #[test]
    fn promotion_preserves_active_bytes_and_requires_fresh_sibling_proof() {
        let base = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../../../tests/test-vault")
            .canonicalize()
            .unwrap()
            .join(format!("promotion-{}", uuid::Uuid::new_v4()));
        let root = base.join("vault");
        let mut session = Session::open(&root, &base.join("private"), "en").unwrap();
        let params = json!({"storage_id":session.journal.storage_id,"generation":1});
        let draft = session
            .request("paper.create_draft", params.clone())
            .unwrap();
        let mut paper = session.edits[draft["edit_token"].as_str().unwrap()]
            .paper
            .clone();
        paper.pages[0].content = "selected conflict".into();
        let bytes = paper::render(&paper).unwrap();
        let path = format!("cache/{}.md", paper.code);
        let sibling = format!("cache/{} 2.md", paper.code);
        std::fs::write(root.join(&path), b"damaged active bytes\xff").unwrap();
        std::fs::write(root.join(&sibling), &bytes).unwrap();
        session
            .preserve_conflicts(vec![ConflictCopy::new(
                sibling.clone(),
                "sibling",
                bytes.clone(),
            )])
            .unwrap();
        let token = session.journal.conflicts.keys().next().unwrap().clone();
        let mut inspect_params = params.clone();
        inspect_params["token"] = json!(token);
        let mut inspect = session
            .request("host.conflict.inspect", inspect_params)
            .unwrap();
        inspect["storage_id"] = params["storage_id"].clone();
        inspect["generation"] = params["generation"].clone();
        let result = session
            .request("host.conflict.promote", inspect.clone())
            .unwrap();
        assert_eq!(result["state"], "submitted");
        assert!(session
            .journal
            .conflicts
            .values()
            .any(|c| c.bytes == b"damaged active bytes\xff"));
        assert_eq!(std::fs::read(root.join(&sibling)).unwrap(), bytes);
        assert_eq!(std::fs::read(root.join(&path)).unwrap(), bytes);
        assert_eq!(
            session
                .request("host.conflict.promote", inspect.clone())
                .unwrap_err()
                .code,
            "commit_unknown"
        );
        assert_eq!(
            session.request("host.conflict.reconcile", params).unwrap()["state"],
            "committed"
        );
        let snapshot = session.vault().unwrap().read(&path).unwrap();
        session
            .vault()
            .unwrap()
            .save(&path, &paper, Some(&snapshot))
            .unwrap();
        let snapshot = session.vault().unwrap().read(&path).unwrap();
        std::fs::write(root.join(&sibling), [bytes.as_slice(), b"changed"].concat()).unwrap();
        assert!(session
            .vault()
            .unwrap()
            .save(&path, &paper, Some(&snapshot))
            .is_err());
        std::fs::remove_dir_all(base).unwrap();
    }
}
