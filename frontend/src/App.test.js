import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App.vue";
import PrototypeView from "./PrototypeView.vue";
import {
  bridgeRequest,
  getRuntimeStatus,
  openSystemTarget,
  restartSidecar,
} from "./bridge.js";

vi.mock("./bridge.js", () => ({
  bridgeRequest: vi.fn(),
  getRuntimeStatus: vi.fn(),
  openSystemTarget: vi.fn(),
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

describe("desktop shell gates", () => {
  beforeEach(() => {
    vi.resetAllMocks();
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
      summary: "Saved Summary.",
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
          paper_label: stored.code,
          cards: [{ title: "Summary", content: stored.summary }],
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
    await wrapper.get('button[aria-label="打开 Flashcard"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("Saved Summary.");
    expect(bridgeRequest).toHaveBeenCalledWith("flashcard.open", {
      path: stored.path,
    });

    await wrapper.get('button[aria-label="返回 Paper"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("Paper 工作台");
    expect(bridgeRequest).toHaveBeenCalledWith("paper.open", {
      path: stored.path,
    });
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
