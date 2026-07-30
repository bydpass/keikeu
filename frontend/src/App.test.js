import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App.vue";
import PrototypeView from "./PrototypeView.vue";
import {
  bridgeRequest,
  chooseVaultDirectory,
  confirmDiscardChanges,
  getRuntimeStatus,
  openSystemTarget,
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

const draftPaper = {
  path: null,
  edit_token: "edit-draft",
  code: "K-20260725-001",
  display_name: null,
  initial_summary: "",
  summary: "",
  highlights: [],
  tags: [],
  created: "2026-07-25T12:00:00",
  updated: "2026-07-25T12:00:00",
};

function buttonByText(wrapper, text) {
  const button = wrapper.findAll("button").find((item) => item.text() === text);
  if (!button) {
    throw new Error(`Button not found: ${text}`);
  }
  return button;
}

describe("desktop shell gates", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    confirmDiscardChanges.mockResolvedValue(true);
    registerWindowCloseGuard.mockResolvedValue(vi.fn());
    window.history.replaceState({}, "", "/");
    bridgeRequest.mockImplementation(async (method) => {
      if (method === "startup.load") {
        return { state: "ready", show_daily_card: false };
      }
      if (method === "library.query") {
        return {
          scope: "all",
          entries: [],
          folders: [],
          trash_folders: [],
          trash_count: 0,
          errors: [],
        };
      }
      if (method === "paper.create_draft") {
        return draftPaper;
      }
      throw new Error(`Unexpected method: ${method}`);
    });
  });

  it("unblocks only after the host is ready", async () => {
    getRuntimeStatus.mockResolvedValue({
      state: "ready",
      app_version: "0.1.0",
      core_version: "paper-v3/index-v3",
    });

    const wrapper = mount(App);
    await flushPromises();

    expect(wrapper.text()).toContain("Python Core 已连接");
    expect(wrapper.text()).toContain("Paper 工作台");
    expect(wrapper.text()).toContain("paper-v3/index-v3");
  });

  it("shows the host layer and can request a restart", async () => {
    getRuntimeStatus.mockResolvedValue({
      state: "blocked",
      error: {
        code: "protocol_mismatch",
        layer: "tauri_host",
        message: "Sidecar 协议不兼容。",
        recovery: "restart_sidecar",
      },
    });
    restartSidecar.mockResolvedValue({
      state: "ready",
      app_version: "0.1.0",
      core_version: "paper-v3/index-v3",
    });

    const wrapper = mount(App);
    await flushPromises();
    expect(wrapper.text()).toContain("protocol_mismatch");
    expect(wrapper.text()).toContain("tauri_host");

    await wrapper.get("button").trigger("click");
    await flushPromises();

    expect(restartSidecar).toHaveBeenCalledOnce();
    expect(wrapper.text()).toContain("Paper 工作台");
  });

  it("keeps the synthetic prototype isolated from the bridge", async () => {
    window.history.replaceState({}, "", "/?prototype=1");

    const wrapper = mount(App);
    await flushPromises();

    expect(wrapper.find(".runtime-gate").exists()).toBe(false);
    expect(getRuntimeStatus).not.toHaveBeenCalled();
    expect(bridgeRequest).not.toHaveBeenCalled();
  });

  it("renders the CP5 specimen with synthetic data only", () => {
    const wrapper = mount(PrototypeView);

    expect(wrapper.text()).toContain("合成样张");
    expect(wrapper.text()).toContain("不连接 Vault");
    expect(wrapper.text()).toContain("3 synthetic Papers");
  });

  it("routes between the saved Paper and its Summary-first Flashcard", async () => {
    const stored = {
      ...draftPaper,
      path: "cache/K-20260725-001.md",
      display_name: "Night Train",
      summary: "Saved Summary.",
      highlights: [
        { display_name: "Window", content: "Saved first anchor." },
        { display_name: "Platform", content: "Saved second anchor." },
      ],
    };
    bridgeRequest.mockImplementation(async (method, params) => {
      if (method === "startup.load") {
        return { state: "ready", show_daily_card: false };
      }
      if (method === "library.query") {
        return {
          scope: "all",
          entries: [],
          folders: [],
          trash_folders: [],
          trash_count: 0,
          errors: [],
        };
      }
      if (method === "paper.create_draft" || method === "paper.open") {
        return stored;
      }
      if (method === "flashcard.open") {
        return {
          path: stored.path,
          paper_label: `${stored.display_name} (${stored.code})`,
          cards: [
            { title: "Summary", content: stored.summary },
            ...stored.highlights.map((highlight) => ({
              title: highlight.display_name,
              content: highlight.content,
            })),
          ],
          options: [],
        };
      }
      throw new Error(`Unexpected method: ${method} ${JSON.stringify(params)}`);
    });
    getRuntimeStatus.mockResolvedValue({
      state: "ready",
      app_version: "0.1.0",
      core_version: "paper-v3/index-v3",
    });

    const wrapper = mount(App);
    await flushPromises();
    await wrapper.get('[name="summary"]').setValue("Unsaved form content.");
    await wrapper.get('button[aria-label="打开 Flashcard"]').trigger("click");
    await flushPromises();

    expect(confirmDiscardChanges).toHaveBeenCalledOnce();
    expect(wrapper.text()).toContain("Night Train");
    expect(wrapper.text()).toContain("Saved Summary.");
    expect(wrapper.text()).not.toContain("Unsaved form content.");
    expect(wrapper.text()).toContain("1 / 3");
    expect(bridgeRequest).toHaveBeenCalledWith("flashcard.open", {
      path: stored.path,
    });

    await wrapper.findAll(".flashcard-list button")[1].trigger("click");
    expect(wrapper.text()).toContain("Saved first anchor.");
    await wrapper.get('button[aria-label="返回 Paper"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("Paper 工作台");
    expect(bridgeRequest).toHaveBeenCalledWith("paper.open", {
      path: stored.path,
    });

    await wrapper.get('button[aria-label="打开 Flashcard"]').trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("Saved Summary.");
    expect(wrapper.text()).toContain("1 / 3");
    wrapper.unmount();
  });

  it("routes from Paper into the read-only Library", async () => {
    getRuntimeStatus.mockResolvedValue({
      state: "ready",
      app_version: "0.1.0",
      core_version: "paper-v3/index-v3",
    });
    openSystemTarget.mockResolvedValue(undefined);

    const wrapper = mount(App);
    await flushPromises();
    await wrapper.get('button[aria-label="打开 Library"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("Folder-aware retrieval");
    expect(bridgeRequest).toHaveBeenCalledWith("library.query", {
      scope: "all",
      search: "",
      sort: "updated_desc",
    });
    wrapper.unmount();
  });

  it("opens the Vault switcher from Library and can cancel without changing state", async () => {
    getRuntimeStatus.mockResolvedValue({
      state: "ready",
      app_version: "0.1.0",
      core_version: "paper-v3/index-v3",
    });
    openSystemTarget.mockResolvedValue(undefined);
    const wrapper = mount(App);
    await flushPromises();
    await wrapper.get('button[aria-label="打开 Library"]').trigger("click");
    await flushPromises();

    await buttonByText(wrapper, "切换 Vault").trigger("click");
    expect(wrapper.text()).toContain("打开或创建 Vault");
    await buttonByText(wrapper, "取消并返回").trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("Folder-aware retrieval");
    wrapper.unmount();
  });

  it("returns to the same saved Paper after canceling a Vault switch", async () => {
    const stored = {
      ...draftPaper,
      path: "cache/K-20260725-001.md",
      summary: "Saved Paper context",
    };
    bridgeRequest.mockImplementation(async (method, params) => {
      if (method === "startup.load") {
        return { state: "ready", show_daily_card: false };
      }
      if (method === "library.query") {
        return {
          scope: "all",
          entries: [],
          folders: [],
          trash_folders: [],
          trash_count: 0,
          errors: [],
        };
      }
      if (method === "paper.create_draft" || method === "paper.open") {
        return stored;
      }
      throw new Error(`Unexpected method: ${method} ${JSON.stringify(params)}`);
    });
    getRuntimeStatus.mockResolvedValue({
      state: "ready",
      app_version: "0.1.0",
      core_version: "paper-v3/index-v3",
    });

    const wrapper = mount(App);
    await flushPromises();
    await buttonByText(wrapper, "切换 Vault").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("打开或创建 Vault");

    await buttonByText(wrapper, "取消并返回").trigger("click");
    await flushPromises();

    expect(bridgeRequest).toHaveBeenCalledWith("paper.open", {
      path: stored.path,
    });
    expect(wrapper.get('[name="summary"]').element.value).toBe(
      "Saved Paper context",
    );
    wrapper.unmount();
  });

  it("routes a startup Vault gate into the CP9 picker", async () => {
    getRuntimeStatus.mockResolvedValue({
      state: "ready",
      app_version: "0.1.0",
      core_version: "paper-v3/index-v3",
    });
    bridgeRequest.mockImplementation(async (method) => {
      if (method === "startup.load") {
        return {
          state: "vault_picker",
          show_daily_card: false,
          message: "Vault selection required",
          configured_path: "",
          migration: null,
          preview: null,
        };
      }
      throw new Error(`Unexpected method: ${method}`);
    });

    const wrapper = mount(App);
    await flushPromises();

    expect(wrapper.text()).toContain("打开或创建 Vault");
    expect(wrapper.text()).toContain("Paper Markdown 保留在本地");
    expect(chooseVaultDirectory).not.toHaveBeenCalled();
    wrapper.unmount();
  });

  it("keeps specimen filtering, selection, and reordering in memory", async () => {
    const wrapper = mount(PrototypeView);

    await wrapper.get('input[type="search"]').setValue("角色");
    const matchingPapers = wrapper.findAll(".paper-list button");
    expect(matchingPapers).toHaveLength(1);
    await matchingPapers[0].trigger("click");
    expect(wrapper.get(".workspace-header h2").text()).toBe("角色动机");

    const menuButtons = wrapper.findAll(".row-actions > button");
    expect(menuButtons).toHaveLength(2);
    await menuButtons[1].trigger("click");
    const moveButtons = wrapper.findAll(".row-menu button");
    expect(moveButtons.map((button) => button.text())).toEqual(["上移", "下移"]);
    await moveButtons[0].trigger("click");

    expect(
      wrapper.findAll(".highlight-row strong").map((highlight) => highlight.text()),
    ).toEqual(["行动压力", "表层理由"]);
    expect(getRuntimeStatus).not.toHaveBeenCalled();
  });
});
