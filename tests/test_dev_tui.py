from __future__ import annotations

from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import signal
import subprocess
import sys
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _load_dev() -> ModuleType:
    loader = SourceFileLoader("keikeu_dev", str(ROOT / "dev"))
    spec = spec_from_loader(loader.name, loader)
    assert spec is not None
    module = module_from_spec(spec)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    return module


DEV = _load_dev()


def test_document_discovery_preview_search_and_containment(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    manual = repository / "docs" / "manual"
    design = repository / "docs" / "design"
    archive = repository / "docs" / "archive"
    hidden = design / ".od-skills"
    for directory in (manual, design, archive, hidden):
        directory.mkdir(parents=True, exist_ok=True)

    (repository / "README.md").write_text("# Root readme\n", encoding="utf-8")
    (repository / "CONTEXT.md").write_text("# Generated route\n", encoding="utf-8")
    (manual / "README.md").write_text("# Manual map\n", encoding="utf-8")
    guide = manual / "guide.html"
    guide.write_text(
        """<!doctype html><html><head><title>Guide title</title>
        <style>.secret { color: red; }</style><script>hidden()</script></head>
        <body><h1>Visible guide</h1><p>same</p><p>same</p>
        <p>commit_unknown recovery</p></body></html>""",
        encoding="utf-8",
    )
    (manual / "guide.pdf").write_bytes(b"pdf attachment")
    (manual / "theme.css").write_text("body {}", encoding="utf-8")
    (design / "design.html").write_text("<h1>Active design</h1>", encoding="utf-8")
    (archive / "old.md").write_text("# Old\n", encoding="utf-8")
    (hidden / "internal.md").write_text("# Hidden\n", encoding="utf-8")

    documents = DEV.discover_documents(repository)
    manual_paths = {
        item.relative_path for item in documents if item.group == "manual"
    }
    active_paths = {
        item.relative_path for item in documents if item.group == "active"
    }

    assert manual_paths == {"docs/manual/README.md", "docs/manual/guide.html"}
    assert active_paths == {"README.md", "docs/design/design.html"}
    parsed = next(item for item in documents if item.path == guide.resolve())
    assert parsed.title == "Guide title"
    assert "commit_unknown recovery" in parsed.body
    assert parsed.body.splitlines().count("same") == 2
    assert ".secret" not in parsed.body
    assert "hidden()" not in parsed.body
    assert parsed.pdf_path == (manual / "guide.pdf").resolve()
    assert DEV.search_documents(documents, "COMMIT_UNKNOWN") == [parsed]

    outside = tmp_path / "outside.md"
    outside.write_text("# outside\n", encoding="utf-8")
    escaped = manual / "escaped.md"
    escaped.symlink_to(outside)
    with pytest.raises(ValueError, match="escapes"):
        DEV.validate_document_path(escaped, repository)


def test_open_document_uses_native_argv_without_shell(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    document = repository / "docs" / "manual" / "README.md"
    document.parent.mkdir(parents=True)
    document.write_text("# Manual\n", encoding="utf-8")
    calls = []

    def fake_popen(command: list[str], **kwargs: object) -> object:
        calls.append((command, kwargs))
        return object()

    result = DEV.open_document(document, repository, popen=fake_popen)

    assert result is not None
    command, kwargs = calls[0]
    assert command == ["/usr/bin/open", str(document.resolve())]
    assert kwargs["cwd"] == repository.resolve()
    assert kwargs["shell"] is False


def test_spawn_task_uses_fixed_process_group_and_no_shell(tmp_path: Path) -> None:
    calls = []

    class FakeProcess:
        pid = 4321
        stdout = None
        killed = False

        def kill(self) -> None:
            self.killed = True

    process = FakeProcess()

    def fake_popen(command: list[str], **kwargs: object) -> FakeProcess:
        calls.append((command, kwargs))
        return process

    spawned, pgid = DEV.spawn_task(
        DEV.APP_COMMAND,
        root=tmp_path,
        popen=fake_popen,
        getpgid=lambda pid: pid,
    )

    assert spawned is process
    assert pgid == process.pid
    command, kwargs = calls[0]
    assert command == ["npm", "--prefix", "apps/desktop", "run", "tauri:dev"]
    assert kwargs["cwd"] == tmp_path.resolve()
    assert kwargs["shell"] is False
    assert kwargs["start_new_session"] is True
    assert kwargs["stdout"] == subprocess.PIPE
    assert kwargs["stderr"] == subprocess.STDOUT
    assert kwargs["encoding"] == "utf-8"

    with pytest.raises(RuntimeError, match="process group"):
        DEV.spawn_task(
            DEV.APP_COMMAND,
            root=tmp_path,
            popen=fake_popen,
            getpgid=lambda _pid: 999,
        )
    assert process.killed is True


def test_managed_task_waits_for_the_whole_group_and_signals_only_its_pgid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    group_alive = {"value": True}
    starts: list[str] = []
    signals: list[tuple[int, int]] = []

    class FinishedParent:
        pid = 4242
        stdout = None

        @staticmethod
        def poll() -> int:
            return 0

    task = DEV.ManagedTask()
    task.process = FinishedParent()
    task.pgid = 4242
    task.label = "应用"
    task.after_exit = "app"
    monkeypatch.setattr(
        DEV, "process_group_alive", lambda pgid: bool(pgid) and group_alive["value"]
    )
    monkeypatch.setattr(task, "start_app", lambda: starts.append("app") or True)

    task.tick()
    assert starts == []
    assert task.pgid == 4242

    group_alive["value"] = False
    task.tick()
    assert starts == ["app"]
    assert task.pgid is None

    task.process = FinishedParent()
    task.pgid = 5151
    group_alive["value"] = True
    monkeypatch.setattr(
        DEV.os, "killpg", lambda pgid, sent_signal: signals.append((pgid, sent_signal))
    )
    assert task.send_signal(signal.SIGINT) is True
    assert signals == [(5151, signal.SIGINT)]


def test_managed_task_keeps_queued_action_when_launch_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class RunningParent:
        @staticmethod
        def poll() -> None:
            return None

    task = DEV.ManagedTask()
    task.process = RunningParent()
    task.pgid = 4242
    task.after_exit = "quit"
    monkeypatch.setattr(DEV, "process_group_alive", lambda _pgid: True)

    assert task.launch(DEV.APP_COMMAND, "应用") is False
    assert task.after_exit == "quit"


def test_confirmation_never_signals_a_replacement_process_group(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class RunningParent:
        @staticmethod
        def poll() -> None:
            return None

    signals: list[tuple[int, int]] = []
    ui = DEV.DevTui(object(), [])
    ui.task.process = RunningParent()
    ui.task.pgid = 1111
    monkeypatch.setattr(DEV, "process_group_alive", lambda _pgid: True)
    monkeypatch.setattr(
        DEV.os, "killpg", lambda pgid, sent_signal: signals.append((pgid, sent_signal))
    )

    ui._confirm_signal("强制终止？", signal.SIGKILL)
    assert ui.confirmation is not None
    _, action = ui.confirmation
    ui.task.pgid = 2222
    action()

    assert signals == []
    assert ui.task.logs[-1].endswith("任务已切换；未发送信号。")


def test_stop_and_kill_require_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class RunningParent:
        @staticmethod
        def poll() -> None:
            return None

    signals: list[tuple[int, str | None, int | None]] = []
    ui = DEV.DevTui(object(), [])
    ui.task.process = RunningParent()
    ui.task.pgid = 3131
    monkeypatch.setattr(DEV, "process_group_alive", lambda _pgid: True)
    monkeypatch.setattr(
        ui.task,
        "send_signal",
        lambda sent_signal, after_exit=None, expected_pgid=None: signals.append(
            (sent_signal, after_exit, expected_pgid)
        )
        or True,
    )

    ui.handle_key("s")
    assert signals == []
    ui.handle_key("y")
    ui.handle_key("K")
    assert signals == [(signal.SIGINT, None, 3131)]
    ui.handle_key("y")
    assert signals == [
        (signal.SIGINT, None, 3131),
        (signal.SIGKILL, None, 3131),
    ]


@pytest.mark.parametrize(("return_code", "expected_starts"), [(0, 1), (1, 0)])
def test_build_starts_app_only_after_success(
    monkeypatch: pytest.MonkeyPatch,
    return_code: int,
    expected_starts: int,
) -> None:
    class FinishedBuild:
        @staticmethod
        def poll() -> int:
            return return_code

    starts: list[bool] = []
    task = DEV.ManagedTask()
    task.process = FinishedBuild()
    task.pgid = 4141
    task.label = "Sidecar 构建"
    task.after_exit = "app-on-success"
    monkeypatch.setattr(DEV, "process_group_alive", lambda _pgid: False)
    monkeypatch.setattr(task, "start_app", lambda: starts.append(True) or True)

    task.tick()
    assert len(starts) == expected_starts


def test_document_list_refreshes_on_entry_and_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    refreshed = [
        DEV.Document(
            path=ROOT / "README.md",
            relative_path="README.md",
            title="Fresh",
            body="updated",
            group="active",
        )
    ]
    ui = DEV.DevTui(object(), [])
    monkeypatch.setattr(DEV, "discover_documents", lambda: refreshed)

    ui.handle_key("2")
    assert ui.documents == refreshed
    ui.documents = []
    ui.handle_key("/")
    assert ui.documents == refreshed


def test_keyboard_interrupt_uses_the_managed_quit_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class InterruptingScreen:
        @staticmethod
        def timeout(_milliseconds: int) -> None:
            pass

        @staticmethod
        def get_wch() -> str:
            raise KeyboardInterrupt

    ui = DEV.DevTui(InterruptingScreen(), [])
    quit_calls: list[bool] = []
    monkeypatch.setattr(DEV.curses, "curs_set", lambda _visibility: None)
    monkeypatch.setattr(ui, "draw", lambda: None)

    def quit_once() -> None:
        quit_calls.append(True)
        ui.task.exit_ready = True

    monkeypatch.setattr(ui, "_quit", quit_once)
    ui.run()
    assert quit_calls == [True]


def test_terminal_width_log_cleaning_and_memory_limit() -> None:
    assert DEV.cell_width("中文") == 4
    assert DEV.cell_width("e\u0301") == 1
    assert DEV.clip_cells("A中文B", 4) == "A中"
    assert DEV.wrap_cells("中文AB", 4) == ["中文", "AB"]
    assert DEV.clean_log_line("\x1b[31merror\x1b[0m\r\n") == "error"

    task = DEV.ManagedTask()
    for index in range(DEV.LOG_LIMIT + 5):
        task.log(str(index))
    assert len(task.logs) == DEV.LOG_LIMIT
    assert task.logs[-1].endswith(str(DEV.LOG_LIMIT + 4))


def test_fixed_commands_keep_sidecar_build_explicit() -> None:
    assert DEV.APP_COMMAND == ("npm", "--prefix", "apps/desktop", "run", "tauri:dev")
    assert DEV.BUILD_COMMAND == (
        str(ROOT / ".venv" / "bin" / "python"),
        "scripts/build_sidecar.py",
    )
