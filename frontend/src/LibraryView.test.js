import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LibraryView from "./LibraryView.vue";
import { bridgeRequest, openSystemTarget } from "./bridge.js";

vi.mock("./bridge.js", () => ({
  bridgeRequest: vi.fn(),
  openSystemTarget: vi.fn(),
}));

const runtime = {
  state: "ready",
  app_version: "0.1.0",
  core_version: "paper-v3/index-v3",
};

const rootEntry = {
  path: "cache/K-20260725-001.md",
  code: "K-20260725-001",
  display_name: "Night Train",
  folder: null,
  summary: "A train waits outside the city.",
  tags: ["night", "rain"],
  highlight_names: ["Window"],
  created: "2026-07-25T12:00:00",
  updated: "2026-07-25T13:00:00",
  trashed: false,
};

const folderEntry = {
  path: "cache/Ideas/K-20260725-002.md",
  code: "K-20260725-002",
  display_name: "Blue Hour",
  folder: "Ideas",
  summary: "Blue hour settles over the harbour.",
  tags: ["harbour"],
  highlight_names: ["Signal"],
  created: "2026-07-25T14:00:00",
  updated: "2026-07-25T15:00:00",
  trashed: false,
};

function libraryView(overrides = {}) {
  return {
    scope: "all",
    entries: [rootEntry, folderEntry],
    folders: ["Ideas"],
    trash_folders: [],
    trash_count: 1,
    errors: [
      {
        path: "cache/K-20260725-999.md",
        reason: "missing required frontmatter",
      },
    ],
    ...overrides,
  };
}

function buttonByText(wrapper, text) {
  const button = wrapper.findAll("button").find((item) => item.text() === text);
  if (!button) {
    throw new Error(`Button not found: ${text}`);
  }
  return button;
}

describe("CP8/CP9 Library slice", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    bridgeRequest.mockResolvedValue(libraryView());
    openSystemTarget.mockResolvedValue(undefined);
  });

  it("renders Python-sorted entries, folders, detail context, and damaged items", async () => {
    const wrapper = mount(LibraryView, { props: { runtime } });
    await flushPromises();

    expect(bridgeRequest).toHaveBeenCalledWith("library.query", {
      scope: "all",
      search: "",
      sort: "updated_desc",
    });
    expect(wrapper.text()).toContain("Night Train");
    expect(wrapper.text()).toContain("Blue Hour");
    expect(wrapper.text()).toContain("Ideas");
    expect(wrapper.text()).toContain("损坏 Paper：cache/K-20260725-999.md");
    expect(wrapper.text()).toContain("A train waits outside the city.");
    expect(wrapper.text()).toContain("2026-07-25 12:00");
    expect(wrapper.text()).not.toContain("2026-07-25T12:00:00");
    const context = wrapper.get(".library-context");
    expect(context.classes()).toContain("fixed-context-rail");
    wrapper.unmount();
  });

  it("blocks an incomplete Library DTO at the Vue trust boundary", async () => {
    bridgeRequest.mockResolvedValue(
      libraryView({ entries: [{ ...rootEntry, tags: [42] }] }),
    );
    const wrapper = mount(LibraryView, { props: { runtime } });
    await flushPromises();

    expect(wrapper.text()).toContain(
      "无法读取 Library：Library 数据不完整。",
    );
    wrapper.unmount();
  });

  it("clears selection when scope, search, or sort changes", async () => {
    bridgeRequest.mockImplementation(async (_method, params) => {
      if (params.scope === "folder:Ideas") {
        return libraryView({ scope: "folder:Ideas", entries: [folderEntry] });
      }
      return libraryView();
    });
    const wrapper = mount(LibraryView, { props: { runtime } });
    await flushPromises();

    await wrapper.get(`input[aria-label="选择 ${rootEntry.display_name}"]`).setValue(true);
    expect(wrapper.text()).toContain("已选择 1");

    await wrapper.get(".library-scopes button:nth-of-type(3)").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("已选择 0");
    expect(bridgeRequest).toHaveBeenLastCalledWith("library.query", {
      scope: "folder:Ideas",
      search: "",
      sort: "updated_desc",
    });

    await wrapper.get('input[type="search"]').setValue("harbour");
    await flushPromises();
    expect(bridgeRequest).toHaveBeenLastCalledWith("library.query", {
      scope: "folder:Ideas",
      search: "harbour",
      sort: "updated_desc",
    });

    await wrapper.get(".library-toolbar select").setValue("name");
    await flushPromises();
    expect(bridgeRequest).toHaveBeenLastCalledWith("library.query", {
      scope: "folder:Ideas",
      search: "harbour",
      sort: "name",
    });
    wrapper.unmount();
  });

  it("keeps only the newest asynchronous query result", async () => {
    let resolveSlow;
    let resolveFast;
    bridgeRequest
      .mockResolvedValueOnce(libraryView())
      .mockImplementationOnce(
        () => new Promise((resolve) => {
          resolveSlow = resolve;
        }),
      )
      .mockImplementationOnce(
        () => new Promise((resolve) => {
          resolveFast = resolve;
        }),
      );
    const wrapper = mount(LibraryView, { props: { runtime } });
    await flushPromises();

    await wrapper.get('input[type="search"]').setValue("slow");
    await wrapper.get('input[type="search"]').setValue("fast");
    resolveFast(libraryView({ entries: [folderEntry] }));
    await flushPromises();
    resolveSlow(libraryView({ entries: [rootEntry] }));
    await flushPromises();

    expect(wrapper.text()).toContain("Blue Hour");
    expect(wrapper.text()).not.toContain("Night Train");
    wrapper.unmount();
  });

  it("routes selected Papers and delegates only relative system targets", async () => {
    const wrapper = mount(LibraryView, { props: { runtime } });
    await flushPromises();

    await wrapper.get(".detail-actions button").trigger("click");
    expect(wrapper.emitted("open-paper")[0]).toEqual([rootEntry.path]);

    const actions = wrapper.findAll(".detail-actions button");
    await actions[1].trigger("click");
    await actions[2].trigger("click");
    await actions[3].trigger("click");
    await wrapper.get(".reveal-vault").trigger("click");
    await flushPromises();

    expect(wrapper.emitted("open-flashcard")[0]).toEqual([rootEntry.path]);
    expect(openSystemTarget.mock.calls).toEqual([
      ["open", rootEntry.path],
      ["reveal", rootEntry.path],
      ["reveal", "."],
    ]);
    wrapper.unmount();
  });

  it("does not route a trashed path into Paper or Flashcard", async () => {
    bridgeRequest.mockResolvedValue(
      libraryView({
        scope: "trash",
        entries: [
          {
            ...rootEntry,
            path: ".trash/cache/K-20260725-001.md",
            trashed: true,
          },
        ],
      }),
    );
    const wrapper = mount(LibraryView, { props: { runtime } });
    await flushPromises();

    await wrapper.get('button[aria-label="打开 Paper"]').trigger("click");
    await wrapper.get('button[aria-label="打开 Flashcard"]').trigger("click");

    expect(wrapper.emitted("open-paper")[0]).toEqual([null]);
    expect(wrapper.emitted("open-flashcard")[0]).toEqual([null]);
    wrapper.unmount();
  });

  it("focuses search with Cmd+F and blocks only fatal host failures", async () => {
    const wrapper = mount(LibraryView, {
      props: { runtime },
      attachTo: document.body,
    });
    await flushPromises();

    const shortcut = new KeyboardEvent("keydown", {
      key: "f",
      metaKey: true,
      cancelable: true,
    });
    window.dispatchEvent(shortcut);
    expect(shortcut.defaultPrevented).toBe(true);
    expect(document.activeElement).toBe(wrapper.get('input[type="search"]').element);
    wrapper.unmount();

    bridgeRequest.mockRejectedValue({
      code: "sidecar_unavailable",
      layer: "tauri_host",
      message: "Sidecar stopped",
      recovery: "restart_sidecar",
    });
    const blocked = mount(LibraryView, { props: { runtime } });
    await flushPromises();
    expect(blocked.emitted("runtime-blocked")[0][0]).toMatchObject({
      code: "sidecar_unavailable",
      layer: "tauri_host",
    });
    blocked.unmount();
  });

  it("moves selected Papers once and preserves partial-result failures", async () => {
    bridgeRequest.mockImplementation(async (method) => {
      if (method === "library.query") return libraryView();
      if (method === "library.move") {
        return [
          {
            source: rootEntry.path,
            destination: "cache/Ideas/K-20260725-001.md",
            error: null,
          },
          {
            source: folderEntry.path,
            destination: null,
            error: "injected provider failure",
          },
        ];
      }
      throw new Error(`Unexpected method: ${method}`);
    });
    const wrapper = mount(LibraryView, { props: { runtime } });
    await flushPromises();
    for (const checkbox of wrapper.findAll(".library-list input[type='checkbox']")) {
      await checkbox.setValue(true);
    }

    await buttonByText(wrapper, "移动所选").trigger("click");
    await flushPromises();
    await wrapper.get(".operation-dialog select").setValue("Ideas");
    await buttonByText(wrapper, "确认执行").trigger("click");
    await flushPromises();

    expect(bridgeRequest).toHaveBeenCalledWith("library.move", {
      paths: [rootEntry.path, folderEntry.path],
      destination_folder: "Ideas",
    });
    expect(wrapper.text()).toContain("移动：1 项成功，1 项失败");
    expect(wrapper.text()).toContain("injected provider failure");
    expect(wrapper.text()).toContain("已选择 1");
    wrapper.unmount();
  });

  it("uses the same move method for drag and the keyboard-reachable action", async () => {
    bridgeRequest.mockImplementation(async (method, params) => {
      if (method === "library.query") return libraryView();
      if (method === "library.move") {
        return [{
          source: params.paths[0],
          destination: `cache/Ideas/${params.paths[0].split("/").at(-1)}`,
          error: null,
        }];
      }
      throw new Error(`Unexpected method: ${method}`);
    });
    const wrapper = mount(LibraryView, { props: { runtime } });
    await flushPromises();
    const transfer = {
      setData: vi.fn(),
      getData: vi.fn(() => rootEntry.path),
    };

    await wrapper.get(".library-list li").trigger("dragstart", {
      dataTransfer: transfer,
    });
    const ideas = wrapper
      .findAll(".library-scopes button")
      .find((button) => button.text() === "Ideas");
    await ideas.trigger("drop", { dataTransfer: transfer });
    await flushPromises();

    expect(bridgeRequest).toHaveBeenCalledWith("library.move", {
      paths: [rootEntry.path],
      destination_folder: "Ideas",
    });
    wrapper.unmount();
  });

  it("soft-deletes an explicit active path and rebuilds only on explicit request", async () => {
    bridgeRequest.mockImplementation(async (method, params) => {
      if (method === "library.query") return libraryView();
      if (method === "library.soft_delete") {
        return [{
          source: params.paths[0],
          destination: `.trash/${params.paths[0]}`,
          error: null,
        }];
      }
      if (method === "library.rebuild") return libraryView();
      throw new Error(`Unexpected method: ${method}`);
    });
    const wrapper = mount(LibraryView, { props: { runtime } });
    await flushPromises();

    await wrapper.findAll(".detail-actions button").at(-1).trigger("click");
    await flushPromises();
    await buttonByText(wrapper, "确认执行").trigger("click");
    await flushPromises();
    expect(bridgeRequest).toHaveBeenCalledWith("library.soft_delete", {
      paths: [rootEntry.path],
    });

    await buttonByText(wrapper, "重建索引").trigger("click");
    await flushPromises();
    expect(bridgeRequest).toHaveBeenCalledWith("library.rebuild", {
      scope: "all",
      search: "",
      sort: "updated_desc",
    });
    wrapper.unmount();
  });

  it("never retries a branch mutation with an unknown commit result", async () => {
    bridgeRequest.mockImplementation(async (method) => {
      if (method === "library.query") return libraryView();
      if (method === "library.branch") {
        throw {
          code: "commit_unknown",
          layer: "tauri_host",
          message: "response lost",
          recovery: "restart_then_reload",
        };
      }
      throw new Error(`Unexpected method: ${method}`);
    });
    const wrapper = mount(LibraryView, { props: { runtime } });
    await flushPromises();

    await buttonByText(wrapper, "复制分支").trigger("click");
    await flushPromises();

    expect(
      bridgeRequest.mock.calls.filter(([method]) => method === "library.branch"),
    ).toHaveLength(1);
    expect(wrapper.emitted("runtime-blocked")[0][0]).toMatchObject({
      code: "commit_unknown",
      layer: "tauri_host",
    });
    wrapper.unmount();
  });

  it("requires exact execute before permanently deleting four Papers", async () => {
    const trashed = Array.from({ length: 4 }, (_item, index) => ({
      ...rootEntry,
      path: `.trash/cache/K-20260725-00${index + 1}.md`,
      code: `K-20260725-00${index + 1}`,
      trashed: true,
    }));
    const trashView = libraryView({
      scope: "trash",
      entries: trashed,
      folders: [],
      trash_count: 4,
      errors: [],
    });
    bridgeRequest.mockImplementation(async (method, params) => {
      if (method === "library.query") return trashView;
      if (method === "library.permanently_delete") {
        return params.paths.map((path) => ({
          source: path,
          destination: null,
          error: null,
        }));
      }
      throw new Error(`Unexpected method: ${method}`);
    });
    const wrapper = mount(LibraryView, { props: { runtime } });
    await flushPromises();

    await buttonByText(wrapper, "清空 Trash").trigger("click");
    await flushPromises();
    await buttonByText(wrapper, "确认执行").trigger("click");
    expect(wrapper.text()).toContain("请输入完全一致的小写 execute");
    expect(bridgeRequest).not.toHaveBeenCalledWith(
      "library.permanently_delete",
      expect.anything(),
    );

    await wrapper.get(".operation-dialog input[type='text']").setValue("execute");
    await buttonByText(wrapper, "确认执行").trigger("click");
    await flushPromises();
    expect(
      bridgeRequest.mock.calls.filter(
        ([method]) => method === "library.permanently_delete",
      ),
    ).toHaveLength(1);
    wrapper.unmount();
  });

  it("creates, renames, merges, and soft-deletes folders through service methods", async () => {
    const folderView = libraryView({
      scope: "folder:Ideas",
      folders: ["Ideas", "Archive"],
      entries: [folderEntry],
    });
    bridgeRequest.mockImplementation(async (method) => {
      if (method === "library.query") return folderView;
      if (method === "library.create_folder") return "Notes";
      if (method === "library.rename_folder") return "Notes";
      if (method === "library.merge_folders") return [];
      if (method === "library.soft_delete_folder") {
        return [
          {
            source: folderEntry.path,
            destination: `.trash/${folderEntry.path}`,
            error: null,
          },
        ];
      }
      throw new Error(`Unexpected method: ${method}`);
    });
    const wrapper = mount(LibraryView, { props: { runtime } });
    await flushPromises();

    await buttonByText(wrapper, "新建文件夹").trigger("click");
    await wrapper.get(".operation-dialog input").setValue("Notes");
    await buttonByText(wrapper, "确认执行").trigger("click");
    await flushPromises();
    expect(bridgeRequest).toHaveBeenCalledWith("library.create_folder", {
      name: "Notes",
    });

    await buttonByText(wrapper, "重命名").trigger("click");
    await wrapper.get(".operation-dialog input").setValue("Notes");
    await buttonByText(wrapper, "确认执行").trigger("click");
    await flushPromises();
    expect(bridgeRequest).toHaveBeenCalledWith("library.rename_folder", {
      folder: "Ideas",
      new_name: "Notes",
    });

    await buttonByText(wrapper, "合并到…").trigger("click");
    await wrapper.get(".operation-dialog select").setValue("Archive");
    await buttonByText(wrapper, "确认执行").trigger("click");
    await flushPromises();
    expect(bridgeRequest).toHaveBeenCalledWith("library.merge_folders", {
      source: "Ideas",
      destination: "Archive",
    });

    await buttonByText(wrapper, "文件夹移至 Trash").trigger("click");
    await buttonByText(wrapper, "确认执行").trigger("click");
    await flushPromises();
    expect(bridgeRequest).toHaveBeenCalledWith(
      "library.soft_delete_folder",
      { folder: "Ideas" },
    );
    wrapper.unmount();
  });

  it("restores a Trash folder and permanently deletes its explicit Papers first", async () => {
    const trashedEntry = {
      ...folderEntry,
      path: ".trash/cache/Ideas/K-20260725-002.md",
      trashed: true,
    };
    const trashView = libraryView({
      scope: "trash",
      entries: [trashedEntry],
      folders: [],
      trash_folders: ["Ideas"],
      trash_count: 1,
      errors: [],
    });
    bridgeRequest.mockImplementation(async (method, params) => {
      if (method === "library.query") return trashView;
      if (method === "library.restore_folder") {
        return [{
          source: ".trash/cache/Ideas",
          destination: "cache/Ideas",
          error: null,
        }];
      }
      if (method === "library.restore") {
        return [{
          source: trashedEntry.path,
          destination: folderEntry.path,
          error: null,
        }];
      }
      if (method === "library.permanently_delete") {
        return params.paths.map((path) => ({
          source: path,
          destination: null,
          error: null,
        }));
      }
      if (method === "library.permanently_delete_folder") {
        return {
          source: ".trash/cache/Ideas",
          destination: null,
          error: null,
        };
      }
      throw new Error(`Unexpected method: ${method}`);
    });
    const wrapper = mount(LibraryView, { props: { runtime } });
    await flushPromises();

    await wrapper.findAll(".detail-actions button")[4].trigger("click");
    await flushPromises();
    expect(bridgeRequest).toHaveBeenCalledWith("library.restore", {
      paths: [trashedEntry.path],
    });

    const folderButtons = wrapper.findAll(".trash-folders button");
    await folderButtons[0].trigger("click");
    await flushPromises();
    expect(bridgeRequest).toHaveBeenCalledWith("library.restore_folder", {
      folder: "Ideas",
    });

    await wrapper.findAll(".trash-folders button")[1].trigger("click");
    await flushPromises();
    await buttonByText(wrapper, "确认执行").trigger("click");
    await flushPromises();
    expect(bridgeRequest).toHaveBeenCalledWith(
      "library.permanently_delete",
      { paths: [trashedEntry.path] },
    );
    expect(bridgeRequest).toHaveBeenCalledWith(
      "library.permanently_delete_folder",
      { folder: "Ideas" },
    );
    wrapper.unmount();
  });
});
