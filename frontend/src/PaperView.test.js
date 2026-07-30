import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import PaperView from "./PaperView.vue";
import {
  bridgeRequest,
  confirmDiscardChanges,
  registerWindowCloseGuard,
} from "./bridge.js";

vi.mock("./bridge.js", () => ({
  bridgeRequest: vi.fn(),
  confirmDiscardChanges: vi.fn(),
  registerWindowCloseGuard: vi.fn(),
}));

const runtime = {
  state: "ready",
  app_version: "0.1.0",
  core_version: "paper-v3/index-v3",
};

function paper(overrides = {}) {
  return {
    path: null,
    edit_token: "edit-1",
    code: "K-20260725-001",
    display_name: null,
    initial_summary: "",
    summary: "",
    highlights: [],
    tags: [],
    created: "2026-07-25T12:00:00",
    updated: "2026-07-25T12:00:00",
    ...overrides,
  };
}

function installBridge({
  startup = { state: "ready", show_daily_card: false },
  entries = [],
  draft = paper(),
  opened = paper(),
  saved = paper(),
  saveError = null,
  deleteResult = { source: "cache/K.md", destination: "Trash/cache/K.md", error: null },
} = {}) {
  bridgeRequest.mockImplementation(async (method) => {
    if (method === "startup.load") return startup;
    if (method === "library.query") return { entries, errors: [] };
    if (method === "paper.create_draft") return draft;
    if (method === "paper.open") return opened;
    if (method === "paper.save") {
      if (saveError) throw saveError;
      return saved;
    }
    if (method === "paper.soft_delete") return deleteResult;
    throw new Error(`Unexpected method: ${method}`);
  });
}

describe("Road v0.5 Paper Desk", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    confirmDiscardChanges.mockResolvedValue(true);
    registerWindowCloseGuard.mockResolvedValue(vi.fn());
  });

  it("shows the claimed daily card before creating a blank Paper", async () => {
    installBridge({
      startup: { state: "ready", show_daily_card: true },
    });
    const wrapper = mount(PaperView, { props: { runtime } });
    await flushPromises();

    expect(wrapper.text()).toContain("每日一张");
    expect(bridgeRequest).not.toHaveBeenCalledWith("paper.create_draft", {});

    await wrapper.get(".daily-gate button").trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("Paper 工作台");
    expect(bridgeRequest).toHaveBeenCalledWith("paper.create_draft", {});
    wrapper.unmount();
  });

  it("does not bypass a Vault or migration startup gate", async () => {
    installBridge({
      startup: {
        state: "vault_picker",
        show_daily_card: false,
        message: "Vault selection required",
      },
    });
    const wrapper = mount(PaperView, { props: { runtime } });
    await flushPromises();

    expect(wrapper.text()).toContain("当前还不能进入 Paper");
    expect(wrapper.text()).toContain("Vault selection required");
    expect(bridgeRequest).not.toHaveBeenCalledWith("paper.create_draft", {});
    expect(wrapper.emitted("open-vault")[0][0]).toMatchObject({
      state: "vault_picker",
      message: "Vault selection required",
    });
    wrapper.unmount();
  });

  it("consumes a confirmed startup DTO without claiming startup twice", async () => {
    installBridge();
    const confirmed = { state: "ready", show_daily_card: false };
    const wrapper = mount(PaperView, {
      props: { runtime, initialStartup: confirmed },
    });
    await flushPromises();

    expect(wrapper.emitted("startup-consumed")).toHaveLength(1);
    expect(bridgeRequest).not.toHaveBeenCalledWith("startup.load", {});
    expect(wrapper.text()).toContain("Paper 工作台");
    wrapper.unmount();
  });

  it("saves the controlled form through Cmd+S with ordered DTO fields", async () => {
    const stored = paper({
      path: "cache/K-20260725-001.md",
      initial_summary: "First summary",
      summary: "First summary",
      display_name: "Night Bus",
      highlights: [{ display_name: "Breath", content: "A held breath." }],
      tags: ["rain", "station"],
    });
    installBridge({ saved: stored });
    const wrapper = mount(PaperView, { props: { runtime } });
    await flushPromises();

    await wrapper.get('[name="display_name"]').setValue("Night Bus");
    await wrapper.get('[name="summary"]').setValue("First summary");
    await wrapper.get('[name="tags"]').setValue("rain, station");
    await wrapper.get(".paper-highlights > button").trigger("click");
    await wrapper.get(".highlight-fields input").setValue("Breath");
    await wrapper.get(".highlight-fields textarea").setValue("A held breath.");

    const shortcut = new KeyboardEvent("keydown", {
      key: "s",
      metaKey: true,
      cancelable: true,
    });
    window.dispatchEvent(shortcut);
    await flushPromises();

    expect(shortcut.defaultPrevented).toBe(true);
    expect(bridgeRequest).toHaveBeenCalledWith("paper.save", {
      edit_token: "edit-1",
      summary: "First summary",
      display_name: "Night Bus",
      highlights: [{ display_name: "Breath", content: "A held breath." }],
      tags: ["rain", " station"],
    });
    expect(wrapper.text()).toContain("已保存至 Markdown");
    expect(wrapper.text()).toContain("First summary");
    wrapper.unmount();
  });

  it("makes the four editable regions obvious and keeps the original draft locked", async () => {
    installBridge({
      draft: paper({
        path: "cache/K-20260725-001.md",
        display_name: "Night Bus",
        initial_summary: "Frozen first draft",
        summary: "Saved summary",
        tags: ["rain"],
      }),
    });
    const wrapper = mount(PaperView, { props: { runtime } });
    await flushPromises();

    expect(wrapper.find('[name="code"]').exists()).toBe(false);
    expect(wrapper.get('[name="display_name"]').element.readOnly).toBe(false);
    expect(wrapper.get('[name="summary"]').element.readOnly).toBe(false);
    expect(wrapper.get('[name="tags"]').element.readOnly).toBe(false);
    expect(wrapper.text()).toContain("Highlights");
    expect(wrapper.get("details.initial-copy").attributes("open")).toBeUndefined();
    expect(wrapper.get("details.initial-copy summary").text()).toContain("归档只读");
    expect(wrapper.text()).toContain("已保存至 Markdown");

    await wrapper.get('[name="summary"]').setValue("Unsaved summary");
    expect(wrapper.get(".paper-save-state").text()).toBe("未保存");
    wrapper.unmount();
  });

  it("opens an existing Paper, preserves its initial copy, and saves reordered Highlights", async () => {
    const entry = {
      path: "cache/K-20260725-002.md",
      code: "K-20260725-002",
      display_name: "Scene",
    };
    const opened = paper({
      path: entry.path,
      edit_token: "edit-existing",
      code: entry.code,
      display_name: entry.display_name,
      initial_summary: "Frozen first draft",
      summary: "Current summary",
      highlights: [
        { display_name: "First", content: "One" },
        { display_name: "Second", content: "Two" },
      ],
    });
    installBridge({ entries: [entry], opened, saved: opened });
    const wrapper = mount(PaperView, { props: { runtime } });
    await flushPromises();

    await wrapper.get(".paper-picker button").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("Frozen first draft");

    const firstRowButtons = wrapper.findAll(".highlight-actions")[0].findAll("button");
    await firstRowButtons[1].trigger("click");
    await wrapper.get(".paper-editor").trigger("submit");
    await flushPromises();

    const saveCall = bridgeRequest.mock.calls.find(([method]) => method === "paper.save");
    expect(saveCall[1].highlights).toEqual([
      { display_name: "Second", content: "Two" },
      { display_name: "First", content: "One" },
    ]);
    wrapper.unmount();
  });

  it("reorders Highlights with the native drag handle", async () => {
    const stored = paper({
      path: "cache/K-20260725-003.md",
      summary: "Saved summary",
      highlights: [
        { display_name: "First", content: "One" },
        { display_name: "Second", content: "Two" },
      ],
    });
    installBridge({ draft: stored, saved: stored });
    const wrapper = mount(PaperView, { props: { runtime } });
    await flushPromises();

    const dataTransfer = {
      effectAllowed: "",
      setData: vi.fn(),
    };
    await wrapper.findAll(".highlight-grip")[0].trigger("dragstart", { dataTransfer });
    await wrapper.findAll(".paper-highlights li")[1].trigger("drop");
    await wrapper.get(".paper-editor").trigger("submit");
    await flushPromises();

    expect(dataTransfer.setData).toHaveBeenCalledWith("text/plain", expect.any(String));
    const saveCall = bridgeRequest.mock.calls.find(([method]) => method === "paper.save");
    expect(saveCall[1].highlights).toEqual([
      { display_name: "Second", content: "Two" },
      { display_name: "First", content: "One" },
    ]);
    wrapper.unmount();
  });

  it.each([
    [
      "stale_snapshot",
      "Paper 已在外部修改；未覆盖。请重新打开后决定如何处理。",
    ],
    [
      "not_found",
      "Paper 已在外部删除或移动；未保存。请刷新 Paper 列表。",
    ],
  ])("does not retry a save rejected as %s", async (code, message) => {
    installBridge({
      draft: paper({
        path: "cache/K-20260725-001.md",
        summary: "Disk summary",
      }),
      saveError: {
        code,
        layer: "application_service",
        message: "de-identified service failure",
        recovery: "refresh",
      },
    });
    const wrapper = mount(PaperView, { props: { runtime } });
    await flushPromises();

    await wrapper.get('[name="summary"]').setValue("Unsaved local edit");
    await wrapper.get(".paper-editor").trigger("submit");
    await flushPromises();

    expect(wrapper.text()).toContain(message);
    expect(
      bridgeRequest.mock.calls.filter(([method]) => method === "paper.save"),
    ).toHaveLength(1);
    expect(wrapper.get('[name="summary"]').element.value).toBe("Unsaved local edit");
    expect(wrapper.get(".paper-save-state").text()).toBe("未保存");
    wrapper.unmount();
  });

  it("requires confirmation before soft delete and opens a fresh draft afterward", async () => {
    const stored = paper({
      path: "cache/K-20260725-001.md",
      summary: "Saved",
    });
    let draftCount = 0;
    installBridge({ draft: stored });
    const baseImplementation = bridgeRequest.getMockImplementation();
    bridgeRequest.mockImplementation(async (method, params) => {
      if (method === "paper.create_draft") {
        draftCount += 1;
        return draftCount === 1 ? stored : paper({ edit_token: "edit-2" });
      }
      return baseImplementation(method, params);
    });
    const wrapper = mount(PaperView, { props: { runtime } });
    await flushPromises();

    await wrapper.findAll(".paper-actions button")[1].trigger("click");
    expect(wrapper.text()).toContain("确认软删除这个 Paper");
    await wrapper.get(".danger-action").trigger("click");
    await flushPromises();

    expect(bridgeRequest).toHaveBeenCalledWith("paper.soft_delete", {
      edit_token: "edit-1",
    });
    expect(wrapper.text()).toContain("Paper 已移入回收站");
    expect(
      bridgeRequest.mock.calls.filter(([method]) => method === "paper.create_draft"),
    ).toHaveLength(2);
    expect(wrapper.findAll(".paper-actions button")[1].attributes("disabled")).toBeDefined();
    wrapper.unmount();
  });

  it("blocks the UI when a mutation result becomes unknown", async () => {
    installBridge({
      draft: paper({ summary: "Saved text" }),
      saveError: {
        code: "commit_unknown",
        layer: "tauri_host",
        message: "response lost",
        recovery: "restart_sidecar",
      },
    });
    const wrapper = mount(PaperView, { props: { runtime } });
    await flushPromises();

    await wrapper.get('[name="summary"]').setValue("Changed text");
    await wrapper.get(".paper-editor").trigger("submit");
    await flushPromises();

    expect(wrapper.emitted("runtime-blocked")[0][0]).toMatchObject({
      code: "commit_unknown",
      layer: "tauri_host",
    });
    expect(
      bridgeRequest.mock.calls.filter(([method]) => method === "paper.save"),
    ).toHaveLength(1);
    wrapper.unmount();
  });

  it("keeps the page and content when the user continues editing", async () => {
    const stored = paper({
      path: "cache/K-20260725-001.md",
      summary: "Saved text",
    });
    installBridge({ draft: stored });
    confirmDiscardChanges.mockResolvedValue(false);
    const wrapper = mount(PaperView, { props: { runtime } });
    await flushPromises();

    await wrapper.get('[name="summary"]').setValue("Unsaved local edit");
    await wrapper.get('button[aria-label="打开 Flashcard"]').trigger("click");
    await flushPromises();

    expect(confirmDiscardChanges).toHaveBeenCalledOnce();
    expect(wrapper.emitted("open-flashcard")).toBeUndefined();
    expect(wrapper.get('[name="summary"]').element.value).toBe("Unsaved local edit");
    expect(wrapper.get(".paper-save-state").text()).toBe("未保存");
    wrapper.unmount();
  });

  it("discards only to the latest successful save before leaving", async () => {
    const initial = paper({
      path: "cache/K-20260725-001.md",
      edit_token: "edit-1",
      summary: "First baseline",
    });
    const saved = paper({
      path: initial.path,
      edit_token: "edit-2",
      summary: "Latest baseline",
    });
    installBridge({ draft: initial, saved });
    const wrapper = mount(PaperView, { props: { runtime } });
    await flushPromises();

    await wrapper.get('[name="summary"]').setValue("Latest baseline");
    await wrapper.get(".paper-editor").trigger("submit");
    await flushPromises();
    await wrapper.get('[name="summary"]').setValue("Throw this away");
    await wrapper.get('button[aria-label="打开 Library"]').trigger("click");
    await flushPromises();

    expect(wrapper.emitted("open-library")).toHaveLength(1);
    expect(wrapper.get('[name="summary"]').element.value).toBe("Latest baseline");
    expect(wrapper.get(".paper-save-state").text()).toBe("已保存至 Markdown");
    wrapper.unmount();
  });

  it("uses the same guard for new Paper, Paper switch, and Vault switch", async () => {
    const entry = {
      path: "cache/K-20260725-002.md",
      code: "K-20260725-002",
      display_name: "Other Paper",
    };
    installBridge({
      draft: paper({
        path: "cache/K-20260725-001.md",
        summary: "Saved text",
      }),
      entries: [entry],
    });
    confirmDiscardChanges.mockResolvedValue(false);
    const wrapper = mount(PaperView, { props: { runtime } });
    await flushPromises();

    await wrapper.get('[name="summary"]').setValue("Unsaved local edit");
    await wrapper.get(".new-paper").trigger("click");
    await wrapper.get(".paper-picker button").trigger("click");
    await wrapper.get(".vault-switch").trigger("click");
    await flushPromises();

    expect(confirmDiscardChanges).toHaveBeenCalledTimes(3);
    expect(
      bridgeRequest.mock.calls.filter(([method]) => method === "paper.create_draft"),
    ).toHaveLength(1);
    expect(bridgeRequest).not.toHaveBeenCalledWith("paper.open", {
      path: entry.path,
    });
    expect(wrapper.emitted("open-vault")).toBeUndefined();
    expect(wrapper.get('[name="summary"]').element.value).toBe("Unsaved local edit");
    wrapper.unmount();
  });

  it("runs window close through the same latest-baseline guard", async () => {
    installBridge({ draft: paper({ summary: "Saved text" }) });
    confirmDiscardChanges.mockResolvedValue(false);
    const wrapper = mount(PaperView, { props: { runtime } });
    await flushPromises();
    const closeGuard = registerWindowCloseGuard.mock.calls[0][0];

    await wrapper.get('[name="summary"]').setValue("Unsaved local edit");
    await expect(closeGuard()).resolves.toBe(false);
    expect(wrapper.get('[name="summary"]').element.value).toBe("Unsaved local edit");

    confirmDiscardChanges.mockResolvedValue(true);
    await expect(closeGuard()).resolves.toBe(true);
    expect(wrapper.get('[name="summary"]').element.value).toBe("Saved text");
    wrapper.unmount();
  });

  it("stays dirty when the native discard dialog fails", async () => {
    installBridge({ draft: paper({ summary: "Saved text" }) });
    confirmDiscardChanges.mockRejectedValue(new Error("dialog unavailable"));
    const wrapper = mount(PaperView, { props: { runtime } });
    await flushPromises();

    await wrapper.get('[name="summary"]').setValue("Unsaved local edit");
    await wrapper.get('button[aria-label="打开 Library"]').trigger("click");
    await flushPromises();

    expect(wrapper.emitted("open-library")).toBeUndefined();
    expect(wrapper.get('[name="summary"]').element.value).toBe("Unsaved local edit");
    expect(wrapper.get(".paper-save-state").text()).toBe("未保存");
    expect(wrapper.text()).toContain("无法确认是否放弃更改");
    wrapper.unmount();
  });
});
