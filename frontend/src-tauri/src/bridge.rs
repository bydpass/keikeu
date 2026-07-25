use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::sync::{mpsc, Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};
use tauri::AppHandle;
use tauri_plugin_shell::{
    process::{CommandChild, CommandEvent},
    ShellExt,
};

const PROTOCOL_VERSION: u64 = 1;
const SIDECAR_NAME: &str = "keikeu-sidecar";

#[derive(Clone, Debug, Deserialize, PartialEq, Serialize)]
pub struct BridgeError {
    pub code: String,
    pub message: String,
    pub recovery: String,
    pub layer: String,
}

impl BridgeError {
    pub(crate) fn host(code: &str, message: &str, recovery: &str) -> Self {
        Self {
            code: code.to_owned(),
            message: message.to_owned(),
            recovery: recovery.to_owned(),
            layer: "tauri_host".to_owned(),
        }
    }

    fn unavailable(message: &str) -> Self {
        Self::host("sidecar_unavailable", message, "restart_sidecar")
    }

    fn protocol(message: &str) -> Self {
        Self::host("protocol_mismatch", message, "restart_sidecar")
    }

    fn commit_unknown() -> Self {
        Self::host(
            "commit_unknown",
            "写入请求后的响应不可用；磁盘提交状态未知。",
            "restart_then_reload",
        )
    }

    fn invalid(message: &str) -> Self {
        Self::host("invalid_request", message, "correct_input")
    }
}

#[derive(Clone, Debug, PartialEq, Serialize)]
#[serde(tag = "state", rename_all = "snake_case")]
pub enum RuntimeStatus {
    Starting,
    Ready {
        app_version: String,
        core_version: String,
    },
    Blocked {
        error: BridgeError,
    },
    Stopped,
}

#[derive(Clone, Copy)]
struct Timeouts {
    hello: Duration,
    read: Duration,
    mutation: Duration,
    long_mutation: Duration,
}

impl Default for Timeouts {
    fn default() -> Self {
        Self {
            hello: Duration::from_secs(10),
            read: Duration::from_secs(20),
            mutation: Duration::from_secs(60),
            long_mutation: Duration::from_secs(600),
        }
    }
}

#[derive(Clone, Copy)]
struct RequestPolicy {
    mutation: bool,
    timeout: Duration,
}

fn public_policy(method: &str, timeouts: Timeouts) -> Option<RequestPolicy> {
    let mutation = matches!(
        method,
        "startup.load"
            | "vault.open"
            | "vault.initialize"
            | "vault.relocate"
            | "migration.run"
            | "paper.save"
            | "paper.soft_delete"
            | "library.rebuild"
            | "library.move"
            | "library.branch"
            | "library.soft_delete"
            | "library.restore"
            | "library.permanently_delete"
            | "library.create_folder"
            | "library.rename_folder"
            | "library.merge_folders"
            | "library.soft_delete_folder"
            | "library.restore_folder"
            | "library.permanently_delete_folder"
    );
    let known = mutation
        || matches!(
            method,
            "vault.inspect"
                | "migration.preflight"
                | "paper.create_draft"
                | "paper.open"
                | "flashcard.open"
                | "library.query"
        );
    if !known {
        return None;
    }
    let timeout = if matches!(method, "vault.relocate" | "migration.run") {
        timeouts.long_mutation
    } else if mutation {
        timeouts.mutation
    } else {
        timeouts.read
    };
    Some(RequestPolicy { mutation, timeout })
}

enum ChildEvent {
    Stdout(Vec<u8>),
    Stderr,
    Error,
    Terminated,
}

trait ChildControl: Send {
    fn write(&mut self, bytes: &[u8]) -> Result<(), ()>;
    fn kill(self: Box<Self>);
}

struct SpawnedSidecar {
    child: Box<dyn ChildControl>,
    events: mpsc::Receiver<ChildEvent>,
}

trait SidecarSpawner: Send + Sync {
    fn spawn(&self) -> Result<SpawnedSidecar, ()>;
}

struct TauriChild(Option<CommandChild>);

impl ChildControl for TauriChild {
    fn write(&mut self, bytes: &[u8]) -> Result<(), ()> {
        self.0.as_mut().ok_or(())?.write(bytes).map_err(|_| ())
    }

    fn kill(mut self: Box<Self>) {
        if let Some(child) = self.0.take() {
            let _ = child.kill();
        }
    }
}

struct TauriSpawner {
    app: AppHandle,
}

impl SidecarSpawner for TauriSpawner {
    fn spawn(&self) -> Result<SpawnedSidecar, ()> {
        let command = self.app.shell().sidecar(SIDECAR_NAME).map_err(|_| ())?;
        let (mut receiver, child) = command.spawn().map_err(|_| ())?;
        let (event_sender, events) = mpsc::channel();
        tauri::async_runtime::spawn(async move {
            while let Some(event) = receiver.recv().await {
                let event = match event {
                    CommandEvent::Stdout(line) => ChildEvent::Stdout(line),
                    CommandEvent::Stderr(_) => ChildEvent::Stderr,
                    CommandEvent::Error(_) => ChildEvent::Error,
                    CommandEvent::Terminated(_) => ChildEvent::Terminated,
                    _ => continue,
                };
                if event_sender.send(event).is_err() {
                    break;
                }
            }
        });
        Ok(SpawnedSidecar {
            child: Box::new(TauriChild(Some(child))),
            events,
        })
    }
}

#[derive(Clone, Default)]
struct SharedChild(Arc<Mutex<Option<Box<dyn ChildControl>>>>);

impl SharedChild {
    fn replace(&self, child: Box<dyn ChildControl>) {
        self.kill();
        if let Ok(mut current) = self.0.lock() {
            *current = Some(child);
        }
    }

    fn write(&self, bytes: &[u8]) -> Result<(), ()> {
        let mut current = self.0.lock().map_err(|_| ())?;
        current.as_mut().ok_or(())?.write(bytes)
    }

    fn kill(&self) {
        let child = self.0.lock().ok().and_then(|mut current| current.take());
        if let Some(child) = child {
            child.kill();
        }
    }
}

enum WorkerJob {
    Request {
        method: String,
        params: Value,
        reply: mpsc::SyncSender<Result<Value, BridgeError>>,
    },
    ResolveTarget {
        action: String,
        relative_target: String,
        reply: mpsc::SyncSender<Result<String, BridgeError>>,
    },
    Restart {
        reply: mpsc::SyncSender<RuntimeStatus>,
    },
    Shutdown {
        reply: mpsc::SyncSender<()>,
    },
}

#[derive(Clone)]
pub struct BridgeHandle {
    jobs: mpsc::Sender<WorkerJob>,
    status: Arc<Mutex<RuntimeStatus>>,
    child: SharedChild,
}

impl BridgeHandle {
    pub fn start(app: AppHandle) -> Self {
        Self::with_spawner(Arc::new(TauriSpawner { app }), Timeouts::default())
    }

    fn with_spawner(spawner: Arc<dyn SidecarSpawner>, timeouts: Timeouts) -> Self {
        let (jobs, receiver) = mpsc::channel();
        let status = Arc::new(Mutex::new(RuntimeStatus::Starting));
        let child = SharedChild::default();
        let worker_status = Arc::clone(&status);
        let worker_child = child.clone();
        let spawn_result = thread::Builder::new()
            .name("keikeu-sidecar-worker".to_owned())
            .spawn(move || {
                Worker::new(spawner, worker_status, worker_child, timeouts).run(receiver)
            });
        if spawn_result.is_err() {
            set_status(
                &status,
                RuntimeStatus::Blocked {
                    error: BridgeError::unavailable("无法启动本地 sidecar worker。"),
                },
            );
        }
        Self {
            jobs,
            status,
            child,
        }
    }

    pub fn status(&self) -> RuntimeStatus {
        self.status
            .lock()
            .map(|value| value.clone())
            .unwrap_or(RuntimeStatus::Blocked {
                error: BridgeError::unavailable("本地运行状态不可用。"),
            })
    }

    pub async fn request(&self, method: String, params: Value) -> Result<Value, BridgeError> {
        let jobs = self.jobs.clone();
        tauri::async_runtime::spawn_blocking(move || {
            let (reply, response) = mpsc::sync_channel(1);
            jobs.send(WorkerJob::Request {
                method,
                params,
                reply,
            })
            .map_err(|_| BridgeError::unavailable("Sidecar worker 已停止。"))?;
            response
                .recv()
                .map_err(|_| BridgeError::unavailable("Sidecar worker 未返回结果。"))?
        })
        .await
        .map_err(|_| BridgeError::unavailable("Sidecar worker join 失败。"))?
    }

    pub async fn resolve_target(
        &self,
        action: String,
        relative_target: String,
    ) -> Result<String, BridgeError> {
        let jobs = self.jobs.clone();
        tauri::async_runtime::spawn_blocking(move || {
            let (reply, response) = mpsc::sync_channel(1);
            jobs.send(WorkerJob::ResolveTarget {
                action,
                relative_target,
                reply,
            })
            .map_err(|_| BridgeError::unavailable("Sidecar worker 已停止。"))?;
            response
                .recv()
                .map_err(|_| BridgeError::unavailable("Sidecar worker 未返回系统目标。"))?
        })
        .await
        .map_err(|_| BridgeError::unavailable("Sidecar worker join 失败。"))?
    }

    pub async fn restart(&self) -> RuntimeStatus {
        let jobs = self.jobs.clone();
        let fallback = self.clone();
        tauri::async_runtime::spawn_blocking(move || {
            let (reply, response) = mpsc::sync_channel(1);
            if jobs.send(WorkerJob::Restart { reply }).is_err() {
                return fallback.status();
            }
            response.recv().unwrap_or_else(|_| fallback.status())
        })
        .await
        .unwrap_or_else(|_| self.status())
    }

    pub fn shutdown(&self) {
        self.child.kill();
        let (reply, response) = mpsc::sync_channel(1);
        if self.jobs.send(WorkerJob::Shutdown { reply }).is_ok() {
            let _ = response.recv_timeout(Duration::from_secs(2));
        }
        set_status(&self.status, RuntimeStatus::Stopped);
    }
}

struct Worker {
    spawner: Arc<dyn SidecarSpawner>,
    status: Arc<Mutex<RuntimeStatus>>,
    child: SharedChild,
    events: Option<mpsc::Receiver<ChildEvent>>,
    session_id: Option<String>,
    next_id: u64,
    timeouts: Timeouts,
}

impl Worker {
    fn new(
        spawner: Arc<dyn SidecarSpawner>,
        status: Arc<Mutex<RuntimeStatus>>,
        child: SharedChild,
        timeouts: Timeouts,
    ) -> Self {
        Self {
            spawner,
            status,
            child,
            events: None,
            session_id: None,
            next_id: 1,
            timeouts,
        }
    }

    fn run(mut self, jobs: mpsc::Receiver<WorkerJob>) {
        let _ = self.restart();
        while let Ok(job) = jobs.recv() {
            match job {
                WorkerJob::Request {
                    method,
                    params,
                    reply,
                } => {
                    let _ = reply.send(self.request(&method, params));
                }
                WorkerJob::ResolveTarget {
                    action,
                    relative_target,
                    reply,
                } => {
                    let _ = reply.send(self.resolve_target(&action, &relative_target));
                }
                WorkerJob::Restart { reply } => {
                    let _ = self.restart();
                    let _ = reply.send(current_status(&self.status));
                }
                WorkerJob::Shutdown { reply } => {
                    self.stop();
                    let _ = reply.send(());
                    return;
                }
            }
        }
        self.stop();
    }

    fn restart(&mut self) -> Result<(), BridgeError> {
        self.child.kill();
        self.events = None;
        self.session_id = None;
        self.next_id = 1;
        set_status(&self.status, RuntimeStatus::Starting);

        let spawned = self.spawner.spawn().map_err(|_| {
            let error = BridgeError::unavailable("无法启动打包的 Python sidecar。");
            self.block(error.clone());
            error
        })?;
        self.child.replace(spawned.child);
        self.events = Some(spawned.events);

        let id = self.take_id();
        let payload = json!({
            "v": PROTOCOL_VERSION,
            "id": id,
            "method": "system.hello",
            "params": {},
        });
        let response = self.send_and_wait(payload, id, false, self.timeouts.hello)?;
        let result = response
            .get("result")
            .and_then(Value::as_object)
            .ok_or_else(|| self.protocol_block("Sidecar hello 缺少 result。"))?;
        if result.get("protocol_version").and_then(Value::as_u64) != Some(PROTOCOL_VERSION) {
            return Err(self.protocol_block("Sidecar 协议版本不兼容。"));
        }
        let session_id = result
            .get("session_id")
            .and_then(Value::as_str)
            .filter(|value| !value.is_empty())
            .ok_or_else(|| self.protocol_block("Sidecar hello 缺少 session。"))?
            .to_owned();
        let app_version = result
            .get("app_version")
            .and_then(Value::as_str)
            .ok_or_else(|| self.protocol_block("Sidecar hello 缺少应用版本。"))?
            .to_owned();
        let core_version = result
            .get("core_version")
            .and_then(Value::as_str)
            .ok_or_else(|| self.protocol_block("Sidecar hello 缺少 Core 版本。"))?
            .to_owned();
        self.session_id = Some(session_id);
        set_status(
            &self.status,
            RuntimeStatus::Ready {
                app_version,
                core_version,
            },
        );
        Ok(())
    }

    fn request(&mut self, method: &str, params: Value) -> Result<Value, BridgeError> {
        let policy = public_policy(method, self.timeouts)
            .ok_or_else(|| BridgeError::invalid("Rust host 不允许此 bridge method。"))?;
        if !params.is_object() {
            return Err(BridgeError::invalid("Bridge params 必须是 JSON object。"));
        }
        self.call(method, params, policy)
    }

    fn resolve_target(
        &mut self,
        action: &str,
        relative_target: &str,
    ) -> Result<String, BridgeError> {
        if !matches!(action, "open" | "reveal") {
            return Err(BridgeError::invalid("系统动作必须是 open 或 reveal。"));
        }
        let response = self.call(
            "system.resolve_target",
            json!({
                "action": action,
                "relative_target": relative_target,
            }),
            RequestPolicy {
                mutation: false,
                timeout: self.timeouts.read,
            },
        )?;
        if response.get("ok").and_then(Value::as_bool) == Some(false) {
            return response
                .get("error")
                .cloned()
                .and_then(|error| serde_json::from_value(error).ok())
                .ok_or_else(|| self.protocol_block("Sidecar error envelope 无效。"));
        }
        response
            .get("result")
            .and_then(|result| result.get("path"))
            .and_then(Value::as_str)
            .map(str::to_owned)
            .ok_or_else(|| self.protocol_block("Sidecar 未返回已验证系统目标。"))
    }

    fn call(
        &mut self,
        method: &str,
        params: Value,
        policy: RequestPolicy,
    ) -> Result<Value, BridgeError> {
        if !matches!(current_status(&self.status), RuntimeStatus::Ready { .. }) {
            return Err(status_error(&self.status));
        }
        let session_id = self
            .session_id
            .clone()
            .ok_or_else(|| self.protocol_block("Rust host 缺少当前 session。"))?;
        let id = self.take_id();
        let payload = json!({
            "v": PROTOCOL_VERSION,
            "id": id,
            "session_id": session_id,
            "method": method,
            "params": params,
        });
        self.send_and_wait(payload, id, policy.mutation, policy.timeout)
    }

    fn send_and_wait(
        &mut self,
        payload: Value,
        expected_id: u64,
        mutation: bool,
        timeout: Duration,
    ) -> Result<Value, BridgeError> {
        let mut bytes = serde_json::to_vec(&payload)
            .map_err(|_| BridgeError::invalid("无法编码 bridge request。"))?;
        bytes.push(b'\n');
        if self.child.write(&bytes).is_err() {
            return Err(self.response_lost(mutation, false));
        }

        let deadline = Instant::now() + timeout;
        loop {
            let remaining = deadline.saturating_duration_since(Instant::now());
            if remaining.is_zero() {
                return Err(self.response_lost(mutation, false));
            }
            let event = match self
                .events
                .as_ref()
                .ok_or(())
                .and_then(|events| events.recv_timeout(remaining).map_err(|_| ()))
            {
                Ok(event) => event,
                Err(()) => return Err(self.response_lost(mutation, false)),
            };
            match event {
                ChildEvent::Stderr => continue,
                ChildEvent::Error | ChildEvent::Terminated => {
                    return Err(self.response_lost(mutation, false));
                }
                ChildEvent::Stdout(line) => {
                    let response: Value = serde_json::from_slice(&line)
                        .map_err(|_| self.response_lost(mutation, true))?;
                    validate_response(&response, expected_id)
                        .map_err(|_| self.response_lost(mutation, true))?;
                    return Ok(response);
                }
            }
        }
    }

    fn response_lost(&mut self, mutation: bool, invalid_protocol: bool) -> BridgeError {
        let error = if mutation {
            BridgeError::commit_unknown()
        } else if invalid_protocol {
            BridgeError::protocol("Sidecar 返回了无法验证的协议响应。")
        } else {
            BridgeError::unavailable("Sidecar 响应超时、EOF 或进程已终止。")
        };
        self.block(error.clone());
        error
    }

    fn protocol_block(&mut self, message: &str) -> BridgeError {
        let error = BridgeError::protocol(message);
        self.block(error.clone());
        error
    }

    fn block(&mut self, error: BridgeError) {
        self.child.kill();
        self.events = None;
        self.session_id = None;
        set_status(&self.status, RuntimeStatus::Blocked { error });
    }

    fn stop(&mut self) {
        self.child.kill();
        self.events = None;
        self.session_id = None;
        set_status(&self.status, RuntimeStatus::Stopped);
    }

    fn take_id(&mut self) -> u64 {
        let id = self.next_id;
        self.next_id = self.next_id.saturating_add(1);
        id
    }
}

fn validate_response(response: &Value, expected_id: u64) -> Result<(), ()> {
    let object = response.as_object().ok_or(())?;
    if object.get("v").and_then(Value::as_u64) != Some(PROTOCOL_VERSION)
        || object.get("id").and_then(Value::as_u64) != Some(expected_id)
    {
        return Err(());
    }
    match object.get("ok").and_then(Value::as_bool) {
        Some(true) if object.contains_key("result") => Ok(()),
        Some(false) => {
            let error = object.get("error").and_then(Value::as_object).ok_or(())?;
            for field in ["code", "message", "recovery", "layer"] {
                if error.get(field).and_then(Value::as_str).is_none() {
                    return Err(());
                }
            }
            Ok(())
        }
        _ => Err(()),
    }
}

fn set_status(status: &Arc<Mutex<RuntimeStatus>>, value: RuntimeStatus) {
    if let Ok(mut current) = status.lock() {
        *current = value;
    }
}

fn current_status(status: &Arc<Mutex<RuntimeStatus>>) -> RuntimeStatus {
    status
        .lock()
        .map(|value| value.clone())
        .unwrap_or(RuntimeStatus::Blocked {
            error: BridgeError::unavailable("本地运行状态不可用。"),
        })
}

fn status_error(status: &Arc<Mutex<RuntimeStatus>>) -> BridgeError {
    match current_status(status) {
        RuntimeStatus::Blocked { error } => error,
        RuntimeStatus::Stopped => BridgeError::unavailable("Sidecar 已停止。"),
        RuntimeStatus::Starting => BridgeError::unavailable("Sidecar 尚未完成握手。"),
        RuntimeStatus::Ready { .. } => BridgeError::unavailable("Sidecar 状态发生竞争。"),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::VecDeque;
    use std::sync::atomic::{AtomicUsize, Ordering};

    struct FakePlan {
        events: Vec<ChildEvent>,
        write_fails: bool,
    }

    struct FakeSpawner {
        plans: Mutex<VecDeque<FakePlan>>,
        writes: Arc<Mutex<Vec<Value>>>,
        kills: Arc<AtomicUsize>,
    }

    impl FakeSpawner {
        fn new(plans: Vec<FakePlan>) -> Self {
            Self {
                plans: Mutex::new(plans.into()),
                writes: Arc::new(Mutex::new(Vec::new())),
                kills: Arc::new(AtomicUsize::new(0)),
            }
        }
    }

    struct FakeChild {
        writes: Arc<Mutex<Vec<Value>>>,
        kills: Arc<AtomicUsize>,
        sender: Option<mpsc::Sender<ChildEvent>>,
        write_fails: bool,
    }

    impl ChildControl for FakeChild {
        fn write(&mut self, bytes: &[u8]) -> Result<(), ()> {
            if self.write_fails {
                return Err(());
            }
            let value = serde_json::from_slice(bytes).map_err(|_| ())?;
            self.writes.lock().map_err(|_| ())?.push(value);
            Ok(())
        }

        fn kill(mut self: Box<Self>) {
            self.sender.take();
            self.kills.fetch_add(1, Ordering::SeqCst);
        }
    }

    impl SidecarSpawner for FakeSpawner {
        fn spawn(&self) -> Result<SpawnedSidecar, ()> {
            let plan = self.plans.lock().map_err(|_| ())?.pop_front().ok_or(())?;
            let (sender, events) = mpsc::channel();
            for event in plan.events {
                sender.send(event).map_err(|_| ())?;
            }
            Ok(SpawnedSidecar {
                child: Box::new(FakeChild {
                    writes: Arc::clone(&self.writes),
                    kills: Arc::clone(&self.kills),
                    sender: Some(sender),
                    write_fails: plan.write_fails,
                }),
                events,
            })
        }
    }

    fn hello(id: u64, session: &str) -> ChildEvent {
        ChildEvent::Stdout(
            serde_json::to_vec(&json!({
                "v": 1,
                "id": id,
                "ok": true,
                "result": {
                    "protocol_version": 1,
                    "session_id": session,
                    "app_version": "0.1.0",
                    "core_version": "paper-v3/index-v3",
                },
            }))
            .unwrap(),
        )
    }

    fn success(id: u64, result: Value) -> ChildEvent {
        ChildEvent::Stdout(
            serde_json::to_vec(&json!({
                "v": 1,
                "id": id,
                "ok": true,
                "result": result,
            }))
            .unwrap(),
        )
    }

    fn short_timeouts() -> Timeouts {
        Timeouts {
            hello: Duration::from_millis(100),
            read: Duration::from_millis(20),
            mutation: Duration::from_millis(20),
            long_mutation: Duration::from_millis(20),
        }
    }

    fn wait_ready(handle: &BridgeHandle) {
        let deadline = Instant::now() + Duration::from_secs(1);
        while Instant::now() < deadline {
            if matches!(handle.status(), RuntimeStatus::Ready { .. }) {
                return;
            }
            thread::sleep(Duration::from_millis(2));
        }
        panic!("bridge did not become ready: {:?}", handle.status());
    }

    #[test]
    fn incompatible_hello_blocks_before_business_requests() {
        let incompatible = ChildEvent::Stdout(
            serde_json::to_vec(&json!({
                "v": 1,
                "id": 1,
                "ok": true,
                "result": {
                    "protocol_version": 2,
                    "session_id": "session-a",
                    "app_version": "0.1.0",
                    "core_version": "paper-v3/index-v3",
                },
            }))
            .unwrap(),
        );
        let spawner = Arc::new(FakeSpawner::new(vec![FakePlan {
            events: vec![incompatible],
            write_fails: false,
        }]));
        let handle = BridgeHandle::with_spawner(spawner.clone(), short_timeouts());
        let deadline = Instant::now() + Duration::from_secs(1);
        while Instant::now() < deadline && !matches!(handle.status(), RuntimeStatus::Blocked { .. })
        {
            thread::sleep(Duration::from_millis(2));
        }

        let RuntimeStatus::Blocked { error } = handle.status() else {
            panic!("incompatible hello did not block");
        };
        assert_eq!(error.code, "protocol_mismatch");
        assert_eq!(spawner.writes.lock().unwrap().len(), 1);
        handle.shutdown();
    }

    #[test]
    fn handshake_adds_session_and_matches_response_id() {
        let spawner = Arc::new(FakeSpawner::new(vec![FakePlan {
            events: vec![hello(1, "session-a"), success(2, json!({"entries": []}))],
            write_fails: false,
        }]));
        let handle = BridgeHandle::with_spawner(spawner.clone(), short_timeouts());
        wait_ready(&handle);

        let response =
            tauri::async_runtime::block_on(handle.request("library.query".to_owned(), json!({})))
                .unwrap();
        assert_eq!(response["id"], 2);

        let writes = spawner.writes.lock().unwrap();
        assert_eq!(writes.len(), 2);
        assert_eq!(writes[0]["method"], "system.hello");
        assert_eq!(writes[1]["session_id"], "session-a");
        assert_eq!(writes[1]["method"], "library.query");
        handle.shutdown();
    }

    #[test]
    fn concurrent_callers_are_serialized_with_monotonic_ids() {
        let spawner = Arc::new(FakeSpawner::new(vec![FakePlan {
            events: vec![
                hello(1, "session-a"),
                success(2, json!({"request": 2})),
                success(3, json!({"request": 3})),
            ],
            write_fails: false,
        }]));
        let handle = BridgeHandle::with_spawner(spawner.clone(), short_timeouts());
        wait_ready(&handle);

        let first_handle = handle.clone();
        let first = thread::spawn(move || {
            tauri::async_runtime::block_on(
                first_handle.request("library.query".to_owned(), json!({})),
            )
            .unwrap()
        });
        let second_handle = handle.clone();
        let second = thread::spawn(move || {
            tauri::async_runtime::block_on(
                second_handle.request("library.query".to_owned(), json!({})),
            )
            .unwrap()
        });
        let mut ids = vec![first.join().unwrap()["id"].as_u64().unwrap()];
        ids.push(second.join().unwrap()["id"].as_u64().unwrap());
        ids.sort_unstable();
        assert_eq!(ids, vec![2, 3]);

        let writes = spawner.writes.lock().unwrap();
        assert_eq!(writes.len(), 3);
        assert_eq!(writes[1]["id"], 2);
        assert_eq!(writes[2]["id"], 3);
        drop(writes);
        handle.shutdown();
    }

    #[test]
    fn public_request_cannot_reach_internal_system_method() {
        let spawner = Arc::new(FakeSpawner::new(vec![FakePlan {
            events: vec![hello(1, "session-a")],
            write_fails: false,
        }]));
        let handle = BridgeHandle::with_spawner(spawner, short_timeouts());
        wait_ready(&handle);

        let error = tauri::async_runtime::block_on(handle.request(
            "system.resolve_target".to_owned(),
            json!({"action": "open", "relative_target": "P-001.md"}),
        ))
        .unwrap_err();
        assert_eq!(error.code, "invalid_request");
        handle.shutdown();
    }

    #[test]
    fn validated_system_target_stays_internal_to_rust() {
        let spawner = Arc::new(FakeSpawner::new(vec![FakePlan {
            events: vec![
                hello(1, "session-a"),
                success(2, json!({"path": "/tmp/test-vault/P-001.md"})),
            ],
            write_fails: false,
        }]));
        let handle = BridgeHandle::with_spawner(spawner.clone(), short_timeouts());
        wait_ready(&handle);

        let path = tauri::async_runtime::block_on(
            handle.resolve_target("reveal".to_owned(), "drafts/P-001.md".to_owned()),
        )
        .unwrap();
        assert_eq!(path, "/tmp/test-vault/P-001.md");

        let writes = spawner.writes.lock().unwrap();
        assert_eq!(writes[1]["method"], "system.resolve_target");
        assert_eq!(writes[1]["params"]["action"], "reveal");
        assert_eq!(writes[1]["params"]["relative_target"], "drafts/P-001.md");
        drop(writes);
        handle.shutdown();
    }

    #[test]
    fn mutation_response_loss_is_commit_unknown_and_never_retried() {
        let spawner = Arc::new(FakeSpawner::new(vec![FakePlan {
            events: vec![hello(1, "session-a")],
            write_fails: false,
        }]));
        let handle = BridgeHandle::with_spawner(spawner.clone(), short_timeouts());
        wait_ready(&handle);

        let error =
            tauri::async_runtime::block_on(handle.request("paper.save".to_owned(), json!({})))
                .unwrap_err();
        assert_eq!(error.code, "commit_unknown");
        assert!(matches!(handle.status(), RuntimeStatus::Blocked { .. }));
        assert_eq!(spawner.writes.lock().unwrap().len(), 2);
        handle.shutdown();
    }

    #[test]
    fn invalid_read_response_blocks_as_protocol_mismatch() {
        let spawner = Arc::new(FakeSpawner::new(vec![FakePlan {
            events: vec![hello(1, "session-a"), success(999, json!({}))],
            write_fails: false,
        }]));
        let handle = BridgeHandle::with_spawner(spawner, short_timeouts());
        wait_ready(&handle);

        let error =
            tauri::async_runtime::block_on(handle.request("library.query".to_owned(), json!({})))
                .unwrap_err();
        assert_eq!(error.code, "protocol_mismatch");
        handle.shutdown();
    }

    #[test]
    fn crash_during_read_is_sidecar_unavailable() {
        let spawner = Arc::new(FakeSpawner::new(vec![FakePlan {
            events: vec![hello(1, "session-a"), ChildEvent::Terminated],
            write_fails: false,
        }]));
        let handle = BridgeHandle::with_spawner(spawner, short_timeouts());
        wait_ready(&handle);

        let error =
            tauri::async_runtime::block_on(handle.request("library.query".to_owned(), json!({})))
                .unwrap_err();
        assert_eq!(error.code, "sidecar_unavailable");
        handle.shutdown();
    }

    #[test]
    fn restart_spawns_a_new_session_and_kills_the_old_child() {
        let spawner = Arc::new(FakeSpawner::new(vec![
            FakePlan {
                events: vec![hello(1, "session-a")],
                write_fails: false,
            },
            FakePlan {
                events: vec![hello(1, "session-b")],
                write_fails: false,
            },
        ]));
        let handle = BridgeHandle::with_spawner(spawner.clone(), short_timeouts());
        wait_ready(&handle);

        let status = tauri::async_runtime::block_on(handle.restart());
        assert!(matches!(status, RuntimeStatus::Ready { .. }));
        let writes = spawner.writes.lock().unwrap();
        assert_eq!(writes.len(), 2);
        assert_eq!(writes[0]["id"], 1);
        assert_eq!(writes[1]["id"], 1);
        assert!(spawner.kills.load(Ordering::SeqCst) >= 1);
        drop(writes);
        handle.shutdown();
    }

    #[test]
    fn shutdown_kills_child_and_marks_runtime_stopped() {
        let spawner = Arc::new(FakeSpawner::new(vec![FakePlan {
            events: vec![hello(1, "session-a")],
            write_fails: false,
        }]));
        let handle = BridgeHandle::with_spawner(spawner.clone(), short_timeouts());
        wait_ready(&handle);

        handle.shutdown();

        assert_eq!(handle.status(), RuntimeStatus::Stopped);
        assert!(spawner.kills.load(Ordering::SeqCst) >= 1);
    }
}
