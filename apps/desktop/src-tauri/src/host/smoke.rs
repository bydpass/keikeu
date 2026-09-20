//! Explicit debug-only native smoke on a UUID-scoped synthetic store.
use super::*;
use std::path::PathBuf;

pub fn run(support: &Path) {
    let args: Vec<_> = std::env::args().collect();
    let Some(index) = args.iter().position(|s| s == "--keikeu-native-smoke") else {
        return;
    };
    let Some(run) = args
        .get(index + 1)
        .filter(|s| uuid::Uuid::parse_str(s).is_ok())
    else {
        return;
    };
    let Some(stage) = args
        .get(index + 2)
        .filter(|s| ["seed", "recover"].contains(&s.as_str()))
    else {
        return;
    };
    let root = support.join(format!("CP3-{run}"));
    let result = exercise(&root, stage);
    let receipt = match result {
        Ok(()) => json!({"run":run,"stage":stage,"native_host_passed":true}),
        Err(e) => {
            json!({"run":run,"stage":stage,"native_host_passed":false,"code":e.code,"reason":e.reason})
        }
    };
    // Only this debug smoke creates these synthetic receipt files.
    if let Some(home) = std::env::var_os("HOME") {
        let path = PathBuf::from(home)
            .join("Documents")
            .join(format!("CP3-{run}-{stage}.json"));
        if let Ok(mut file) = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(path)
        {
            use std::io::Write;
            if file.write_all(receipt.to_string().as_bytes()).is_ok() {
                let _ = file.sync_all();
            }
        }
    }
}
fn call(s: &mut Session, method: &str, mut params: Value) -> Result<Value> {
    params["storage_id"] = json!(s.journal.storage_id);
    params["generation"] = json!(s.generation);
    s.request(method, params)
}
fn exercise(root: &Path, stage: &str) -> Result<()> {
    let mut session = Session::open(&root.join("Local"), &root.join("Recovery"), "en")?;
    if stage == "seed" {
        if !session.journal.drafts.is_empty() || !session.vault()?.list()?.0.is_empty() {
            return Err(invalid());
        }
        let p = call(&mut session, "paper.create_draft", json!({}))?;
        let token = uuid::Uuid::new_v4().to_string();
        let raw = json!({"code":p["code"],"display_name":"CP3 synthetic Straße","tags_text":"é",
            "pages":[{"name":"first","content":"合成测试正文","type":null},{"name":null,"content":"second page","type":"snapshot"}]});
        call(
            &mut session,
            "host.draft.put",
            json!({"draft_id":token,"revision":1,"edit_token":p["edit_token"],"raw":raw}),
        )?;
        let saved = call(
            &mut session,
            "paper.save",
            json!({"draft_id":token,"revision":1,"edit_token":p["edit_token"],"vault_locator":p["vault_locator"],
            "display_name":"CP3 synthetic Straße","tags":["é"],"pages":raw["pages"]}),
        )?;
        let opened = call(
            &mut session,
            "paper.open",
            json!({"path":saved["paper"]["path"]}),
        )?;
        if opened["paper"]["pages"] != raw["pages"] {
            return Err(invalid());
        }
        call(
            &mut session,
            "host.draft.discard",
            json!({"token":token,"revision":1}),
        )?;
        let mut raw = raw;
        raw["tags_text"] = json!("\"unfinished");
        raw["pages"][1]["content"] = json!("relaunch recovery bytes");
        call(
            &mut session,
            "host.draft.put",
            json!({"draft_id":token,"revision":2,"edit_token":saved["paper"]["edit_token"],"raw":raw}),
        )?;
        return Ok(());
    }
    let token = session
        .journal
        .drafts
        .keys()
        .next()
        .ok_or_else(invalid)?
        .clone();
    let recovered = call(&mut session, "host.draft.read", json!({"token":token}))?;
    if recovered["state"] != "ready"
        || recovered["raw"]["tags_text"] != "\"unfinished"
        || recovered["raw"]["pages"][1]["content"] != "relaunch recovery bytes"
    {
        return Err(invalid());
    }
    let found = call(&mut session, "library.query", json!({"query":"STRASSE"}))?;
    if found["entries"].as_array().map(Vec::len) != Some(1) {
        return Err(invalid());
    }
    if call(
        &mut session,
        "host.draft.discard",
        json!({"token":token,"revision":1}),
    )
    .is_ok()
    {
        return Err(invalid());
    }
    if session.journal.drafts[&token].revision != 2 {
        return Err(invalid());
    }
    Ok(())
}

/// Explicit debug-only worker; NSMetadataQuery callbacks need the app main queue running.
pub fn cloud_run(support: &Path) {
    let args: Vec<_> = std::env::args().collect();
    let Some(index) = args.iter().position(|s| s == "--keikeu-cloud-smoke") else {
        return;
    };
    let Some(run) = args
        .get(index + 1)
        .filter(|s| uuid::Uuid::parse_str(s).is_ok())
        .cloned()
    else {
        return;
    };
    let Some(stage) = args
        .get(index + 2)
        .filter(|s| ["seed", "update", "verify", "download"].contains(&s.as_str()))
        .cloned()
    else {
        return;
    };
    let attempt = args
        .get(index + 3)
        .filter(|s| uuid::Uuid::parse_str(s).is_ok())
        .map(|s| format!("-{s}"))
        .unwrap_or_default();
    let support = support.join(format!("CP4-{run}"));
    std::thread::spawn(move || {
        let result = cloud_exercise(&support, &run, &stage);
        let receipt = match result {
            Ok(value) => json!({"run":run,"stage":stage,"cloud_host_passed":true,"result":value}),
            Err(e) => {
                json!({"run":run,"stage":stage,"cloud_host_passed":false,"code":e.code,"reason":e.reason})
            }
        };
        if let Some(home) = std::env::var_os("HOME") {
            let path = PathBuf::from(home)
                .join("Documents")
                .join(format!("CP4-{run}-{stage}{attempt}.json"));
            if let Ok(mut file) = std::fs::OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(path)
            {
                use std::io::Write;
                if file.write_all(receipt.to_string().as_bytes()).is_ok() {
                    let _ = file.sync_all();
                }
            }
        }
    });
}
fn cloud_call(router: &mut router::Router, method: &str, mut p: Value) -> Result<Value> {
    let cap = router.capabilities();
    p["storage_id"] = cap["storage_id"].clone();
    p["generation"] = cap["generation"].clone();
    router
        .request(method, p)
        .map_err(|e| Error::new(&e.code, &format!("{method}: {}", e.reason)))?
        .ok_or_else(invalid)
}
fn cloud_exercise(support: &Path, run: &str, stage: &str) -> Result<Value> {
    let mut router = router::Router::open(support, None, "en")?;
    router.vault_name = format!("CP4-{run}");
    let inspection = cloud_call(
        &mut router,
        "host.storage.inspect",
        json!({"kind":"icloud"}),
    )?;
    cloud_call(
        &mut router,
        "host.storage.select",
        json!({"token":inspection["token"]}),
    )?;
    if stage == "download" {
        let status = cloud_call(&mut router, "host.cloud.status", json!({}))?;
        for item in status["items"].as_array().ok_or_else(invalid)? {
            if item["state"] == "not_downloaded" {
                cloud_call(
                    &mut router,
                    "host.cloud.download",
                    json!({"token":item["token"]}),
                )?;
            }
        }
        return Ok(json!({"items":status["items"]}));
    }
    let list = cloud_call(&mut router, "library.query", json!({"scope":"active"}))?;
    if !list["errors"].as_array().ok_or_else(invalid)?.is_empty() {
        return Err(Error::new("repair_required", "cloud_smoke_list_errors"));
    }
    if !list["cloud_items"]
        .as_array()
        .ok_or_else(invalid)?
        .is_empty()
    {
        return Err(Error::new(
            "not_downloaded",
            "cloud_smoke_download_required",
        ));
    }
    let entries = list["entries"].as_array().ok_or_else(invalid)?;
    if stage == "seed" && !entries.is_empty() {
        return Err(invalid());
    }
    if stage != "seed" && entries.len() != 1 {
        return Err(Error::new("not_ready", "await_cloud_roundtrip"));
    }
    let paper = if stage == "seed" {
        cloud_call(&mut router, "paper.create_draft", json!({}))?
    } else {
        cloud_call(
            &mut router,
            "paper.open",
            json!({"path":entries[0]["path"]}),
        )?["paper"]
            .clone()
    };
    if stage == "verify" {
        if paper["pages"][1]["content"] != "CP4 iPhone update" {
            return Err(Error::new("not_ready", "await_cloud_roundtrip"));
        }
        return Ok(
            json!({"pages":paper["pages"].as_array().ok_or_else(invalid)?.len(),"path":paper["path"]}),
        );
    }
    if stage == "update" && paper["pages"][1]["content"] != "CP4 Mac seed" {
        return Err(Error::new(
            "stale_snapshot",
            "cloud_smoke_seed_content_changed",
        ));
    }
    let content = if stage == "seed" {
        "CP4 Mac seed"
    } else {
        "CP4 iPhone update"
    };
    let raw = json!({"code":paper["code"],"display_name":"CP4 Straße","tags_text":"é", "pages":[
        {"name":"合成测试","content":"CP4 shared source","type":null},
        {"name":null,"content":content,"type":"snapshot"}]});
    let draft_id = uuid::Uuid::new_v4().to_string();
    cloud_call(
        &mut router,
        "host.draft.put",
        json!({"draft_id":draft_id,"revision":1,"edit_token":paper["edit_token"],"raw":raw}),
    )?;
    let saved = cloud_call(
        &mut router,
        "paper.save",
        json!({"draft_id":draft_id,"revision":1,"edit_token":paper["edit_token"],
        "vault_locator":paper["vault_locator"],"display_name":"CP4 Straße","tags":["é"],"pages":raw["pages"]}),
    )?;
    let outcome = cloud_call(
        &mut router,
        "paper.reconcile_save",
        json!({"draft_id":draft_id}),
    )?;
    if outcome["state"] != "committed" {
        return Err(invalid());
    }
    cloud_call(
        &mut router,
        "host.draft.discard",
        json!({"token":draft_id,"revision":1}),
    )?;
    let search = cloud_call(
        &mut router,
        "library.query",
        json!({"scope":"active","query":"STRASSE"}),
    )?;
    if search["entries"].as_array().ok_or_else(invalid)?.len() != 1 {
        return Err(invalid());
    }
    Ok(json!({"path":saved["paper"]["path"],"pages":2,"save_reconciled":true}))
}
