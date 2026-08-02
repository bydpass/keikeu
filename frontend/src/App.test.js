import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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

describe("Road v0.6 desktop shell", () => {
  it("unblocks into the Paper v4 workspace", async () => {
    const wrapper = await mountApp();

    expect(wrapper.text()).toContain("Paper 工作台");
    expect(wrapper.text()).toContain("paper-v4/index-v4");
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

    await buttonByText(wrapper, "重启本地 Core").trigger("click");
    await flushPromises();

    expect(restartSidecar).toHaveBeenCalledOnce();
    expect(wrapper.text()).toContain("Paper 工作台");
  });

  it("keeps the CP3 synthetic prototype isolated from runtime calls", async () => {
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

    expect(wrapper.text()).toContain("Paper 工作台");
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
    expect(wrapper.text()).toContain("无法安全连接 Python Core");

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
    expect(wrapper.text()).toContain("无法安全连接 Python Core");

    await buttonByText(wrapper, "重启本地 Core").trigger("click");
    await flushPromises();

    expect(bridgeRequest.mock.calls.filter(([method]) => method === "library.branch")).toHaveLength(1);
    expect(bridgeRequest.mock.calls.filter(([method]) => method === "startup.load")).toHaveLength(2);
    expect(bridgeRequest.mock.calls.some(([method, params]) =>
      method === "library.query" && params.verify_index === true
    )).toBe(true);
    expect(wrapper.text()).toContain("已在重启后重新读取 Vault");
  });
});
