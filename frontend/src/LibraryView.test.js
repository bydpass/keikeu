import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import LibraryView from "./LibraryView.vue";
import libraryViewSource from "./LibraryView.vue?raw";
import { confirmAction, openSystemTarget } from "./bridge.js";

vi.mock("./bridge.js", () => ({
  bridgeRequest: vi.fn(),
  confirmAction: vi.fn(),
  openSystemTarget: vi.fn(),
}));

const runtime = { state: "ready", core_version: "paper-v4/index-v4" };
const readyStartup = { state: "ready", vault_locator: "vault-v1:test" };
const pickerStartup = { state: "vault_picker", vault_locator: null };
const active = {
  path: "cache/Ideas/K-20260802-001.md",
  code: "K-20260802-001",
  display_name: "Night Train",
  folder: "Ideas",
  tags: ["night"],
  preview: "A train waits outside the city.",
  page_count: 2,
  page_names: ["Platform", "Window"],
  created: "2026-08-02T12:00:00",
  updated: "2026-08-02T13:00:00",
  trashed: false,
  repair_reason: null,
};
const trashed = {
  ...active,
  path: ".trash/cache/Ideas/K-20260802-001.md",
  trashed: true,
};

function library(overrides = {}) {
  return {
    scope: "all",
    entries: [active],
    folders: ["Ideas", "Drafts"],
    trash_folders: ["Old"],
    trash_count: 1,
    errors: [{ path: "cache/broken.md", reason: "page marker missing" }],
    vault_locator: "vault-v1:test",
    index_state: "current",
    ...overrides,
  };
}

function buttonByText(wrapper, text) {
  const button = wrapper.findAll("button").find((item) => item.text() === text);
  if (!button) throw new Error(`button not found: ${text}`);
  return button;
}

function inputByLabel(wrapper, text) {
  const label = wrapper.findAll("label").find((item) => item.text().startsWith(text));
  if (!label) throw new Error(`label not found: ${text}`);
  return label.get("input");
}

const mounted = [];
async function mountLibrary(request, extra = {}) {
  const wrapper = mount(LibraryView, {
    attachTo: document.body,
    props: { runtime, request, ...extra },
  });
  mounted.push(wrapper);
  await flushPromises();
  return wrapper;
}

beforeEach(() => {
  vi.resetAllMocks();
  confirmAction.mockResolvedValue(true);
});

afterEach(() => {
  while (mounted.length) mounted.pop().unmount();
  vi.restoreAllMocks();
});

describe("Road v0.7 Library runtime", () => {
  it("leaves navigation and product identity to the App Shell", async () => {
    const wrapper = await mountLibrary(vi.fn(async () => library()));

    expect(wrapper.find(".library-shell-header").exists()).toBe(false);
    expect(wrapper.findAll("button").some((button) => button.text() === "新 Paper")).toBe(false);
    expect(wrapper.findAll("button").some((button) => button.text() === "Vault")).toBe(false);
  });

  it("renders the accepted v4 projection", async () => {
    const request = vi.fn(async () => library());
    const wrapper = await mountLibrary(request);

    expect(wrapper.text()).toContain("Night Train");
    expect(wrapper.text()).toContain("2 页");
    expect(wrapper.text()).toContain("Platform · Window");
    expect(wrapper.text()).toContain("cache/broken.md");
  });

  it("passes scope, all-page search, sort, and verification to Python", async () => {
    const request = vi.fn(async (_method, params) => library({ scope: params.scope }));
    const wrapper = await mountLibrary(request);

    await buttonByText(wrapper, "Ideas").trigger("click");
    await flushPromises();
    await wrapper.get('.library-v4-header input[type="search"]').setValue("Window");
    await flushPromises();
    await wrapper.get(".library-toolbar select").setValue("name");
    await flushPromises();

    expect(request.mock.calls.some(([method, params]) =>
      method === "library.query" && params.scope === "folder:Ideas"
      && params.search === "Window" && params.sort === "name"
    )).toBe(true);
  });

  it("waits for Chinese IME composition before querying the service", async () => {
    const request = vi.fn(async (_method, params) => library({ scope: params.scope }));
    const wrapper = await mountLibrary(request);
    const input = wrapper.get('.library-v4-header input[type="search"]');
    const initialQueries = request.mock.calls.filter(([method]) => (
      method === "library.query"
    )).length;

    await input.trigger("compositionstart");
    input.element.value = "b";
    await input.trigger("input");
    input.element.value = "ba";
    await input.trigger("input");
    await flushPromises();

    expect(request.mock.calls.filter(([method]) => (
      method === "library.query"
    ))).toHaveLength(initialQueries);

    input.element.value = "暴食";
    await input.trigger("compositionend");
    input.element.value = "暴食";
    await input.trigger("input");
    await flushPromises();

    const newQueries = request.mock.calls
      .filter(([method]) => method === "library.query")
      .slice(initialQueries);
    expect(newQueries).toHaveLength(1);
    expect(newQueries[0][1].search).toBe("暴食");
    expect(input.element.value).toBe("暴食");
  });

  it("moves the selected Paper once with the current locator and reads reports", async () => {
    const request = vi.fn(async (method) => {
      if (method === "library.query") return library();
      if (method === "library.move") return {
        reports: [{ source: active.path, destination: "cache/Drafts/K-20260802-001.md", error: null }],
        warnings: [],
      };
      throw new Error(method);
    });
    const wrapper = await mountLibrary(request);
    await wrapper.get('.paper-operations select[aria-label="目标文件夹"]').setValue("Drafts");

    await buttonByText(wrapper, "移动").trigger("click");
    await flushPromises();

    expect(request.mock.calls.filter(([method]) => method === "library.move")).toEqual([[
      "library.move",
      {
        paths: [active.path],
        destination_folder: "Drafts",
        vault_locator: "vault-v1:test",
      },
      expect.objectContaining({ family: "library_path", vault_locator: "vault-v1:test" }),
    ]]);
    expect(wrapper.text()).toContain("1 项成功，0 项失败");
  });

  it("never retries a branch whose commit result is unknown", async () => {
    const request = vi.fn(async (method) => {
      if (method === "library.query") return library();
      if (method === "library.branch") throw {
        code: "commit_unknown",
        layer: "tauri_host",
        message: "response lost",
        recovery: "restart_then_reload",
      };
      throw new Error(method);
    });
    const wrapper = await mountLibrary(request);

    await buttonByText(wrapper, "创建 Branch").trigger("click");
    await flushPromises();

    expect(request.mock.calls.filter(([method]) => method === "library.branch")).toHaveLength(1);
    expect(wrapper.emitted("runtime-blocked")).toHaveLength(1);
  });

  it("uses tagged Trash operations and never opens a trashed Paper", async () => {
    const request = vi.fn(async (method, params) => {
      if (method === "library.query") {
        return params.scope === "trash"
          ? library({ scope: "trash", entries: [trashed] })
          : library();
      }
      if (method === "library.restore") return {
        reports: [{ source: trashed.path, destination: active.path, error: null }], warnings: [],
      };
      throw new Error(method);
    });
    const wrapper = await mountLibrary(request);
    await buttonByText(wrapper, "废纸篓 · 1").trigger("click");
    await flushPromises();

    expect(wrapper.text()).not.toContain("编辑整份 Paper");
    await buttonByText(wrapper, "恢复").trigger("click");
    await flushPromises();
    expect(request).toHaveBeenCalledWith(
      "library.restore",
      { paths: [trashed.path], vault_locator: "vault-v1:test" },
      expect.objectContaining({ family: "library_path" }),
    );
  });

  it("routes permanent deletion through the async confirmation boundary", async () => {
    const browserConfirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    const request = vi.fn(async (method, params) => {
      if (method === "library.query") {
        return params.scope === "trash"
          ? library({ scope: "trash", entries: [trashed] })
          : library();
      }
      if (method === "library.permanently_delete") {
        return { reports: [{ source: trashed.path, destination: null, error: null }], warnings: [] };
      }
      throw new Error(method);
    });
    const wrapper = await mountLibrary(request);
    await buttonByText(wrapper, "废纸篓 · 1").trigger("click");
    await flushPromises();

    await buttonByText(wrapper, "永久删除").trigger("click");
    await flushPromises();

    expect(confirmAction).toHaveBeenCalledWith(
      "永久删除这份 Paper？此操作不可撤销。",
      { okLabel: "永久删除", cancelLabel: "取消" },
    );
    expect(browserConfirm).not.toHaveBeenCalled();
    expect(request).toHaveBeenCalledWith(
      "library.permanently_delete",
      { paths: [trashed.path], vault_locator: "vault-v1:test" },
      expect.objectContaining({ family: "library_path" }),
    );
  });

  it("keeps folder create, rename, merge, and soft-delete on the same service boundary", async () => {
    const request = vi.fn(async (method, params) => {
      if (method === "library.query") return library({ scope: params.scope });
      if (method === "library.create_folder") return { name: "New", warnings: [] };
      if (method === "library.rename_folder") return { name: "Renamed", warnings: [] };
      if (method === "library.merge_folders" || method === "library.soft_delete_folder") {
        return { reports: [], warnings: [] };
      }
      throw new Error(method);
    });
    const wrapper = await mountLibrary(request);
    await inputByLabel(wrapper, "新文件夹").setValue("New");
    await buttonByText(wrapper, "创建").trigger("click");
    await flushPromises();
    await buttonByText(wrapper, "Ideas").trigger("click");
    await flushPromises();
    await inputByLabel(wrapper, "新名称").setValue("Renamed");
    await buttonByText(wrapper, "重命名").trigger("click");
    await flushPromises();

    expect(request.mock.calls.some(([method]) => method === "library.create_folder")).toBe(true);
    expect(request.mock.calls.some(([method, params]) =>
      method === "library.rename_folder" && params.vault_locator === "vault-v1:test"
    )).toBe(true);
  });

  it("re-reads the renamed folder instead of leaving an all-Paper projection selected", async () => {
    const request = vi.fn(async (method, params) => {
      if (method === "library.query") {
        return library({
          scope: params.scope,
          entries: [],
          folders: params.scope === "folder:Renamed" ? ["Renamed"] : ["fixture——folder"],
          trash_folders: [],
          trash_count: 0,
        });
      }
      if (method === "library.rename_folder") {
        return { name: "Renamed", warnings: [] };
      }
      throw new Error(method);
    });
    const wrapper = await mountLibrary(request);
    await wrapper.get(".library-scope-select select").setValue("folder:fixture——folder");
    await flushPromises();
    await inputByLabel(wrapper, "新名称").setValue("Renamed");
    await buttonByText(wrapper, "重命名").trigger("click");
    await flushPromises();

    expect(wrapper.get(".library-scope-select select").element.value).toBe("folder:Renamed");
    expect(request).toHaveBeenLastCalledWith("library.query", {
      scope: "folder:Renamed",
      search: "",
      sort: "updated_desc",
      verify_index: true,
    });
  });

  it("uses one bounded compact scope control when folder count grows", async () => {
    const folders = ["Alpha", "Beta", "Gamma", "fixture——folder"];
    const request = vi.fn(async (method, params) => {
      if (method === "library.query") return library({ scope: params.scope, folders });
      throw new Error(method);
    });
    const wrapper = await mountLibrary(request);
    const compactScope = wrapper.get(".library-scope-select select");

    expect(compactScope.findAll("option").map((option) => option.text())).toEqual([
      "全部 Paper",
      "未归档",
      ...folders,
      "废纸篓 · 1",
      "↳ Old",
    ]);
    await compactScope.setValue("folder:fixture——folder");
    await flushPromises();

    expect(request).toHaveBeenLastCalledWith("library.query", {
      scope: "folder:fixture——folder",
      search: "",
      sort: "updated_desc",
      verify_index: false,
    });
  });

  it("keeps current-folder actions beside the scope instead of after Paper results", async () => {
    const request = vi.fn(async (_method, params) => library({ scope: params.scope }));
    const wrapper = await mountLibrary(request);

    await wrapper.get(".library-scope-select select").setValue("folder:Ideas");
    await flushPromises();

    const scopes = wrapper.get(".library-scopes");
    const operations = wrapper.get('.folder-operations[aria-label="当前文件夹操作"]');
    expect(scopes.element.contains(operations.element)).toBe(true);
    expect(wrapper.get(".library-main").element.contains(operations.element)).toBe(false);
  });

  it("bounds native controls when a folder name reaches the 200-character limit", async () => {
    const longFolder = "W".repeat(200);
    const request = vi.fn(async () => library({ folders: [longFolder] }));
    const wrapper = await mountLibrary(request);
    const destination = wrapper.get('.paper-operations select[aria-label="目标文件夹"]');

    expect(destination.findAll("option").at(1).text()).toBe(longFolder);
    expect(libraryViewSource).toMatch(
      /button, input, select \{[^}]*min-width: 0;[^}]*max-width: 100%;/s,
    );
    expect(libraryViewSource).toMatch(
      /@media \(max-width: 820px\)[\s\S]*?\.library-shell \{ grid-template-columns: minmax\(0, 1fr\);/,
    );
  });

  it("moves the complete folder tree without surfacing non-Paper cleanup blockers", async () => {
    let deleted = false;
    const request = vi.fn(async (method, params) => {
      if (method === "library.query") {
        return library({
          scope: params.scope,
          entries: [],
          folders: deleted ? [] : ["fixture——folder"],
          trash_folders: deleted ? ["fixture——folder"] : [],
          trash_count: 0,
        });
      }
      if (method === "library.soft_delete_folder") {
        deleted = true;
        return {
          reports: [{
            source: "cache/fixture——folder",
            destination: ".trash/cache/fixture——folder",
            error: null,
          }],
          warnings: [],
        };
      }
      throw new Error(method);
    });
    const wrapper = await mountLibrary(request);
    const compactScope = wrapper.get(".library-scope-select select");
    await compactScope.setValue("folder:fixture——folder");
    await flushPromises();
    await buttonByText(wrapper, "删除文件夹").trigger("click");
    await flushPromises();

    expect(request).toHaveBeenCalledWith(
      "library.soft_delete_folder",
      { folder: "fixture——folder", vault_locator: "vault-v1:test" },
      expect.objectContaining({ family: "library_path" }),
    );
    expect(confirmAction).toHaveBeenCalledWith(
      "将这个文件夹及其中全部内容移入废纸篓？",
      { okLabel: "移入废纸篓", cancelLabel: "取消" },
    );
    expect(wrapper.find(".library-error").exists()).toBe(false);
    expect(compactScope.element.value).toBe("all");
  });

  it("returns to all Papers only after folder deletion fully succeeds", async () => {
    let deleted = false;
    const request = vi.fn(async (method, params) => {
      if (method === "library.query") {
        return library({
          scope: params.scope,
          entries: [],
          folders: deleted ? [] : ["fixture——folder"],
          trash_folders: deleted ? ["fixture——folder"] : [],
          trash_count: 0,
        });
      }
      if (method === "library.soft_delete_folder") {
        deleted = true;
        return {
          reports: [{
            source: "cache/fixture——folder",
            destination: ".trash/cache/fixture——folder",
            error: null,
          }],
          warnings: [],
        };
      }
      throw new Error(method);
    });
    const wrapper = await mountLibrary(request);
    const compactScope = wrapper.get(".library-scope-select select");
    await compactScope.setValue("folder:fixture——folder");
    await flushPromises();
    await buttonByText(wrapper, "删除文件夹").trigger("click");
    await flushPromises();

    expect(compactScope.element.value).toBe("all");
    expect(wrapper.find(".library-error").exists()).toBe(false);
    expect(wrapper.text()).toContain("删除文件夹：1 项成功，0 项失败");
    expect(request).toHaveBeenLastCalledWith("library.query", {
      scope: "all",
      search: "",
      sort: "updated_desc",
      verify_index: true,
    });
  });

  it("names all hidden folder contents before permanent deletion", async () => {
    const request = vi.fn(async (_method, params) => library({
      scope: params.scope,
      entries: params.scope === "trash-folder:Old" ? [trashed] : [active],
    }));
    confirmAction.mockResolvedValueOnce(false);
    const wrapper = await mountLibrary(request);
    await wrapper.get(".library-scope-select select").setValue("trash-folder:Old");
    await flushPromises();

    await buttonByText(wrapper, "永久删除文件夹").trigger("click");

    expect(confirmAction).toHaveBeenCalledWith(
      "永久删除这个废纸篓文件夹及其中全部内容？此操作不可撤销。",
      { okLabel: "永久删除", cancelLabel: "取消" },
    );
    expect(request.mock.calls.some(([method]) => (
      method === "library.permanently_delete_folder"
    ))).toBe(false);
  });

  it("re-reads and settles a pending Library intent after restart", async () => {
    const request = vi.fn(async (method) =>
      method === "startup.load" ? readyStartup : library()
    );
    const wrapper = await mountLibrary(request, {
      pendingIntent: { family: "library_path", method: "library.move" },
    });

    expect(request.mock.calls.some(([method, params]) =>
      method === "library.query" && params.verify_index === true
    )).toBe(true);
    expect(wrapper.text()).toContain("已在重启后重新读取 Vault");
    expect(wrapper.emitted("intent-settled")).toHaveLength(1);
  });

  it("audits a pending Index rebuild without replaying it", async () => {
    const request = vi.fn(async (method) =>
      method === "startup.load"
        ? readyStartup
        : library({ index_state: "degraded" })
    );
    const wrapper = await mountLibrary(request, {
      pendingIntent: { family: "index", method: "library.rebuild" },
    });

    expect(request.mock.calls.some(([method, params]) =>
      method === "library.query" && params.verify_index === true
    )).toBe(true);
    expect(request.mock.calls.some(([method]) => method === "library.rebuild")).toBe(false);
    expect(wrapper.text()).toContain("Index 可能过期");
    expect(wrapper.emitted("intent-settled")).toHaveLength(1);
  });

  it("returns to the Vault gate when restart cannot restore an active Vault", async () => {
    const request = vi.fn(async (method) => {
      if (method === "startup.load") return pickerStartup;
      throw new Error(method);
    });
    const wrapper = await mountLibrary(request, {
      pendingIntent: { family: "library_path", method: "library.move" },
    });

    expect(wrapper.emitted("open-vault")[0]).toEqual([pickerStartup]);
    expect(request.mock.calls.some(([method]) => method === "library.query")).toBe(false);
    expect(wrapper.emitted("intent-settled")).toBeUndefined();
  });

  it("delegates only the selected relative path to the native open boundary", async () => {
    const wrapper = await mountLibrary(vi.fn(async () => library()));

    await buttonByText(wrapper, "默认编辑器打开").trigger("click");

    expect(openSystemTarget).toHaveBeenCalledWith("open", active.path);
  });

  it("reveals only a validated broken relative path", async () => {
    const wrapper = await mountLibrary(vi.fn(async () => library()));

    await wrapper.get(".library-errors summary").trigger("click");
    await buttonByText(wrapper, "在 Finder 中显示").trigger("click");

    expect(openSystemTarget).toHaveBeenCalledWith("reveal", "cache/broken.md");
  });

  it("classifies explicit Index rebuild separately from path mutations", async () => {
    const request = vi.fn(async (method) => {
      if (method === "library.query") return library({ index_state: "degraded" });
      if (method === "library.rebuild") return library({ index_state: "current" });
      throw new Error(method);
    });
    const wrapper = await mountLibrary(request);

    await buttonByText(wrapper, "显式重建 Index").trigger("click");
    await flushPromises();

    expect(request.mock.calls.find(([method]) => method === "library.rebuild")[2]).toMatchObject({
      family: "index",
      method: "library.rebuild",
    });
  });
});
