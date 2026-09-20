pub mod apple;
mod conflicts;
mod private;
pub mod router;
#[cfg(debug_assertions)]
pub mod smoke;
use crate::paper::{self, Error, Page, Paper, Reconcile, Result, Snapshot, Vault};
use private::Private;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::HashMap;
use std::path::Path;
use std::sync::Mutex;

const METHODS: &[&str] = &[
    "host.capabilities",
    "host.export",
    "paper.create_draft",
    "paper.open",
    "paper.save",
    "paper.reconcile_save",
    "library.query",
    "host.draft.put",
    "host.draft.list",
    "host.draft.read",
    "host.draft.discard",
    "host.locale.get",
    "host.locale.set",
    "host.conflict.inspect",
    "host.conflict.promote",
    "host.conflict.reconcile",
];

pub struct Host(pub Mutex<Result<router::Router>>);

// The lease travels with the blocking result, so cancellation also releases the switch guard.
pub struct PythonLease(tauri::AppHandle);
impl Drop for PythonLease {
    fn drop(&mut self) {
        use tauri::Manager;
        let state = self.0.state::<Host>();
        if let Ok(mut router) = state.0.lock() {
            if let Ok(router) = router.as_mut() {
                router.python_requests = router.python_requests.saturating_sub(1);
            }
        };
    }
}
pub enum Dispatch {
    Native(Value),
    Python(PythonLease),
}
pub async fn dispatch(app: tauri::AppHandle, method: String, params: Value) -> Result<Dispatch> {
    use tauri::Manager;
    tauri::async_runtime::spawn_blocking(move || {
        let state = app.state::<Host>();
        let result = {
            let mut state = state
                .0
                .lock()
                .map_err(|_| Error::new("host_unavailable", "restart_to_recover"))?;
            state
                .as_mut()
                .map_err(|e| e.clone())?
                .request(&method, params)?
        };
        match result {
            None => Ok(Dispatch::Python(PythonLease(app.clone()))),
            Some(value) => {
                // System panels must not hold the storage queue needed by background drafts.
                let value = match value.get("native_export") {
                    Some(request) => {
                        let result = apple::call(request.clone())?;
                        if !matches!(result["state"].as_str(), Some("exported" | "cancelled")) {
                            return Err(Error::new("export_failed", "system_export_failed"));
                        }
                        result
                    }
                    None => value,
                };
                Ok(Dispatch::Native(value))
            }
        }
    })
    .await
    .map_err(|_| Error::new("commit_unknown", "worker_result_unknown"))?
}

#[derive(Clone)]
struct Edit {
    paper: Paper,
    path: String,
    baseline: Option<Snapshot>,
}
#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Journal {
    version: u32,
    storage_id: String,
    locale: String,
    drafts: HashMap<String, Draft>,
    #[serde(default)]
    conflicts: HashMap<String, conflicts::ConflictCopy>,
    #[serde(default)]
    acknowledged: HashMap<String, String>,
    #[serde(default)]
    pending_promotion: Option<conflicts::Promotion>,
}
#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Draft {
    revision: u64,
    raw: Value,
    paper: Paper,
    target_path: String,
    source_digest: Option<String>,
    submitted: Option<Paper>,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Editable {
    display_name: Option<String>,
    tags: Vec<String>,
    pages: Vec<Page>,
}

pub struct Session {
    private: Private,
    journal: Journal,
    vault: Option<Vault>,
    edits: HashMap<String, Edit>,
    repairs: HashMap<String, Vec<u8>>,
    reconciled: HashMap<String, String>,
    promotions: HashMap<String, conflicts::Promotion>,
    generation: u64,
    recovery_writable: bool,
}

fn invalid() -> Error {
    Error::new("validation_failed", "invalid_host_request")
}
fn text<'a>(v: &'a Value, key: &str) -> Result<&'a str> {
    v[key].as_str().ok_or_else(invalid)
}
fn id(v: &Value, key: &str) -> Result<String> {
    let value = text(v, key)?;
    uuid::Uuid::parse_str(value).map_err(|_| invalid())?;
    Ok(value.into())
}
fn editable(p: &Paper) -> Value {
    json!({"display_name":p.display_name,"tags":p.tags,"pages":p.pages})
}
fn apply(p: &Paper, value: Value) -> Result<Paper> {
    let e: Editable = serde_json::from_value(value).map_err(|_| invalid())?;
    let mut p = p.clone();
    p.display_name = e.display_name;
    p.tags = e.tags;
    p.pages = e.pages;
    Ok(p)
}

impl Session {
    pub fn open(root: &Path, private_path: &Path, system_locale: &str) -> Result<Self> {
        Private::open(&root.join("cache"))?;
        Self::with_vault(Some(Vault::open(root)?), private_path, system_locale)
    }

    fn with_vault(vault: Option<Vault>, private_path: &Path, system_locale: &str) -> Result<Self> {
        let private = Private::open(private_path)?;
        #[cfg(target_os = "ios")]
        if apple::call(json!({"method":"exclude_backup","path":private_path}))?["state"]
            != "excluded"
        {
            return Err(Error::new(
                "recovery_unavailable",
                "backup_exclusion_failed",
            ));
        }

        let journal: Journal = match private.read()? {
            Some(value) => serde_json::from_value(value)
                .map_err(|_| Error::new("recovery_unavailable", "invalid_private_journal"))?,
            None => {
                let j = Journal {
                    version: 1,
                    storage_id: uuid::Uuid::new_v4().to_string(),
                    locale: if system_locale.starts_with("zh") {
                        "zh-CN"
                    } else {
                        "en"
                    }
                    .into(),
                    drafts: HashMap::new(),
                    conflicts: HashMap::new(),
                    acknowledged: HashMap::new(),
                    pending_promotion: None,
                };
                private.write(&serde_json::to_value(&j).map_err(|_| invalid())?)?;
                j
            }
        };
        if journal.version != 1
            || uuid::Uuid::parse_str(&journal.storage_id).is_err()
            || !["en", "zh-CN"].contains(&journal.locale.as_str())
        {
            return Err(invalid());
        }
        Ok(Self {
            private,
            journal,
            vault,
            edits: HashMap::new(),
            repairs: HashMap::new(),
            reconciled: HashMap::new(),
            promotions: HashMap::new(),
            generation: 1,
            recovery_writable: true,
        })
    }

    fn vault(&self) -> Result<&Vault> {
        self.vault
            .as_ref()
            .ok_or_else(|| Error::new("storage_unavailable", "connect_storage_before_file_access"))
    }

    fn persist(&mut self, next: Journal) -> Result<()> {
        if !self.recovery_writable {
            return Err(Error::new(
                "recovery_unavailable",
                "restart_to_inspect_private_journal",
            ));
        }
        if let Err(e) = self
            .private
            .write(&serde_json::to_value(&next).map_err(|_| invalid())?)
        {
            self.recovery_writable = false;
            return Err(e);
        }
        self.journal = next;
        Ok(())
    }
    pub fn capabilities(&self) -> Value {
        json!({"platform":if cfg!(target_os="ios") {"ios"} else {"macos"},
            "storage_id":self.journal.storage_id,"generation":self.generation,"backend":"rust","methods":METHODS})
    }
    fn dto(&mut self, edit: Edit) -> Value {
        let token = uuid::Uuid::new_v4().to_string();
        let p = &edit.paper;
        let result = json!({"path":edit.baseline.as_ref().map(|s| &s.path),"target_path":edit.path,
            "edit_token":token,"vault_locator":self.journal.storage_id,
            "source_digest":edit.baseline.as_ref().map(Snapshot::digest),"code":p.code,
            "created":p.created,"updated":p.updated,"display_name":p.display_name,"tags":p.tags,"pages":p.pages});
        self.edits.insert(token, edit);
        result
    }
    fn opened(&mut self, s: Snapshot) -> Value {
        self.dto(Edit {
            paper: s.paper.clone(),
            path: s.path.clone(),
            baseline: Some(s),
        })
    }
    pub fn request(&mut self, method: &str, mut p: Value) -> Result<Value> {
        if method == "host.capabilities" {
            return Ok(self.capabilities());
        }
        if !METHODS.contains(&method) {
            return Err(Error::new("unsupported_method", "method_unavailable"));
        }
        if p["storage_id"] != self.journal.storage_id || p["generation"] != self.generation {
            return Err(Error::new("stale_session", "storage_generation_changed"));
        }
        let map = p.as_object_mut().ok_or_else(invalid)?;
        map.remove("storage_id");
        map.remove("generation");
        match method {
            "host.export" => {
                if p["source"] == "raw" {
                    let raw = &p["raw"];
                    validate_raw(raw, text(raw, "code")?)?;
                    return Ok(
                        json!({"native_export":{"method":"export","content":serde_json::to_string_pretty(raw).map_err(|_|invalid())?}}),
                    );
                }
                let (bytes, extension) = match text(&p, "source")? {
                    "draft" => (
                        serde_json::to_vec_pretty(
                            self.journal
                                .drafts
                                .get(text(&p, "token")?)
                                .ok_or_else(invalid)?,
                        )
                        .map_err(|_| invalid())?,
                        "json",
                    ),
                    "paper" if self.repairs.contains_key(text(&p, "token")?) => {
                        (self.repairs[text(&p, "token")?].clone(), "md")
                    }
                    "paper" => {
                        let edit = self.edits.get(text(&p, "token")?).ok_or_else(invalid)?;
                        (
                            match &edit.baseline {
                                Some(s) => s.bytes.clone(),
                                None => paper::render(&edit.paper)?,
                            },
                            "md",
                        )
                    }
                    _ => return Err(invalid()),
                };
                let path = self.private.export_copy(&bytes, extension)?;
                Ok(json!({"native_export":{"method":"export","path":path}}))
            }
            "host.locale.get" => Ok(json!({"locale":self.journal.locale})),
            "host.locale.set" => {
                let locale = text(&p, "locale")?;
                if !["en", "zh-CN"].contains(&locale) {
                    return Err(invalid());
                }
                let mut next = self.journal.clone();
                next.locale = locale.into();
                self.persist(next)?;
                Ok(json!({"locale":self.journal.locale}))
            }
            "paper.create_draft" => {
                let (papers, errors) = self.vault()?.list()?;
                let prefix = format!("K-{}-", chrono::Local::now().format("%Y%m%d"));
                let mut used = std::collections::HashSet::new();
                let mut reserve = |code: &str| {
                    if code.starts_with(&prefix) {
                        if let Some(sequence) = paper::code_sequence(code) {
                            used.insert(sequence);
                        }
                    }
                };
                for snapshot in &papers {
                    reserve(&snapshot.paper.code);
                }
                for (path, _) in &errors {
                    if let Some(stem) = Path::new(path).file_stem().and_then(|s| s.to_str()) {
                        reserve(stem);
                    }
                    if let Ok(bytes) = self.vault()?.read_raw(path) {
                        if let Ok(paper) = paper::parse(&bytes) {
                            reserve(&paper.code);
                        }
                    }
                }
                for edit in self.edits.values() {
                    reserve(&edit.paper.code);
                }
                for draft in self.journal.drafts.values() {
                    reserve(&draft.paper.code);
                }
                let sequence = (1..1000).find(|n| !used.contains(n)).ok_or_else(invalid)?;
                let code = format!("{prefix}{sequence:03}");
                let now = chrono::Local::now().to_rfc3339_opts(chrono::SecondsFormat::Micros, true);
                let paper = Paper {
                    code: code.clone(),
                    created: now.clone(),
                    updated: now,
                    display_name: None,
                    legacy_title: None,
                    tags: vec![],
                    pages: vec![Page {
                        name: None,
                        content: String::new(),
                        r#type: None,
                    }],
                    extra_frontmatter: vec![],
                };
                Ok(self.dto(Edit {
                    paper,
                    path: format!("cache/{code}.md"),
                    baseline: None,
                }))
            }
            "paper.open" => match self.vault()?.read(text(&p, "path")?) {
                Ok(s) => Ok(json!({"state":"opened","paper":self.opened(s)})),
                Err(e) if e.code == "repair_required" => {
                    let token = uuid::Uuid::new_v4().to_string();
                    self.repairs
                        .insert(token.clone(), self.vault()?.read_raw(text(&p, "path")?)?);
                    Ok(
                        json!({"state":"repair_required","repair":{"origin":"open","path":text(&p,"path")?,
                        "reason":e.reason,"page_number":e.page_number,"export_token":token}}),
                    )
                }
                Err(e) => Err(e),
            },
            "library.query" => {
                if p.get("scope").is_some_and(|s| s != "active") {
                    return Err(invalid());
                }
                let (mut papers, errors) =
                    self.vault()?.search(p["query"].as_str().unwrap_or(""))?;
                papers.sort_by(|a, b| {
                    b.paper
                        .updated
                        .cmp(&a.paper.updated)
                        .then(a.path.cmp(&b.path))
                });
                let entries:Vec<_> = papers.iter().map(|s| json!({"path":s.path,"code":s.paper.code,
                    "display_name":s.paper.display_name,"folder":s.path.strip_prefix("cache/").and_then(|p| p.rsplit_once('/').map(|v|v.0)),
                    "tags":s.paper.tags,"preview":s.paper.pages.iter().map(|p|p.content.as_str()).collect::<Vec<_>>().join("\n").chars().take(160).collect::<String>(),
                    "page_count":s.paper.pages.len(),"page_names":s.paper.pages.iter().filter_map(|p|p.name.as_ref()).collect::<Vec<_>>(),
                    "created":s.paper.created,"updated":s.paper.updated,"trashed":false,"repair_reason":null})).collect();
                let mut folders: Vec<_> = entries
                    .iter()
                    .filter_map(|e| e["folder"].as_str().map(str::to_owned))
                    .collect();
                folders.sort();
                folders.dedup();
                Ok(
                    json!({"scope":"active","entries":entries,"errors":errors.iter().map(|(path,e)|json!({"path":path,"reason":e.reason})).collect::<Vec<_>>(),
                    "folders":folders,"trash_folders":[],"trash_count":0,"vault_locator":self.journal.storage_id,"index_state":"not_applicable"}),
                )
            }
            "host.draft.put" => {
                let token = id(&p, "draft_id")?;
                let revision = p["revision"]
                    .as_u64()
                    .filter(|n| *n > 0)
                    .ok_or_else(invalid)?;
                if p["edit_token"].is_null() {
                    let old = self.journal.drafts.get(&token).ok_or_else(invalid)?;
                    validate_raw(&p["raw"], &old.paper.code)?;
                    if revision < old.revision || (revision == old.revision && old.raw != p["raw"])
                    {
                        return Err(Error::new("stale_revision", "draft_revision_changed"));
                    }
                    let mut next = self.journal.clone();
                    let draft = next.drafts.get_mut(&token).unwrap();
                    draft.raw = p["raw"].clone();
                    draft.revision = revision;
                    self.persist(next)?;
                    return Ok(json!({"token":token,"revision":revision}));
                }
                let edit = self
                    .edits
                    .get(text(&p, "edit_token")?)
                    .ok_or_else(invalid)?;
                validate_raw(&p["raw"], &edit.paper.code)?;
                let mut pending = None;
                if let Some(old) = self.journal.drafts.get(&token) {
                    if old.paper.code != edit.paper.code
                        || old.target_path != edit.path
                        || revision < old.revision
                        || (revision == old.revision && old.raw != p["raw"])
                    {
                        return Err(Error::new("stale_revision", "draft_revision_changed"));
                    }
                    if revision == old.revision
                        && old.paper == edit.paper
                        && old.source_digest == edit.baseline.as_ref().map(Snapshot::digest)
                        && p["settle"] != true
                    {
                        return Ok(json!({"token":token,"revision":revision}));
                    }
                    if let Some(submitted) = &old.submitted {
                        // A host-issued snapshot proves the observed outcome. Future saves still CAS it.
                        // Raw protection must never wait on provider discovery or file coordination.
                        let settled = edit.baseline.as_ref().is_some_and(|snapshot| {
                            paper::render(submitted).is_ok_and(|bytes| bytes == snapshot.bytes)
                        }) || (p["settle"] == true
                            && self.reconciled.get(&token).map(String::as_str)
                                == p["edit_token"].as_str());
                        if !settled {
                            pending = Some(submitted.clone());
                        }
                    }
                }
                let mut next = self.journal.clone();
                let previous = self.journal.drafts.get(&token);
                let (protected_paper, protected_digest) = if pending.is_some() {
                    let old = previous.ok_or_else(invalid)?;
                    (old.paper.clone(), old.source_digest.clone())
                } else {
                    (
                        edit.paper.clone(),
                        edit.baseline.as_ref().map(Snapshot::digest),
                    )
                };
                next.drafts.insert(
                    token.clone(),
                    Draft {
                        revision,
                        raw: p["raw"].clone(),
                        paper: protected_paper,
                        target_path: edit.path.clone(),
                        source_digest: protected_digest,
                        submitted: pending,
                    },
                );
                self.persist(next)?;
                Ok(json!({"token":token,"revision":revision}))
            }
            "host.draft.list" => Ok(
                json!({"drafts":self.journal.drafts.iter().map(|(token,d)|json!({"token":token,"revision":d.revision,
                "code":d.paper.code,"pending_save":d.submitted.is_some()})).collect::<Vec<_>>()}),
            ),
            "host.draft.read" => {
                let token = id(&p, "token")?;
                let d = self.journal.drafts.get(&token).ok_or_else(invalid)?.clone();
                if d.submitted.is_some() {
                    let dto = self.dto(Edit {
                        paper: d.paper.clone(),
                        path: d.target_path.clone(),
                        baseline: None,
                    });
                    return Ok(
                        json!({"token":token,"revision":d.revision,"raw":d.raw,"paper":dto,
                        "baseline":if d.source_digest.is_some(){editable(&d.paper)}else{Value::Null},"state":"commit_unknown"}),
                    );
                }
                let baseline = if d.source_digest.is_some() {
                    match self.vault().and_then(|v| v.read(&d.target_path)) {
                        Ok(s) if Some(s.digest()) == d.source_digest => Some(s),
                        _ => {
                            return Ok(
                                json!({"token":token,"revision":d.revision,"raw":d.raw,"state":"stale","paper":d.paper,"pending_save":d.submitted.is_some()}),
                            )
                        }
                    }
                } else {
                    None
                };
                let dto = self.dto(Edit {
                    paper: d.paper.clone(),
                    path: d.target_path,
                    baseline,
                });
                Ok(
                    json!({"token":token,"revision":d.revision,"raw":d.raw,"paper":dto,"baseline":if d.source_digest.is_some(){editable(&d.paper)}else{Value::Null},
                    "state":if d.submitted.is_some(){"commit_unknown"}else{"ready"}}),
                )
            }
            "host.draft.discard" => {
                let token = id(&p, "token")?;
                let Some(d) = self.journal.drafts.get(&token) else {
                    return Ok(json!({"state":"absent"}));
                };
                if p["revision"].as_u64() != Some(d.revision) {
                    return Err(Error::new("stale_revision", "newer_draft_retained"));
                }
                let mut next = self.journal.clone();
                next.drafts.remove(&token);
                self.persist(next)?;
                Ok(json!({"state":"removed"}))
            }
            "host.conflict.inspect" | "host.conflict.promote" | "host.conflict.reconcile" => {
                self.promote_request(method, &p)
            }
            "paper.save" => self.save(&p),
            "paper.reconcile_save" => self.reconcile(&p),
            _ => Err(invalid()),
        }
    }

    fn save(&mut self, p: &Value) -> Result<Value> {
        if self.journal.pending_promotion.is_some() {
            return Err(Error::new("commit_unknown", "reconcile_promotion_first"));
        }
        let token = id(p, "draft_id")?;
        let d = self.journal.drafts.get(&token).ok_or_else(invalid)?.clone();
        let edit = self
            .edits
            .get(text(p, "edit_token")?)
            .ok_or_else(invalid)?
            .clone();
        if p["vault_locator"] != self.journal.storage_id
            || p["revision"].as_u64() != Some(d.revision)
            || d.target_path != edit.path
            || d.source_digest != edit.baseline.as_ref().map(Snapshot::digest)
        {
            return Err(invalid());
        }
        if d.submitted.is_some() {
            return Err(Error::new("commit_unknown", "reconcile_pending_save_first"));
        }
        let mut submitted = apply(
            &edit.paper,
            json!({"display_name":p["display_name"],"tags":p["tags"],"pages":p["pages"]}),
        )?;
        submitted.updated =
            chrono::Local::now().to_rfc3339_opts(chrono::SecondsFormat::Micros, true);
        let submitted = paper::parse(&paper::render(&submitted)?)?;
        let mut next = self.journal.clone();
        next.drafts.get_mut(&token).unwrap().submitted = Some(submitted.clone());
        self.persist(next)?;
        match self
            .vault()?
            .save(&edit.path, &submitted, edit.baseline.as_ref())
        {
            Ok(s) => {
                // Leave the exact protected revision until the caller observes success and clears it.
                Ok(json!({"paper":self.opened(s),"warnings":[]}))
            }
            Err(e) => {
                if e.code != "commit_unknown" {
                    let mut next = self.journal.clone();
                    next.drafts.get_mut(&token).unwrap().submitted = None;
                    self.persist(next)?;
                }
                Err(e)
            }
        }
    }
    fn reconcile(&mut self, p: &Value) -> Result<Value> {
        let token = id(p, "draft_id")?;
        let d = self.journal.drafts.get(&token).ok_or_else(invalid)?.clone();
        let submitted = d.submitted.as_ref().ok_or_else(invalid)?;
        let outcome =
            self.vault()?
                .reconcile(&d.target_path, d.source_digest.as_deref(), submitted)?;
        let (state, dto) = match outcome {
            Reconcile::Committed(s) => ("committed", self.opened(s)),
            Reconcile::NotCommitted(baseline) => (
                "not_committed",
                self.dto(Edit {
                    paper: d.paper,
                    path: d.target_path,
                    baseline,
                }),
            ),
            Reconcile::Stale => {
                return Ok(
                    json!({"state":"stale","stale_reason":"third_content","index_state":"not_applicable"}),
                )
            }
        };
        if state == "not_committed" {
            self.reconciled
                .insert(token, text(&dto, "edit_token")?.to_owned());
        }
        Ok(json!({"state":state,"paper":dto,"index_state":"not_applicable"}))
    }
}

fn validate_raw(raw: &Value, code: &str) -> Result<()> {
    if raw["code"] != code || !raw["display_name"].is_string() || !raw["tags_text"].is_string() {
        return Err(invalid());
    }
    let pages = raw["pages"]
        .as_array()
        .filter(|p| !p.is_empty())
        .ok_or_else(invalid)?;
    for p in pages {
        if !(p["name"].is_null() || p["name"].is_string())
            || !p["content"].is_string()
            || !(p["type"].is_null()
                || matches!(p["type"].as_str(), Some("summary" | "snapshot" | "whisper")))
        {
            return Err(invalid());
        }
    }
    Ok(())
}

pub fn envelope(result: Result<Value>) -> Value {
    match result {
        Ok(value) => json!({"ok":true,"result":value}),
        Err(e) => {
            json!({"ok":false,"error":{"code":e.code,"layer":"rust_host","message":e.reason,"recovery":"inspect_or_export"}})
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn call(s: &mut Session, method: &str, mut p: Value) -> Result<Value> {
        p["storage_id"] = json!(s.journal.storage_id);
        p["generation"] = json!(s.generation);
        s.request(method, p)
    }
    #[test]
    fn local_creation_recovery_revision_and_cas() {
        let base = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../../../tests/test-vault")
            .canonicalize()
            .unwrap()
            .join(format!("host-{}", uuid::Uuid::new_v4()));
        let root = base.join("local");
        let private = base.join("private");
        let mut s = Session::open(&root, &private, "zh-Hans").unwrap();
        let storage = s.journal.storage_id.clone();
        let paper = call(&mut s, "paper.create_draft", json!({})).unwrap();
        let token = uuid::Uuid::new_v4().to_string();
        let raw = json!({"code":paper["code"],"display_name":"", "tags_text":"\"unfinished", "pages":[{"name":null,"content":"保留原稿","type":null}]});
        let mut put =
            json!({"draft_id":token,"revision":1,"edit_token":paper["edit_token"],"raw":raw});
        call(&mut s, "host.draft.put", put.clone()).unwrap();
        put["revision"] = json!(2);
        put["raw"]["pages"][0]["content"] = json!("newer");
        call(&mut s, "host.draft.put", put.clone()).unwrap();
        assert_eq!(
            call(
                &mut s,
                "host.draft.discard",
                json!({"token":token,"revision":1})
            )
            .unwrap_err()
            .code,
            "stale_revision"
        );
        drop(s);
        let mut s = Session::open(&root, &private, "en").unwrap();
        assert_eq!(s.journal.storage_id, storage);
        assert_eq!(s.journal.locale, "zh-CN");
        let restored = call(&mut s, "host.draft.read", json!({"token":token})).unwrap();
        assert_eq!(restored["raw"], put["raw"]);
        let p = restored["paper"].clone();
        let save = json!({"draft_id":token,"revision":2,"edit_token":p["edit_token"],"vault_locator":p["vault_locator"],
            "display_name":"Straße","tags":["é"],"pages":[{"name":null,"content":"newer","type":null}]});
        let saved = call(&mut s, "paper.save", save.clone()).unwrap();
        assert_eq!(
            call(&mut s, "paper.save", save).unwrap_err().code,
            "commit_unknown"
        );
        assert_eq!(
            call(&mut s, "paper.reconcile_save", json!({"draft_id":token})).unwrap()["state"],
            "committed"
        );
        let mut newer = put.clone();
        newer["revision"] = json!(3);
        newer["edit_token"] = saved["paper"]["edit_token"].clone();
        newer["raw"]["pages"][0]["content"] = json!("input after save");
        call(&mut s, "host.draft.put", newer).unwrap();
        assert!(s.journal.drafts[&token].submitted.is_none());
        assert_eq!(
            call(
                &mut s,
                "host.draft.discard",
                json!({"token":token,"revision":2})
            )
            .unwrap_err()
            .code,
            "stale_revision"
        );
        assert_eq!(
            call(&mut s, "library.query", json!({"query":"STRASSE"})).unwrap()["entries"]
                .as_array()
                .unwrap()
                .len(),
            1
        );
        call(
            &mut s,
            "host.draft.discard",
            json!({"token":token,"revision":3}),
        )
        .unwrap();
        assert!(s.journal.drafts.is_empty());
        let reopened = call(&mut s, "paper.open", json!({"path":saved["paper"]["path"]})).unwrap();
        assert_eq!(reopened["paper"]["pages"], saved["paper"]["pages"]);
        assert_eq!(
            s.request(
                "library.query",
                json!({"storage_id":storage,"generation":0})
            )
            .unwrap_err()
            .code,
            "stale_session"
        );
        // Broken Papers remain exportable and Unicode decimal filenames reserve their sequence.
        let broken_path = format!("cache/K-{}-٠٠٢.md", chrono::Local::now().format("%Y%m%d"));
        let broken = b"unparsed synthetic bytes\xff";
        std::fs::write(root.join(&broken_path), broken).unwrap();
        let repair = call(&mut s, "paper.open", json!({"path":broken_path})).unwrap();
        assert_eq!(repair["state"], "repair_required");
        assert_eq!(
            s.repairs[repair["repair"]["export_token"].as_str().unwrap()],
            broken
        );
        let next = call(&mut s, "paper.create_draft", json!({})).unwrap();
        assert!(next["code"].as_str().unwrap().ends_with("-003"));
        // Recovery failure precedes formal publication and retains the previous journal.
        std::fs::rename(&private, base.join("private-held")).unwrap();
        let before = std::fs::read(root.join(saved["paper"]["path"].as_str().unwrap())).unwrap();
        assert!(call(&mut s, "host.locale.set", json!({"locale":"en"})).is_err());
        assert_eq!(s.journal.locale, "zh-CN");
        assert_eq!(
            before,
            std::fs::read(root.join(saved["paper"]["path"].as_str().unwrap())).unwrap()
        );
    }
}
