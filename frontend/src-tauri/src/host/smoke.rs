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
        if !session.journal.drafts.is_empty() || !session.vault.list()?.0.is_empty() {
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
