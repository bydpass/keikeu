import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import PaperView from "./PaperView.vue";
import {
  confirmDiscardChanges,
  openSystemTarget,
  registerWindowCloseGuard,
} from "./bridge.js";

vi.mock("./bridge.js", () => ({
  bridgeRequest: vi.fn(),
  confirmDiscardChanges: vi.fn(),
  openSystemTarget: vi.fn(),
  registerWindowCloseGuard: vi.fn(),
}));

const runtime = {
  state: "ready",
  app_version: "0.1.0",
  core_version: "paper-v4/index-v4",
};

function paper(overrides = {}) {
  return {
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
    ...overrides,
  };
}

function ready() {
  return {
    state: "ready",
    show_daily_card: false,
    vault_locator: "vault-v1:test",
    index_state: "current",
  };
}

function buttonByText(wrapper, text) {
  const button = wrapper.findAll("button").find((item) => item.text() === text);
  if (!button) throw new Error(`button not found: ${text}`);
  return button;
}

const mounted = [];
async function mountPaper(request, extra = {}) {
  const wrapper = mount(PaperView, {
    attachTo: document.body,
    props: { runtime, request, ...extra },
  });
  mounted.push(wrapper);
  await flushPromises();
  return wrapper;
}

beforeEach(() => {
  vi.resetAllMocks();
  confirmDiscardChanges.mockResolvedValue(true);
  openSystemTarget.mockResolvedValue(undefined);
  registerWindowCloseGuard.mockResolvedValue(vi.fn());
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText: vi.fn().mockResolvedValue(undefined) },
  });
});

afterEach(() => {
  while (mounted.length) mounted.pop().unmount();
});

describe("Road v0.6 Paper runtime", () => {
  it("opens a blank v4 Paper directly into the accepted card workbench", async () => {
    const request = vi.fn(async (method) => {
      if (method === "startup.load") return ready();
      if (method === "paper.create_draft") return paper();
      throw new Error(method);
    });

    const wrapper = await mountPaper(request);

    expect(wrapper.text()).toContain("Paper 工作台");
    expect(wrapper.text()).toContain("paper-v4/index-v4");
    expect(wrapper.findAll(".card-actions > button").map((item) => item.text())).toEqual([
      "保存",
      "删除本页",
      "加一页",
    ]);
    expect(wrapper.emitted("paper-path-change")[0]).toEqual([null]);
  });

  it("exposes the existing departure guard and reports an opened path", async () => {
    const opened = paper({ path: "cache/opened.md", source_digest: "digest" });
    const request = vi.fn(async (method) => {
      if (method === "startup.load") return ready();
      if (method === "paper.open") return { state: "opened", paper: opened };
      throw new Error(method);
    });
    const wrapper = await mountPaper(request, { initialPath: opened.path });
    expect(wrapper.emitted("paper-path-change").at(-1)).toEqual([opened.path]);

    await wrapper.get(".page-content-field textarea").setValue("Unsaved");
    confirmDiscardChanges.mockResolvedValueOnce(false).mockResolvedValueOnce(true);
    await expect(wrapper.vm.confirmDeparture()).resolves.toBe(false);
    await expect(wrapper.vm.confirmDeparture()).resolves.toBe(true);
    expect(confirmDiscardChanges).toHaveBeenCalledTimes(2);
  });

  it("sends one whole-page Save DTO plus the restart reconciliation intent", async () => {
    const draft = paper();
    const stored = paper({
      path: draft.target_path,
      source_digest: "digest-new",
      pages: [{ name: "First", content: "Changed", type: "summary" }],
    });
    const request = vi.fn(async (method) => {
      if (method === "startup.load") return ready();
      if (method === "paper.create_draft") return draft;
      if (method === "paper.save") return { paper: stored, warnings: [] };
      throw new Error(method);
    });
    const wrapper = await mountPaper(request);
    await wrapper.get(".page-title-field input").setValue("First");
    await wrapper.get(".page-content-field textarea").setValue("Changed");
    await buttonByText(wrapper, "进一步").trigger("click");
    await wrapper.get(".advanced-panel select").setValue("summary");

    await buttonByText(wrapper, "保存").trigger("click");
    await flushPromises();

    const saveCall = request.mock.calls.find(([method]) => method === "paper.save");
    expect(saveCall[1]).toEqual({
      edit_token: "edit-1",
      vault_locator: "vault-v1:test",
      display_name: null,
      tags: [],
      pages: [{ name: "First", content: "Changed", type: "summary" }],
    });
    expect(saveCall[2].family).toBe("paper_save");
    expect(saveCall[2].reconcile).toMatchObject({
      code: draft.code,
      source_digest: null,
      baseline: null,
      submitted: { pages: saveCall[1].pages },
    });
    expect(wrapper.text()).toContain("Paper 已保存为卡页 Markdown");
    expect(wrapper.emitted("paper-path-change").at(-1)).toEqual([stored.path]);
  });

  it("treats damaged open as tagged repair instead of a failed transport", async () => {
    let checks = 0;
    const request = vi.fn(async (method) => {
      if (method === "startup.load") return ready();
      if (method === "paper.open") {
        checks += 1;
        return checks === 1
          ? {
              state: "repair_required",
              paper: null,
              repair: {
                origin: "open",
                path: "cache/broken.md",
                reason: "page marker missing",
                page_number: 2,
              },
            }
          : { state: "opened", paper: paper({ path: "cache/broken.md" }), repair: null };
      }
      throw new Error(method);
    });

    const wrapper = await mountPaper(request, { initialPath: "cache/broken.md" });

    expect(wrapper.text()).toContain("这份 Paper 暂时不能安全打开");
    expect(wrapper.text()).toContain("cache/broken.md");
    expect(wrapper.text()).toContain("第 2 页");
    expect(wrapper.emitted("runtime-blocked")).toBeUndefined();

    await buttonByText(wrapper, "在 Finder 中显示").trigger("click");
    expect(openSystemTarget).toHaveBeenCalledWith("reveal", "cache/broken.md");
    await buttonByText(wrapper, "重新检查").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("Paper 结构已通过重新检查");
  });

  it("reconciles an unknown save without replay and keeps not-committed draft dirty", async () => {
    const submitted = { display_name: null, tags: [], pages: [{ name: null, content: "Submitted", type: null }] };
    const pending = {
      family: "paper_save",
      method: "paper.save",
      vault_locator: "vault-v1:test",
      save: { edit_token: "old", vault_locator: "vault-v1:test", ...submitted },
      reconcile: {
        vault_locator: "vault-v1:test",
        target_path: "cache/K-20260802-001.md",
        code: "K-20260802-001",
        created: "2026-08-02T12:00:00",
        source_digest: "old-digest",
        baseline: { display_name: null, tags: [], pages: [{ name: null, content: "Baseline", type: null }] },
        submitted,
      },
    };
    const request = vi.fn(async (method) => {
      if (method === "startup.load") return ready();
      if (method === "paper.reconcile_save") return {
        state: "not_committed",
        paper: paper({
          path: pending.reconcile.target_path,
          edit_token: "fresh",
          source_digest: "old-digest",
          pages: submitted.pages,
        }),
        index_state: "current",
      };
      throw new Error(method);
    });

    const wrapper = await mountPaper(request, { pendingIntent: pending });

    expect(request.mock.calls.filter(([method]) => method === "paper.save")).toHaveLength(0);
    expect(request.mock.calls.filter(([method]) => method === "paper.reconcile_save")).toHaveLength(1);
    expect(wrapper.text()).toContain("草稿仍在，请检查后重新保存");
    expect(wrapper.text()).toContain("草稿有未保存修改");
    expect(wrapper.emitted("intent-settled")).toHaveLength(1);
  });

  it("keeps an unknown-save repair in App ownership until a read-only recheck", async () => {
    const submitted = {
      display_name: "Retained",
      tags: ["private"],
      pages: [{ name: "Page", content: "Retained draft", type: "summary" }],
    };
    const pending = {
      family: "paper_save",
      method: "paper.save",
      save: { edit_token: "old", vault_locator: "vault-v1:test", ...submitted },
      reconcile: {
        vault_locator: "vault-v1:test",
        target_path: "cache/K-20260802-001.md",
        code: "K-20260802-001",
        created: "2026-08-02T12:00:00",
        source_digest: "old",
        baseline: { display_name: null, tags: [], pages: [{ name: null, content: "Old", type: null }] },
        submitted,
      },
    };
    let checks = 0;
    const request = vi.fn(async (method) => {
      if (method === "startup.load") return ready();
      if (method === "paper.reconcile_save") {
        checks += 1;
        return checks === 1
          ? {
              state: "repair_required",
              paper: null,
              stale_reason: null,
              repair: {
                origin: "unknown_save",
                path: pending.reconcile.target_path,
                reason: "Paper v4 page 1: invalid marker",
                page_number: 1,
              },
              index_state: "degraded",
            }
          : {
              state: "committed",
              paper: paper({
                path: pending.reconcile.target_path,
                edit_token: "fresh",
                source_digest: "new",
                ...submitted,
              }),
              stale_reason: null,
              repair: null,
              index_state: "current",
            };
      }
      throw new Error(method);
    });
    const wrapper = await mountPaper(request, { pendingIntent: pending });

    expect(wrapper.get(".page-content-field textarea").element.value).toBe(
      "Retained draft",
    );
    expect(wrapper.text()).toContain("复制保留草稿");
    expect(wrapper.emitted("intent-settled")).toBeUndefined();
    await buttonByText(wrapper, "复制保留草稿").trigger("click");
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      JSON.stringify(submitted, null, 2),
    );
    await buttonByText(wrapper, "重新检查").trigger("click");
    await flushPromises();

    expect(request.mock.calls.filter(([method]) => method === "paper.save")).toHaveLength(0);
    expect(request.mock.calls.filter(([method]) => method === "paper.reconcile_save")).toHaveLength(2);
    expect(wrapper.emitted("intent-settled")).toHaveLength(1);
    expect(wrapper.text()).toContain("已确认上次保存落盘");
  });

  it("keeps the window close guard active until an unknown intent is abandoned", async () => {
    const submitted = {
      display_name: null,
      tags: [],
      pages: [{ name: null, content: "Same projection", type: null }],
    };
    const pending = {
      family: "paper_save",
      method: "paper.save",
      save: { edit_token: "old", vault_locator: "vault-v1:test", ...submitted },
      reconcile: {
        vault_locator: "vault-v1:test",
        target_path: "cache/K-20260802-001.md",
        code: "K-20260802-001",
        created: "2026-08-02T12:00:00",
        source_digest: "old",
        baseline: submitted,
        submitted,
      },
    };
    let closeGuard;
    registerWindowCloseGuard.mockImplementation(async (guard) => {
      closeGuard = guard;
      return vi.fn();
    });
    const request = vi.fn(async (method) => {
      if (method === "startup.load") return ready();
      if (method === "paper.reconcile_save") return {
        state: "stale",
        paper: null,
        stale_reason: "third_content",
        repair: null,
        index_state: "current",
      };
      throw new Error(method);
    });
    const wrapper = await mountPaper(request, { pendingIntent: pending });

    confirmDiscardChanges.mockResolvedValueOnce(false).mockResolvedValueOnce(true);
    await expect(closeGuard()).resolves.toBe(false);
    expect(wrapper.emitted("intent-settled")).toBeUndefined();
    await expect(closeGuard()).resolves.toBe(true);
    expect(wrapper.emitted("intent-settled")).toHaveLength(1);
  });

  it("blocks after one unknown save and never retries it", async () => {
    const request = vi.fn(async (method) => {
      if (method === "startup.load") return ready();
      if (method === "paper.create_draft") return paper();
      if (method === "paper.save") throw {
        code: "commit_unknown",
        layer: "tauri_host",
        message: "response lost",
        recovery: "restart_then_reload",
      };
      throw new Error(method);
    });
    const wrapper = await mountPaper(request);
    await wrapper.get(".page-content-field textarea").setValue("Unknown result");

    await buttonByText(wrapper, "保存").trigger("click");
    await flushPromises();

    expect(request.mock.calls.filter(([method]) => method === "paper.save")).toHaveLength(1);
    expect(wrapper.emitted("runtime-blocked")).toHaveLength(1);
  });

  it("soft-deletes the whole Paper with locator after confirmation", async () => {
    const saved = paper({ path: "cache/K-20260802-001.md", source_digest: "digest" });
    const request = vi.fn(async (method) => {
      if (method === "startup.load") return ready();
      if (method === "paper.open") return { state: "opened", paper: saved, repair: null };
      if (method === "paper.soft_delete") return {
        report: { source: saved.path, destination: `.trash/${saved.path}`, error: null },
        warnings: [],
      };
      if (method === "paper.create_draft") return paper({ code: "K-20260802-002", edit_token: "edit-2" });
      throw new Error(method);
    });
    const wrapper = await mountPaper(request, { initialPath: saved.path });

    await buttonByText(wrapper, "整份移入废纸篓").trigger("click");
    await buttonByText(wrapper, "确认移入废纸篓").trigger("click");
    await flushPromises();

    expect(request).toHaveBeenCalledWith(
      "paper.soft_delete",
      { edit_token: "edit-1", vault_locator: "vault-v1:test" },
      expect.objectContaining({ family: "paper_delete" }),
    );
    expect(wrapper.text()).toContain("整份 Paper 已移入废纸篓");
  });

  it("re-reads Trash and settles an unknown whole-Paper delete after restart", async () => {
    const request = vi.fn(async (method, params) => {
      if (method === "startup.load") return ready();
      if (method === "library.query") {
        expect(params).toMatchObject({ scope: "trash", verify_index: true });
        return { entries: [] };
      }
      if (method === "paper.create_draft") return paper();
      throw new Error(method);
    });
    const wrapper = await mountPaper(request, {
      pendingIntent: { family: "paper_delete", method: "paper.soft_delete" },
    });

    expect(wrapper.text()).toContain("已在重启后重新读取废纸篓");
    expect(wrapper.emitted("intent-settled")).toHaveLength(1);
  });
});
