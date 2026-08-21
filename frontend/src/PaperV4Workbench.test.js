import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import PaperV4Workbench from "./PaperV4Workbench.vue";

function paper(overrides = {}) {
  return {
    code: "K-20260802-001",
    path: "cache/夜车/K-20260802-001.md",
    display_name: "夜车",
    tags: ["夜车", "重逢,旧友"],
    pages: [
      { name: "第一页", content: "012345", type: "summary" },
      { name: "第二页", content: "另一段", type: "snapshot" },
    ],
    created: "2026-08-02T10:00:00",
    updated: "2026-08-02T10:30:00",
    ...overrides,
  };
}

function buttonByText(wrapper, text) {
  const button = wrapper.findAll("button").find((item) => item.text() === text);
  if (!button) throw new Error(`button not found: ${text}`);
  return button;
}

const mounted = [];
function mountWorkbench(options = {}) {
  const wrapper = mount(PaperV4Workbench, {
    attachTo: document.body,
    props: { paper: paper(), ...options },
  });
  mounted.push(wrapper);
  return wrapper;
}

afterEach(() => {
  while (mounted.length) mounted.pop().unmount();
});

describe("PaperV4Workbench", () => {
  it("renders Paper context, closed native details, and the three locked actions", () => {
    const wrapper = mountWorkbench();

    expect(wrapper.get(".paper-meta-bar").attributes("aria-label")).toBe("Paper context");
    expect(wrapper.get(".paper-context-state").text()).toContain("2 页");
    expect(wrapper.get(".paper-details").attributes("open")).toBeUndefined();
    expect(wrapper.get(".paper-code strong").text()).toBe("K-20260802-001");
    expect(wrapper.get(".paper-details").text()).toContain("cache/夜车/K-20260802-001.md");
    expect(wrapper.get(".paper-details").text()).toContain("2026-08-02T10:30:00");
    expect(wrapper.text()).not.toContain("草稿与已保存基线一致");
    expect(wrapper.findAll(".card-actions > button").map((item) => item.text())).toEqual([
      "保存",
      "删除本页",
      "加一页",
    ]);
    expect(wrapper.get(".type-badge").text()).toBe("总结");
  });

  it("keeps page name in basic mode and never clears a hidden type", async () => {
    const wrapper = mountWorkbench();
    const title = wrapper.get(".page-title-field input");
    await title.setValue("始终可编辑");
    expect(wrapper.get(".paper-context-state").text()).toContain("草稿有未保存修改");
    await buttonByText(wrapper, "进一步").trigger("click");
    await wrapper.get(".advanced-panel select").setValue("whisper");
    const cardChildren = [...wrapper.get(".card-page").element.children];
    expect(cardChildren.indexOf(wrapper.get(".page-content-field").element)).toBeLessThan(
      cardChildren.indexOf(wrapper.get(".advanced-controls").element),
    );
    expect(cardChildren.indexOf(wrapper.get(".advanced-panel").element)).toBeLessThan(
      cardChildren.indexOf(wrapper.get(".card-actions").element),
    );
    await buttonByText(wrapper, "收起进一步").trigger("click");

    expect(wrapper.get(".page-title-field input").element.value).toBe("始终可编辑");
    expect(wrapper.get(".type-badge").text()).toBe("碎碎念");
  });

  it("keeps Summary visible but disabled when another page already owns it", async () => {
    const wrapper = mountWorkbench();
    await wrapper.findAll(".page-navigation > button")[1].trigger("click");
    await buttonByText(wrapper, "进一步").trigger("click");

    const summary = wrapper.get('.advanced-panel option[value="summary"]');
    expect(summary.attributes("disabled")).toBeDefined();
    expect(wrapper.text()).toContain("已有一页标为总结");
  });

  it("splits at selectionStart and moves selected plus following text without loss", async () => {
    const wrapper = mountWorkbench();
    const textarea = wrapper.get(".page-content-field textarea");
    textarea.element.setSelectionRange(2, 4);
    await textarea.trigger("select");
    await buttonByText(wrapper, "加一页").trigger("click");

    expect(wrapper.findAll(".page-navigation > button")).toHaveLength(3);
    expect(wrapper.get(".page-content-field textarea").element.value).toBe("2345");
    await wrapper.findAll(".page-navigation > button")[0].trigger("click");
    expect(wrapper.get(".page-content-field textarea").element.value).toBe("01");
    expect(document.activeElement).toBe(wrapper.get(".page-title-field input").element);
  });

  it("splits at the end when the content field never had a cursor", async () => {
    const wrapper = mountWorkbench();
    await buttonByText(wrapper, "加一页").trigger("click");

    expect(wrapper.get(".page-content-field textarea").element.value).toBe("");
    await wrapper.findAll(".page-navigation > button")[0].trigger("click");
    expect(wrapper.get(".page-content-field textarea").element.value).toBe("012345");
  });

  it("deletes a normal page and replaces the unique page with a blank draft", async () => {
    const wrapper = mountWorkbench();
    await buttonByText(wrapper, "删除本页").trigger("click");
    expect(wrapper.get(".delete-page-dialog").attributes("open")).toBeDefined();
    await buttonByText(wrapper, "确认删除").trigger("click");
    expect(wrapper.find(".page-navigation").exists()).toBe(false);
    expect(wrapper.get(".paper-context-state").text()).toContain("1 页");
    expect(document.activeElement).toBe(wrapper.get(".page-title-field input").element);

    await buttonByText(wrapper, "删除本页").trigger("click");
    await buttonByText(wrapper, "确认删除").trigger("click");
    expect(wrapper.get(".page-title-field input").element.value).toBe("");
    expect(wrapper.get(".page-content-field textarea").element.value).toBe("");
  });

  it("hides single-page navigation and marks only the current multi-page button", async () => {
    const single = mountWorkbench({
      paper: paper({ pages: [{ name: "唯一页", content: "正文", type: null }] }),
    });
    expect(single.find(".page-navigation").exists()).toBe(false);

    const multiple = mountWorkbench();
    const pageButtons = multiple.findAll(".page-navigation > button");
    expect(pageButtons[0].attributes("aria-current")).toBe("page");
    expect(pageButtons[1].attributes("aria-current")).toBeUndefined();
    await pageButtons[1].trigger("click");
    expect(pageButtons[0].attributes("aria-current")).toBeUndefined();
    expect(pageButtons[1].attributes("aria-current")).toBe("page");
  });

  it("normalizes names and newline Tags only in the emitted Save DTO", async () => {
    const wrapper = mountWorkbench();
    await wrapper.get(".paper-meta-bar input").setValue("  新名称  ");
    await wrapper.get(".paper-meta-bar textarea").setValue("a,b\n a,b \n c ");
    await buttonByText(wrapper, "保存").trigger("click");

    const saved = wrapper.emitted("save")[0][0];
    expect(saved.display_name).toBe("新名称");
    expect(saved.tags).toEqual(["a,b", "c"]);
    expect(saved.pages[0].content).toBe("012345");
    expect(JSON.stringify(saved)).not.toContain("ui_key");
  });

  it("uses Unicode code points and Core-equivalent blank-page validation", async () => {
    const wrapper = mountWorkbench({
      paper: paper({ pages: [{ name: "标题", content: "", type: null }] }),
    });
    await wrapper.get(".page-title-field input").setValue("🌙".repeat(201));
    await buttonByText(wrapper, "保存").trigger("click");
    expect(wrapper.emitted("save")).toBeUndefined();
    expect(wrapper.text()).toContain("最多 200 个 Unicode 字符");

    await wrapper.get(".page-title-field input").setValue("");
    await wrapper.get(".page-content-field textarea").setValue(" \n\t");
    await buttonByText(wrapper, "保存").trigger("click");
    expect(wrapper.text()).toContain("需要标题或正文");

    await wrapper.get(".page-title-field input").setValue("🌙".repeat(200));
    await buttonByText(wrapper, "保存").trigger("click");
    expect(wrapper.emitted("save")).toHaveLength(1);
  });

  it("routes Cmd+S through the same save action and protects dirty unload", async () => {
    const wrapper = mountWorkbench();
    await wrapper.get(".page-content-field textarea").setValue("changed");
    const leaving = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(leaving);
    expect(leaving.defaultPrevented).toBe(true);

    await wrapper.trigger("keydown", { key: "s", metaKey: true });
    expect(wrapper.emitted("save")).toHaveLength(1);
  });

  it("freezes the draft while saving and exposes whole-Paper delete only when ready", async () => {
    const wrapper = mountWorkbench({ canDeleteWholePaper: true });
    await buttonByText(wrapper, "进一步").trigger("click");
    await wrapper.setProps({ saving: true });

    expect(wrapper.get(".paper-context-state").text()).toContain("正在保存");
    expect(buttonByText(wrapper, "保存").attributes("disabled")).toBeDefined();
    expect(wrapper.findAll("input, textarea").every((field) => (
      field.attributes("readonly") !== undefined
    ))).toBe(true);
    expect(wrapper.get(".advanced-panel select").attributes("disabled")).toBeDefined();
    expect(wrapper.get(".mode-toggle").attributes("disabled")).toBeDefined();
    expect(buttonByText(wrapper, "删除本页").attributes("disabled")).toBeDefined();
    expect(buttonByText(wrapper, "加一页").attributes("disabled")).toBeDefined();
    expect(buttonByText(wrapper, "整份移入废纸篓").attributes("disabled")).toBeDefined();
    await wrapper.trigger("keydown", { key: "s", metaKey: true });
    expect(wrapper.emitted("save")).toBeUndefined();

    const ready = mountWorkbench({ canDeleteWholePaper: true });
    await buttonByText(ready, "整份移入废纸篓").trigger("click");
    expect(ready.emitted("whole-delete")).toHaveLength(1);
  });

  it.each(["stale", "repair_required", "commit_unknown"])(
    "retains the draft and blocks Save in %s",
    async (state) => {
      const wrapper = mountWorkbench({ state });
      expect(wrapper.get(".workbench-state").text()).not.toBe("");
      expect(buttonByText(wrapper, "保存").attributes("disabled")).toBeDefined();
    },
  );
});
