use super::*;
use std::path::PathBuf;

#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Selection {
    version: u32,
    local_id: String,
    cloud_id: Option<String>,
    account: Option<String>,
    locale: String,
    selected: String,
    generation: u64,
}
#[derive(Clone)]
struct Inspection {
    kind: String,
    account: Option<String>,
}

pub struct Router {
    support: PathBuf,
    private: Private,
    selection: Selection,
    session: Option<Session>,
    inspections: HashMap<String, Inspection>,
    file_tokens: HashMap<String, String>,
    pub python_requests: usize,
    writable: bool,
    pub(super) vault_name: String,
}
const STORAGE_METHODS: &[&str] = &[
    "host.capabilities",
    "host.storage.inspect",
    "host.storage.select",
    "host.locale.get",
    "host.locale.set",
];
const CLOUD_METHODS: &[&str] = &[
    "host.cloud.status",
    "host.cloud.download",
    "host.conflict.list",
    "host.conflict.preserve",
    "host.conflict.export",
    "host.conflict.inspect",
    "host.conflict.promote",
    "host.conflict.reconcile",
];

impl Router {
    pub fn open(support: &Path, local: Option<Session>, system_locale: &str) -> Result<Self> {
        let path = support.join("Host");
        let private = Private::open(&path)?;
        if apple::call(json!({"method":"exclude_backup","path":path}))?["state"] != "excluded" {
            return Err(Error::new(
                "recovery_unavailable",
                "backup_exclusion_failed",
            ));
        }
        let selection: Selection = match private.read()? {
            Some(v) => serde_json::from_value(v).map_err(|_| invalid())?,
            None => {
                let s = Selection {
                    version: 1,
                    local_id: local
                        .as_ref()
                        .map(|s| s.journal.storage_id.clone())
                        .unwrap_or_else(|| uuid::Uuid::new_v4().to_string()),
                    cloud_id: None,
                    account: None,
                    locale: local
                        .as_ref()
                        .map(|s| s.journal.locale.clone())
                        .unwrap_or_else(|| {
                            if system_locale.starts_with("zh") {
                                "zh-CN"
                            } else {
                                "en"
                            }
                            .into()
                        }),
                    selected: "local".into(),
                    generation: 1,
                };
                private.write(&serde_json::to_value(&s).map_err(|_| invalid())?)?;
                s
            }
        };
        if selection.version != 1
            || !["local", "icloud"].contains(&selection.selected.as_str())
            || !["zh-CN", "en"].contains(&selection.locale.as_str())
            || selection.generation == 0
            || uuid::Uuid::parse_str(&selection.local_id).is_err()
            || selection
                .cloud_id
                .as_ref()
                .is_some_and(|id| uuid::Uuid::parse_str(id).is_err())
            || (selection.selected == "icloud"
                && (selection.cloud_id.is_none() || selection.account.is_none()))
        {
            return Err(invalid());
        }
        let mut router = Self {
            support: support.into(),
            private,
            selection,
            session: local,
            inspections: HashMap::new(),
            file_tokens: HashMap::new(),
            python_requests: 0,
            writable: true,
            vault_name: "keikeu".into(),
        };
        if router.selection.selected == "icloud" {
            router.session = Some(router.cloud_recovery(
                router.selection.account.as_deref().ok_or_else(invalid)?,
                true,
            )?);
        }
        router.bind();
        Ok(router)
    }
    fn bind(&mut self) {
        if let Some(s) = self.session.as_mut() {
            s.generation = self.selection.generation;
        }
    }
    fn storage_id(&self) -> &str {
        if self.selection.selected == "icloud" {
            self.selection.cloud_id.as_deref().unwrap_or("")
        } else {
            &self.selection.local_id
        }
    }
    fn backend(&self) -> &str {
        if cfg!(target_os = "ios") || self.selection.selected == "icloud" {
            "rust"
        } else {
            "python"
        }
    }
    pub fn capabilities(&self) -> Value {
        let mut methods = STORAGE_METHODS.to_vec();
        if self.backend() == "rust" {
            methods.extend(
                METHODS
                    .iter()
                    .copied()
                    .filter(|m| !STORAGE_METHODS.contains(m)),
            );
        }
        if self.selection.selected == "icloud" {
            methods.extend(CLOUD_METHODS);
        }
        json!({"backend":self.backend(),"platform":if cfg!(target_os="ios") {"ios"}else{"macos"},
            "storage_id":self.storage_id(),"generation":self.selection.generation,"storage_kind":self.selection.selected,"methods":methods})
    }
    fn persist(&mut self, next: Selection) -> Result<()> {
        if !self.writable {
            return Err(Error::new(
                "selection_unknown",
                "restart_to_inspect_selection",
            ));
        }
        if let Err(e) = self
            .private
            .write(&serde_json::to_value(&next).map_err(|_| invalid())?)
        {
            self.writable = false;
            return Err(e);
        }
        self.selection = next;
        self.bind();
        Ok(())
    }
    fn native(&self, method: &str, params: Value, account: Option<&str>) -> Result<Value> {
        let mut p = params;
        p["method"] = json!(method);
        p["vault"] = json!(self.vault_name);
        if let Some(account) = account {
            p["account"] = json!(account);
        }
        let result = apple::call(p)?;
        if result["state"] == "unavailable" {
            return Err(Error::new(
                result["code"].as_str().unwrap_or("cloud_unavailable"),
                "cloud_unavailable_recovery_retained",
            ));
        }
        Ok(result)
    }
    fn cloud_recovery(&self, account: &str, existing: bool) -> Result<Session> {
        if account.len() != 64 || !account.bytes().all(|b| b.is_ascii_hexdigit()) {
            return Err(invalid());
        }
        let path = self.support.join("CloudRecovery").join(account);
        if existing && Private::open(&path)?.read()?.is_none() {
            return Err(Error::new("recovery_unavailable", "cloud_recovery_missing"));
        }
        let session = Session::with_vault(None, &path, &self.selection.locale)?;
        if existing && self.selection.cloud_id.as_deref() != Some(&session.journal.storage_id) {
            return Err(Error::new(
                "stale_session",
                "cloud_recovery_identity_changed",
            ));
        }
        Ok(session)
    }
    fn attach_cloud(&mut self, initialize: bool, account: &str) -> Result<Session> {
        let info = self.native("cloud.inspect", json!({}), Some(account))?;
        let container = PathBuf::from(text(&info, "container")?);
        let relative = PathBuf::from("Documents").join(&self.vault_name);
        let vault = apple::coordinate(
            json!({"root":container,"paths":[],"initialize":initialize}),
            || Vault::open_apple_container(&container, &relative, initialize),
        )?;
        let existing =
            self.selection.account.as_deref() == Some(account) && self.selection.cloud_id.is_some();
        let mut session = self.cloud_recovery(account, existing)?;
        session.vault = Some(vault);
        Ok(session)
    }
    fn select(&mut self, p: &Value) -> Result<Value> {
        if self.python_requests != 0
            || self.session.as_ref().is_some_and(|s| {
                s.journal.pending_promotion.is_some()
                    || s.journal.drafts.values().any(|d| d.submitted.is_some())
            })
        {
            return Err(Error::new(
                "pending_write",
                "reconcile_before_storage_switch",
            ));
        }
        let inspection = self
            .inspections
            .get(text(p, "token")?)
            .ok_or_else(invalid)?
            .clone();
        if inspection.kind == self.selection.selected
            && (inspection.kind == "local" || inspection.account == self.selection.account)
        {
            return Ok(self.capabilities());
        }
        let prepared = if inspection.kind == "icloud" {
            Some(self.attach_cloud(true, inspection.account.as_deref().ok_or_else(invalid)?)?)
        } else if cfg!(target_os = "ios") {
            Some(Session::open(
                &self.support.join("LocalVault"),
                &self.support.join("Recovery"),
                &self.selection.locale,
            )?)
        } else {
            None
        };
        let mut next = self.selection.clone();
        next.generation = next.generation.checked_add(1).ok_or_else(invalid)?;
        next.selected = inspection.kind;
        if next.selected == "icloud" {
            next.cloud_id = Some(
                prepared
                    .as_ref()
                    .ok_or_else(invalid)?
                    .journal
                    .storage_id
                    .clone(),
            );
            next.account = inspection.account;
        } else if let Some(s) = &prepared {
            if next.local_id != s.journal.storage_id {
                return Err(Error::new(
                    "stale_session",
                    "local_recovery_identity_changed",
                ));
            }
        }
        self.persist(next)?;
        self.session = prepared;
        self.bind();
        self.inspections.clear();
        self.file_tokens.clear();
        Ok(self.capabilities())
    }

    /// None means unchanged desktop Python dispatch; the caller must balance python_requests.
    pub fn request(&mut self, method: &str, p: Value) -> Result<Option<Value>> {
        if !self.writable {
            return Err(Error::new(
                "selection_unknown",
                "restart_to_inspect_selection",
            ));
        }
        if method == "host.capabilities" {
            return Ok(Some(self.capabilities()));
        }
        if method.starts_with("host.")
            || self.backend() == "rust"
            || p.get("storage_id").is_some()
            || p.get("generation").is_some()
        {
            if p["storage_id"] != self.storage_id()
                || p["generation"].as_u64() != Some(self.selection.generation)
            {
                return Err(Error::new("stale_session", "storage_generation_changed"));
            }
        }
        let result = match method {
            "host.locale.get" => json!({"locale":self.selection.locale}),
            "host.locale.set" => {
                let locale = text(&p, "locale")?;
                if !["zh-CN", "en"].contains(&locale) {
                    return Err(invalid());
                }
                let mut next = self.selection.clone();
                next.locale = locale.into();
                self.persist(next)?;
                json!({"locale":self.selection.locale})
            }
            "host.storage.inspect" => {
                let kind = text(&p, "kind")?;
                let account = match kind {
                    "local" => None,
                    "icloud" => Some(
                        text(&self.native("cloud.inspect", json!({}), None)?, "account")?
                            .to_owned(),
                    ),
                    _ => return Err(invalid()),
                };
                let token = uuid::Uuid::new_v4().to_string();
                self.inspections.insert(
                    token.clone(),
                    Inspection {
                        kind: kind.into(),
                        account,
                    },
                );
                json!({"state":"ready","token":token,"kind":kind})
            }
            "host.storage.select" => self.select(&p)?,
            "host.conflict.list" | "host.conflict.export"
                if self.selection.selected == "icloud" =>
            {
                self.session
                    .as_ref()
                    .ok_or_else(invalid)?
                    .conflict_request(method, &p)?
            }
            "host.conflict.preserve" if self.selection.selected == "icloud" => {
                self.preserve_conflicts()?
            }
            "host.cloud.status" if self.selection.selected == "icloud" => {
                let result =
                    self.native("cloud.status", json!({}), self.selection.account.as_deref())?;
                let mut items = result["items"].as_array().ok_or_else(invalid)?.clone();
                for item in &mut items {
                    let path = text(item, "path")?.to_owned();
                    let token = uuid::Uuid::new_v4().to_string();
                    self.file_tokens.insert(token.clone(), path);
                    item["token"] = json!(token);
                }
                json!({"state":"ready","items":items})
            }
            "host.cloud.download" if self.selection.selected == "icloud" => {
                let path = self
                    .file_tokens
                    .get(text(&p, "token")?)
                    .ok_or_else(invalid)?;
                self.native(
                    "cloud.download",
                    json!({"path":path}),
                    self.selection.account.as_deref(),
                )?
            }
            _ if self.backend() == "python" => {
                if method.starts_with("host.") {
                    return Err(Error::new("unsupported_method", "method_unavailable"));
                }
                self.python_requests += 1;
                return Ok(None);
            }
            _ if self.selection.selected == "icloud" => self.cloud_request(method, p)?,
            _ => self
                .session
                .as_mut()
                .ok_or_else(invalid)?
                .request(method, p)?,
        };
        Ok(Some(result))
    }
    fn preserve_conflicts(&mut self) -> Result<Value> {
        use super::conflicts::ConflictCopy;
        let account = self.selection.account.clone().ok_or_else(invalid)?;
        let info = self.native("cloud.inspect", json!({}), Some(&account))?;
        let found = self.native("cloud.conflicts", json!({}), Some(&account))?;
        let items = found["items"].as_array().ok_or_else(invalid)?;
        if items.iter().any(|i| i["state"] != "available") {
            return Err(Error::new(
                "not_downloaded",
                "download_all_versions_before_preservation",
            ));
        }
        let paths: Vec<String> = items
            .iter()
            .map(|i| text(i, "path").map(str::to_owned))
            .collect::<Result<_>>()?;
        let versions = found["versions"].as_array().ok_or_else(invalid)?;
        let mut copies = Vec::new();
        let mut preserved = Vec::new();
        for version in versions {
            let token = text(version, "token")?;
            let value =
                self.native("cloud.version.read", json!({"token":token}), Some(&account))?;
            let bytes: Vec<u8> =
                serde_json::from_value(value["bytes"].clone()).map_err(|_| invalid())?;
            let copy = ConflictCopy::new(text(version, "path")?.into(), "native", bytes);
            if copy.digest != text(&value, "digest")? {
                return Err(invalid());
            }
            preserved.push(json!({"token":token,"digest":copy.digest}));
            copies.push(copy);
        }
        let session = self.session.as_mut().ok_or_else(invalid)?;
        if session.vault.is_none() {
            session.vault = Some(Vault::open_apple_container(
                Path::new(text(&info, "container")?),
                &PathBuf::from("Documents").join(&self.vault_name),
                false,
            )?);
        }
        session
            .vault
            .as_mut()
            .ok_or_else(invalid)?
            .set_coordinated_paths(paths.clone())?;
        apple::coordinate(json!({"root":info["root"],"paths":paths}), || {
            if apple::call(json!({"method":"cloud.identity"}))?["account"] != account {
                return Err(Error::new(
                    "icloud_account_changed",
                    "cloud_session_invalidated",
                ));
            }
            let vault = session.vault()?;
            let mut files = Vec::new();
            let mut counts: HashMap<String, usize> = HashMap::new();
            for path in &paths {
                let bytes = vault.read_raw(path)?;
                let paper = paper::parse(&bytes).ok();
                if let Some(paper) = &paper {
                    *counts.entry(paper.code.clone()).or_default() += 1;
                }
                files.push((path, bytes, paper));
            }
            for (path, bytes, paper) in files {
                let native = versions.iter().any(|v| v["path"] == *path);
                let sibling = paper.as_ref().is_some_and(|p| {
                    counts[&p.code] > 1
                        || Path::new(path).file_name().and_then(|n| n.to_str())
                            != Some(format!("{}.md", p.code).as_str())
                });
                if native || sibling {
                    copies.push(ConflictCopy::new(
                        path.clone(),
                        if sibling { "sibling" } else { "active" },
                        bytes,
                    ));
                }
            }
            session.preserve_conflicts(copies)
        })?;
        // Never resolve a native version before the complete raw batch has survived durable readback.
        if !preserved.is_empty() {
            self.native(
                "cloud.versions.resolve",
                json!({"preserved":serde_json::to_string(&preserved).map_err(|_| invalid())?}),
                Some(&account),
            )?;
        }
        self.session
            .as_ref()
            .ok_or_else(invalid)?
            .conflict_request("host.conflict.list", &json!({}))
    }
    fn cloud_request(&mut self, method: &str, p: Value) -> Result<Value> {
        // Snapshot export and private recovery listing never need a live provider.
        if matches!(
            method,
            "host.draft.list" | "host.draft.put" | "host.draft.discard" | "host.export"
        ) {
            return self
                .session
                .as_mut()
                .ok_or_else(invalid)?
                .request(method, p);
        }
        let recovery_only = method == "host.draft.read";
        let account = self.selection.account.clone().ok_or_else(invalid)?;
        let preflight = (|| -> Result<(Value, Value)> {
            Ok((
                self.native("cloud.inspect", json!({}), Some(&account))?,
                self.native("cloud.status", json!({}), Some(&account))?,
            ))
        })();
        let (info, status) = match preflight {
            Ok(v) => v,
            Err(e) => {
                let session = self.session.as_mut().ok_or_else(invalid)?;
                session.vault = None;
                if recovery_only {
                    return session.request(method, p);
                }
                return Err(e);
            }
        };
        let items = status["items"].as_array().ok_or_else(invalid)?;
        let mut paths: Vec<String> = items
            .iter()
            .filter(|i| i["state"] == "available")
            .map(|i| text(i, "path").map(str::to_owned))
            .collect::<Result<_>>()?;
        let unavailable: Vec<_> = items
            .iter()
            .filter(|i| i["state"] != "available")
            .cloned()
            .collect();
        if method != "library.query" && !unavailable.is_empty() {
            if recovery_only {
                let session = self.session.as_mut().ok_or_else(invalid)?;
                session.vault = None;
                return session.request(method, p);
            }
            return Err(Error::new(
                "not_downloaded",
                "download_cloud_items_before_file_operation",
            ));
        }
        if matches!(method, "paper.save" | "host.conflict.promote")
            && items.iter().any(|i| i["has_native_conflicts"] == true)
        {
            return Err(Error::new(
                "conflict_required",
                "preserve_native_versions_before_save",
            ));
        }
        let session = self.session.as_mut().ok_or_else(invalid)?;
        if session.vault.is_none() {
            session.vault = Some(Vault::open_apple_container(
                Path::new(text(&info, "container")?),
                &PathBuf::from("Documents").join(&self.vault_name),
                false,
            )?);
        }
        let promotion_path = if matches!(
            method,
            "host.conflict.inspect" | "host.conflict.promote" | "host.conflict.reconcile"
        ) {
            Some(session.promotion_path(method, &p)?)
        } else {
            None
        };
        if let Some(path) = &promotion_path {
            paths.push(path.clone());
        }
        let write = if method == "host.conflict.promote" {
            promotion_path
        } else if method == "paper.save" {
            Some(
                session
                    .edits
                    .get(text(&p, "edit_token")?)
                    .ok_or_else(invalid)?
                    .path
                    .clone(),
            )
        } else {
            None
        };
        if let Some(path) = &write {
            paths.push(path.clone());
        }
        session
            .vault
            .as_mut()
            .ok_or_else(invalid)?
            .set_coordinated_paths(paths.clone())?;
        session
            .vault
            .as_mut()
            .ok_or_else(invalid)?
            .acknowledge_preserved(session.journal.acknowledged.clone());
        let mut result = apple::coordinate(
            json!({"root":info["root"],"paths":paths,"write":write}),
            || {
                let identity = apple::call(json!({"method":"cloud.identity"}))?;
                if identity["account"] != account {
                    return Err(Error::new(
                        "icloud_account_changed",
                        "cloud_session_invalidated",
                    ));
                }
                session.request(method, p)
            },
        )?;
        let identity = apple::call(json!({"method":"cloud.identity"}));
        if !identity.is_ok_and(|value| value["account"] == account) {
            session.vault = None;
            return Err(Error::new(
                if write.is_some() {
                    "commit_unknown"
                } else {
                    "icloud_account_changed"
                },
                "account_changed_during_operation",
            ));
        }
        if method == "library.query" {
            result["cloud_items"] = json!(unavailable);
        }
        Ok(result)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn selection_is_persistent_and_rejects_stale_or_inflight_switches() {
        let base = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../../tests/test-vault")
            .canonicalize()
            .unwrap()
            .join(format!("router-{}", uuid::Uuid::new_v4()));
        let mut router = Router::open(&base, None, "en").unwrap();
        let initial = router.capabilities();
        let scope = json!({"storage_id":initial["storage_id"],"generation":initial["generation"],"kind":"local"});
        let inspection = router
            .request("host.storage.inspect", scope.clone())
            .unwrap()
            .unwrap();
        let mut select = scope.clone();
        select["token"] = inspection["token"].clone();
        router.python_requests = 1;
        assert_eq!(
            router
                .request("host.storage.select", select.clone())
                .unwrap_err()
                .code,
            "pending_write"
        );
        assert_eq!(router.capabilities(), initial);
        router.python_requests = 0;
        assert_eq!(
            router
                .request("host.storage.select", select)
                .unwrap()
                .unwrap(),
            initial
        );
        let mut next = router.selection.clone();
        next.generation += 1;
        router.persist(next).unwrap();
        assert_eq!(
            router
                .request("host.storage.inspect", scope.clone())
                .unwrap_err()
                .code,
            "stale_session"
        );
        assert_eq!(
            router.request("paper.save", scope).unwrap_err().code,
            "stale_session"
        );
        let final_cap = router.capabilities();
        drop(router);
        assert_eq!(
            Router::open(&base, None, "zh-CN").unwrap().capabilities(),
            final_cap
        );
        std::fs::remove_dir_all(base).unwrap();
    }
}
