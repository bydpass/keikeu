import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import LibraryV4Projection from "./LibraryV4Projection.vue";

const entries = [
  {
    path: "cache/夜车/K-20260802-001.md",
    code: "K-20260802-001",
    display_name: "夜车",
    folder: "夜车",
    tags: ["重逢"],
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
    await wrapper.findAll(".library-v4-list button")[1].trigger("click");
    await wrapper.get(".open-paper").trigger("click");

    expect(wrapper.emitted("open")[0]).toEqual(["cache/K-20260802-002.md"]);
    expect(wrapper.text()).toContain("始终从第一页打开");
  });

  it("keeps the detail and open action aligned with a filtered result", async () => {
    const wrapper = mount(LibraryV4Projection, { props: { entries } });
    await wrapper.get('input[type="search"]').setValue("另一条");
    await wrapper.get(".open-paper").trigger("click");

    expect(wrapper.get(".library-v4-detail h3").text()).toBe("K-20260802-002");
    expect(wrapper.emitted("open")[0]).toEqual(["cache/K-20260802-002.md"]);
  });

  it("keeps results before detail when the layout stacks", () => {
    const wrapper = mount(LibraryV4Projection, { props: { entries } });
    const children = wrapper.get(".library-v4-layout").element.children;

    expect(children[0].getAttribute("aria-labelledby")).toBe("library-results-title");
    expect(children[1].classList.contains("library-v4-detail")).toBe(true);
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
