import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import tauriConfig from "../src-tauri/tauri.conf.json";
import App from "./App.vue";
import PrototypeView from "./PrototypeView.vue";
import {
  bridgeRequest,
  confirmDiscardChanges,
  getRuntimeStatus,
  registerWindowCloseGuard,
  restartSidecar,
} from "./bridge.js";

vi.mock("./bridge.js", () => ({
  bridgeRequest: vi.fn(),
  chooseVaultDirectory: vi.fn(),
  confirmDiscardChanges: vi.fn(),
  getRuntimeStatus: vi.fn(),
  openSystemTarget: vi.fn(),
  registerWindowCloseGuard: vi.fn(),
  restartSidecar: vi.fn(),
}));

const runtime = {
  state: "ready",
  app_version: "0.1.0",
  core_version: "paper-v4/index-v4",
};
const draft = {
  path: null,
  edit_token: "edit-1",
  code: "K-20260802-001",
  display_name: null,
  tags: [],
  pages: [{ name: null, content: "Draft", type: null }],
  created: "2026-08-02T12:00:00",
  updated: "2026-08-02T12:00:00",
  vault_locator: "vault-v1:test",
  target_path: "cache/K-20260802-001.md",
  source_digest: null,
};
const libraryEntry = {
  path: "cache/Ideas/K-20260820-002.md",
  code: "K-20260820-002",
  display_name: "Pending mutation",
  folder: "Ideas",
  tags: [],
  preview: "Keep the component mounted until the result is known.",
  page_count: 1,
  page_names: [],
  created: "2026-08-20T12:00:00",
  updated: "2026-08-20T12:00:00",
  trashed: false,
  repair_reason: null,
};

function startup() {
  return {
    state: "ready",
    show_daily_card: false,
    vault_locator: "vault-v1:test",
    index_state: "current",
  };
}

function library(overrides = {}) {
  return {
    scope: "all",
    entries: [],
    folders: [],
    trash_folders: [],
    trash_count: 0,
    errors: [],
    vault_locator: "vault-v1:test",
    index_state: "current",
    ...overrides,
  };
}

function defaultBridge(method) {
  if (method === "startup.load") return startup();
  if (method === "paper.create_draft") return draft;
  if (method === "library.query") return library();
  throw new Error(method);
}

function buttonByText(wrapper, text) {
  const button = wrapper.findAll("button").find((item) => item.text() === text);
  if (!button) throw new Error(`button not found: ${text}`);
  return button;
}

function shellButtonByText(wrapper, text) {
  const button = wrapper.findAll(".app-shellbar button").find((item) => item.text() === text);
  if (!button) throw new Error(`Shell button not found: ${text}`);
  return button;
}

const mounted = [];
async function mountApp() {
  const wrapper = mount(App, { attachTo: document.body });
  mounted.push(wrapper);
  await flushPromises();
  return wrapper;
}

beforeEach(() => {
  vi.resetAllMocks();
  window.history.replaceState({}, "", "/");
  getRuntimeStatus.mockResolvedValue(runtime);
  restartSidecar.mockResolvedValue(runtime);
  confirmDiscardChanges.mockResolvedValue(true);
  registerWindowCloseGuard.mockResolvedValue(vi.fn());
  bridgeRequest.mockImplementation(defaultBridge);
});

afterEach(() => {
  while (mounted.length) mounted.pop().unmount();
});

describe("Road v0.7 desktop shell", () => {
  it("keeps the default desktop window portrait-safe at 720 × 900", () => {
    const mainWindow = tauriConfig.app.windows.find(({ label }) => label === "main");
    expect(mainWindow).toMatchObject({
      width: 720,
      height: 900,
      minWidth: 720,
      minHeight: 680,
    });
    expect(mainWindow.width / mainWindow.height).toBeLessThanOrEqual(1);
  });

  it("unblocks into the Paper v4 workspace with semantic Shell navigation", async () => {
    const wrapper = await mountApp();

    expect(wrapper.find(".paper-v4-workbench").exists()).toBe(true);
    expect(wrapper.text()).not.toContain("paper-v4/index-v4");
    expect(shellButtonByText(wrapper, "Paper").attributes("aria-current")).toBe("page");
    expect(shellButtonByText(wrapper, "Library").attributes("aria-current")).toBeUndefined();
    expect(shellButtonByText(wrapper, "Vault").exists()).toBe(true);
  });

  it("shows the host error and can restart into the same v2 runtime", async () => {
    getRuntimeStatus.mockResolvedValue({
      state: "blocked",
      error: {
        code: "protocol_mismatch",
        layer: "tauri_host",
        message: "Sidecar 协议不兼容。",
        recovery: "restart_sidecar",
      },
    });
    const wrapper = await mountApp();
    expect(wrapper.text()).toContain("protocol_mismatch");
    expect(wrapper.get("#runtime-blocked-title").text()).toBe(
      "本地 Core 协议无法安全核对",
    );
    expect(wrapper.text()).toContain("没有修改 Markdown 或 index.json");
    expect(wrapper.text()).toContain("不会自动重放任何持久操作");
    expect(wrapper.text()).toContain("退出并重新打开同一版本的 app");
    expect(wrapper.find(".app-shell").exists()).toBe(false);

    await buttonByText(wrapper, "重启本地 Core").trigger("click");
    await flushPromises();

    expect(restartSidecar).toHaveBeenCalledOnce();
    expect(wrapper.find(".paper-v4-workbench").exists()).toBe(true);
    expect(wrapper.find(".app-shell").exists()).toBe(true);
  });

  it("explains a stopped sidecar without offering an unsafe replay", async () => {
    getRuntimeStatus.mockRejectedValue(new Error("sidecar stopped"));
    const wrapper = await mountApp();

    expect(wrapper.get("#runtime-blocked-title").text()).toBe(
      "本地 Core 暂时不可用",
    );
    expect(wrapper.text()).toContain("Python Core 未启动、已退出");
    expect(wrapper.text()).toContain("没有修改 Markdown 或 index.json");
    expect(wrapper.text()).toContain("不会自动重放任何持久操作");
    expect(buttonByText(wrapper, "重启本地 Core").exists()).toBe(true);
  });

  it("keeps a dirty Paper and focus when Shell departure is canceled", async () => {
    const wrapper = await mountApp();
    await wrapper.get(".page-content-field textarea").setValue("Unsaved shell draft");
    const libraryButton = shellButtonByText(wrapper, "Library");
    libraryButton.element.focus();
    confirmDiscardChanges.mockResolvedValueOnce(false);

    await libraryButton.trigger("click");
    await flushPromises();

    expect(confirmDiscardChanges).toHaveBeenCalledOnce();
    expect(shellButtonByText(wrapper, "Paper").attributes("aria-current")).toBe("page");
    expect(wrapper.get(".page-content-field textarea").element.value).toBe(
      "Unsaved shell draft",
    );
    expect(wrapper.text()).not.toContain("草稿有未保存修改");
    expect(document.activeElement).toBe(libraryButton.element);
    expect(bridgeRequest.mock.calls.filter(([method]) => method === "library.query")).toHaveLength(0);

    confirmDiscardChanges.mockResolvedValueOnce(true);
    await libraryButton.trigger("click");
    await flushPromises();

    expect(shellButtonByText(wrapper, "Library").attributes("aria-current")).toBe("page");
    expect(bridgeRequest.mock.calls.filter(([method]) => method === "library.query")).toHaveLength(1);
    expect(document.activeElement).toBe(wrapper.get(".app-work-surface").element);
  });

  it("guards a dirty Paper before entering Vault", async () => {
    const wrapper = await mountApp();
    await wrapper.get(".page-content-field textarea").setValue("Keep before Vault");
    const vaultButton = shellButtonByText(wrapper, "Vault");
    vaultButton.element.focus();
    confirmDiscardChanges.mockResolvedValueOnce(false);

    await vaultButton.trigger("click");
    await flushPromises();
    expect(shellButtonByText(wrapper, "Paper").attributes("aria-current")).toBe("page");
    expect(wrapper.get(".page-content-field textarea").element.value).toBe("Keep before Vault");
    expect(document.activeElement).toBe(vaultButton.element);

    confirmDiscardChanges.mockResolvedValueOnce(true);
    await vaultButton.trigger("click");
    await flushPromises();
    expect(shellButtonByText(wrapper, "Vault").attributes("aria-current")).toBe("page");
    expect(confirmDiscardChanges).toHaveBeenCalledTimes(2);
  });

  it("creates one fresh Paper instance only after the shared guard confirms", async () => {
    const wrapper = await mountApp();
    await wrapper.get(".page-content-field textarea").setValue("Keep this draft");
    const newPaperButton = shellButtonByText(wrapper, "新 Paper");
    confirmDiscardChanges.mockResolvedValueOnce(false);

    await newPaperButton.trigger("click");
    await flushPromises();
    expect(bridgeRequest.mock.calls.filter(([method]) => method === "paper.create_draft")).toHaveLength(1);
    expect(wrapper.get(".page-content-field textarea").element.value).toBe("Keep this draft");

    confirmDiscardChanges.mockResolvedValueOnce(true);
    await Promise.all([
      newPaperButton.trigger("click"),
      newPaperButton.trigger("click"),
    ]);
    await flushPromises();

    expect(confirmDiscardChanges).toHaveBeenCalledTimes(2);
    expect(bridgeRequest.mock.calls.filter(([method]) => method === "paper.create_draft")).toHaveLength(2);
    expect(wrapper.get(".page-content-field textarea").element.value).toBe("Draft");
    expect(shellButtonByText(wrapper, "Paper").attributes("aria-current")).toBe("page");
  });

  it("keeps the saved Paper path across a Vault visit and cancel", async () => {
    const stored = {
      ...draft,
      path: draft.target_path,
      edit_token: "edit-saved",
      source_digest: "digest-saved",
      pages: [{ name: null, content: "Saved", type: null }],
    };
    bridgeRequest.mockImplementation((method, params) => {
      if (method === "paper.save") return { paper: stored, warnings: [] };
      if (method === "paper.open") return {
        state: "opened",
        paper: { ...stored, path: params.path },
      };
      return defaultBridge(method);
    });
    const wrapper = await mountApp();
    await wrapper.get(".page-content-field textarea").setValue("Saved");
    await buttonByText(wrapper, "保存").trigger("click");
    await flushPromises();

    await shellButtonByText(wrapper, "Vault").trigger("click");
    await flushPromises();
    expect(shellButtonByText(wrapper, "Vault").attributes("aria-current")).toBe("page");
    await buttonByText(wrapper, "取消并返回").trigger("click");
    await flushPromises();

    const openCalls = bridgeRequest.mock.calls.filter(([method]) => method === "paper.open");
    expect(openCalls).toHaveLength(1);
    expect(openCalls[0][1]).toEqual({ path: draft.target_path });
    expect(shellButtonByText(wrapper, "Paper").attributes("aria-current")).toBe("page");
  });

  it("keeps the active surface mounted until a durable intent is resolved", async () => {
    let rejectBranch;
    const pendingBranch = new Promise((resolve, reject) => {
      rejectBranch = reject;
    });
    bridgeRequest.mockImplementation((method) => {
      if (method === "library.query") return library({ entries: [libraryEntry] });
      if (method === "library.branch") return pendingBranch;
      return defaultBridge(method);
    });
    const wrapper = await mountApp();
    await shellButtonByText(wrapper, "Library").trigger("click");
    await flushPromises();

    await buttonByText(wrapper, "创建 Branch").trigger("click");
    await flushPromises();
    expect(wrapper.findAll(".app-shellbar button").every((button) => (
      button.attributes("disabled") !== undefined
    ))).toBe(true);

    await shellButtonByText(wrapper, "Paper").trigger("click");
    expect(shellButtonByText(wrapper, "Library").attributes("aria-current")).toBe("page");

    rejectBranch({
      code: "commit_unknown",
      layer: "tauri_host",
      message: "提交状态未知。",
      recovery: "restart_sidecar",
    });
    await flushPromises();

    expect(wrapper.find(".app-shell").exists()).toBe(false);
    expect(wrapper.text()).toContain("commit_unknown");
    expect(wrapper.get("#runtime-blocked-title").text()).toBe(
      "写入结果暂时无法确认",
    );
    expect(wrapper.text()).toContain("磁盘可能已提交，也可能未提交");
    expect(wrapper.text()).toContain("不会继续改写 Markdown 或 index.json");
    expect(wrapper.text()).toContain("不会自动重放这次持久操作");
    expect(wrapper.text()).toContain("从磁盘重新读取或核对结果");
    expect(wrapper.text()).not.toContain("Pending mutation");
  });

  it("keeps the Road v0.7 synthetic prototype isolated from runtime calls", async () => {
    const wrapper = mount(PrototypeView);
    mounted.push(wrapper);

    expect(wrapper.text()).toContain("合成样张");
    expect(wrapper.text()).toContain("不连接 Vault");
    expect(getRuntimeStatus).not.toHaveBeenCalled();
    expect(bridgeRequest).not.toHaveBeenCalled();
  });

  it("routes Library back to a whole Paper", async () => {
    bridgeRequest.mockImplementation((method, params) => {
      if (method === "paper.open") return {
        state: "opened",
        paper: { ...draft, path: params.path, source_digest: "digest" },
      };
      return defaultBridge(method);
    });
    const wrapper = await mountApp();

    await buttonByText(wrapper, "Library").trigger("click");
    await flushPromises();
    await buttonByText(wrapper, "新 Paper").trigger("click");
    await flushPromises();

    expect(wrapper.find(".paper-v4-workbench").exists()).toBe(true);
  });

  it("retains a Save intent across host failure and reconciles instead of replaying", async () => {
    bridgeRequest.mockImplementation(async (method) => {
      if (method === "paper.save") throw {
        code: "commit_unknown",
        layer: "tauri_host",
        message: "response lost",
        recovery: "restart_then_reload",
      };
      if (method === "paper.reconcile_save") return {
        state: "committed",
        paper: {
          ...draft,
          path: draft.target_path,
          edit_token: "edit-fresh",
          pages: [{ name: null, content: "Changed", type: null }],
          source_digest: "digest-new",
        },
        index_state: "current",
      };
      return defaultBridge(method);
    });
    const wrapper = await mountApp();
    await wrapper.get(".page-content-field textarea").setValue("Changed");
    await buttonByText(wrapper, "保存").trigger("click");
    await flushPromises();
    expect(wrapper.get("#runtime-blocked-title").text()).toBe(
      "写入结果暂时无法确认",
    );

    await buttonByText(wrapper, "重启本地 Core").trigger("click");
    await flushPromises();

    expect(bridgeRequest.mock.calls.filter(([method]) => method === "paper.save")).toHaveLength(1);
    expect(bridgeRequest.mock.calls.filter(([method]) => method === "paper.reconcile_save")).toHaveLength(1);
    expect(wrapper.text()).toContain("已确认上次保存落盘");
  });

  it("retains a Library intent across component unload and only refreshes after restart", async () => {
    const entry = {
      path: "cache/K-20260802-001.md",
      code: "K-20260802-001",
      display_name: "Library pending",
      folder: null,
      tags: [],
      preview: "Preview",
      page_count: 1,
      page_names: [],
      created: "2026-08-02T12:00:00",
      updated: "2026-08-02T12:00:00",
      trashed: false,
      repair_reason: null,
    };
    bridgeRequest.mockImplementation(async (method, params) => {
      if (method === "library.query") {
        return library({ entries: [entry], index_state: "current" });
      }
      if (method === "library.branch") throw {
        code: "commit_unknown",
        layer: "tauri_host",
        message: "response lost",
        recovery: "restart_then_reload",
      };
      return defaultBridge(method, params);
    });
    const wrapper = await mountApp();
    await buttonByText(wrapper, "Library").trigger("click");
    await flushPromises();
    await buttonByText(wrapper, "创建 Branch").trigger("click");
    await flushPromises();
    expect(wrapper.get("#runtime-blocked-title").text()).toBe(
      "写入结果暂时无法确认",
    );

    await buttonByText(wrapper, "重启本地 Core").trigger("click");
    await flushPromises();

    expect(bridgeRequest.mock.calls.filter(([method]) => method === "library.branch")).toHaveLength(1);
    expect(bridgeRequest.mock.calls.filter(([method]) => method === "startup.load")).toHaveLength(2);
    expect(bridgeRequest.mock.calls.some(([method, params]) =>
      method === "library.query" && params.verify_index === true
    )).toBe(true);
    expect(wrapper.text()).toContain("已在重启后重新读取 Vault");
  });

  it("keeps Library open paths inert while a durable mutation is pending", async () => {
    let resolveBranch;
    const branchPending = new Promise((resolve) => { resolveBranch = resolve; });
    bridgeRequest.mockImplementation((method, params) => {
      if (method === "library.query") {
        return library({ entries: [libraryEntry], index_state: "current" });
      }
      if (method === "library.branch") return branchPending;
      return defaultBridge(method, params);
    });
    const wrapper = await mountApp();
    await buttonByText(wrapper, "Library").trigger("click");
    await flushPromises();
    await buttonByText(wrapper, "创建 Branch").trigger("click");
    await flushPromises();

    expect(wrapper.get(".library-shell").attributes("inert")).toBeDefined();
    expect(shellButtonByText(wrapper, "Paper").attributes("disabled")).toBeDefined();
    await buttonByText(wrapper, "打开整份 Paper").trigger("click");
    await buttonByText(wrapper, "编辑整份 Paper").trigger("click");
    await flushPromises();

    expect(wrapper.get(".app-work-surface").attributes("aria-label")).toBe("Library 工作面");
    expect(bridgeRequest.mock.calls.some(([method]) => method === "paper.open")).toBe(false);

    resolveBranch({
      reports: [{ source: libraryEntry.path, destination: null, error: null }],
      warnings: [],
    });
    await flushPromises();
  });
});
