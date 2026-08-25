import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { defineComponent, h } from "vue";

import LibraryV4Projection from "./LibraryV4Projection.vue";
import projectionSource from "./LibraryV4Projection.vue?raw";

const entries = [
  {
    path: "cache/夜车/K-20260802-001.md",
    code: "K-20260802-001",
    display_name: "夜车",
    folder: "夜车",
    tags: ["重逢", "暴食"],
    preview: "第一页原文",
    page_count: 2,
    page_names: ["开场", "回声"],
    created: "2026-08-02T10:00:00",
    updated: "2026-08-02T11:00:00",
  },
  {
    path: "cache/K-20260802-002.md",
    code: "K-20260802-002",
    display_name: null,
    folder: null,
    tags: [],
    preview: "另一条",
    page_count: 1,
    page_names: [],
    created: "2026-08-02T12:00:00",
    updated: "2026-08-02T12:00:00",
  },
];

describe("LibraryV4Projection", () => {
  it("shows Paper fallback labels, page metadata, and searches every page name", async () => {
    const wrapper = mount(LibraryV4Projection, { props: { entries } });
    expect(wrapper.text()).toContain("K-20260802-002");
    expect(wrapper.text()).toContain("2 页");

    await wrapper.get('input[type="search"]').setValue("回声");
    expect(wrapper.findAll(".library-v4-list > li")).toHaveLength(1);
    expect(wrapper.get(".library-v4-list strong").text()).toBe("夜车");
  });

  it("opens the whole selected Paper without a page deep-link", async () => {
    const wrapper = mount(LibraryV4Projection, { props: { entries } });
    const second = wrapper.findAll(".library-v4-list > li")[1];
    await second.get(".library-paper-trigger").trigger("click");
    await second.get(".open-paper").trigger("click");

    expect(wrapper.emitted("open")[0]).toEqual(["cache/K-20260802-002.md"]);
    expect(wrapper.text()).toContain("始终从第一页打开");
  });

  it("keeps the detail and open action aligned with a filtered result", async () => {
    const wrapper = mount(LibraryV4Projection, { props: { entries } });
    await wrapper.get('input[type="search"]').setValue("另一条");
    await wrapper.get(".open-paper").trigger("click");

    expect(wrapper.get(".library-preview-popover h3").text()).toBe("K-20260802-002");
    expect(wrapper.emitted("open")[0]).toEqual(["cache/K-20260802-002.md"]);
  });

  it("keeps preview in a native top-layer popover outside the result flow", () => {
    const wrapper = mount(LibraryV4Projection, { props: { entries } });
    const rows = wrapper.findAll(".library-v4-list > li");
    const triggers = wrapper.findAll(".library-paper-trigger");
    const popovers = wrapper.findAll(".library-preview-popover");

    expect(popovers).toHaveLength(entries.length);
    rows.forEach((row, index) => {
      const popover = popovers[index];
      const target = popover.attributes("id");
      expect(row.element.children[0]).toBe(triggers[index].element);
      expect(row.element.children[1]).toBe(popover.element);
      expect(triggers[index].attributes()).toMatchObject({
        popovertarget: target,
        popovertargetaction: "show",
      });
      expect(triggers[index].attributes("aria-expanded")).toBeUndefined();
      expect(popover.attributes("popover")).toBe("auto");
      expect(popover.attributes("role")).toBe("dialog");
      expect(popover.get('button[aria-label="关闭 Paper 预览"]').attributes()).toMatchObject({
        popovertarget: target,
        popovertargetaction: "hide",
      });
      expect(popover.get('button[aria-label="关闭 Paper 预览"]').attributes("autofocus")).toBeUndefined();
      expect(popover.get(".open-paper").attributes("popovertargetaction")).toBe("hide");
    });
  });

  it("does not issue search events until Chinese IME composition commits", async () => {
    const wrapper = mount(LibraryV4Projection, { props: { entries } });
    const input = wrapper.get('input[type="search"]');
    await input.trigger("compositionstart");
    input.element.value = "b";
    await input.trigger("input");
    input.element.value = "ba";
    await input.trigger("input");

    expect(wrapper.emitted("search")).toBeUndefined();

    input.element.value = "暴食";
    await input.trigger("compositionend");

    expect(wrapper.emitted("search")).toEqual([["暴食"]]);
    expect(input.element.value).toBe("暴食");
    expect(wrapper.findAll(".library-v4-list > li")).toHaveLength(1);
  });

  it("gives every mounted preview popover a unique target id", () => {
    const host = mount(defineComponent({
      render: () => h("div", [
        h(LibraryV4Projection, { entries }),
        h(LibraryV4Projection, { entries }),
      ]),
    }));
    const popovers = host.findAll(".library-preview-popover");
    const ids = popovers.map((popover) => popover.attributes("id"));

    expect(new Set(ids).size).toBe(ids.length);
  });

  it("keeps preview targets unique when damaged data repeats a Paper code", () => {
    const duplicateCodeEntries = [
      entries[0],
      { ...entries[0], path: "cache/副本/K-20260802-001.md", folder: "副本" },
    ];
    const wrapper = mount(LibraryV4Projection, {
      props: { entries: duplicateCodeEntries },
    });
    const ids = wrapper.findAll(".library-preview-popover")
      .map((popover) => popover.attributes("id"));

    expect(new Set(ids).size).toBe(ids.length);
  });

  it("allows maximum-length unbroken names to wrap in rows and preview", () => {
    const longName = "x".repeat(200);
    const wrapper = mount(LibraryV4Projection, {
      props: {
        entries: [{
          ...entries[0],
          display_name: longName,
          folder: longName,
        }],
      },
    });

    expect(wrapper.get(".library-paper-trigger strong").text()).toBe(longName);
    expect(wrapper.get(".library-paper-trigger small").text()).toBe(longName);
    expect(wrapper.get(".library-preview-popover h3").text()).toBe(longName);
    expect(projectionSource).toMatch(
      /\.library-paper-trigger strong\s*\{[^}]*overflow-wrap: anywhere/s,
    );
    expect(projectionSource).toMatch(
      /\.library-paper-trigger span,\s*\.library-paper-trigger small\s*\{[^}]*overflow-wrap: anywhere/s,
    );
    expect(projectionSource).toMatch(
      /\.library-preview-popover h3\s*\{[^}]*overflow-wrap: anywhere/s,
    );
  });

  it("keeps index degradation and repair rows explicit", async () => {
    const wrapper = mount(LibraryV4Projection, {
      props: {
        entries,
        indexState: "degraded",
        errors: [{ path: "cache/broken.md", reason: "page marker 缺失" }],
      },
    });
    expect(wrapper.text()).toContain("Index 可能过期");
    expect(wrapper.text()).toContain("cache/broken.md");
    await wrapper.get(".index-warning button").trigger("click");
    expect(wrapper.emitted("rebuild-index")).toHaveLength(1);
  });
});
