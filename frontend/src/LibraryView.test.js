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

describe("CP8 Library read slice", () => {
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
});
