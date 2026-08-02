import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import PaperV4Workbench from "./PaperV4Workbench.vue";

function paper(overrides = {}) {
  return {
    code: "K-20260802-001",
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
  it("renders one card page with exactly the three locked bottom actions", () => {
    const wrapper = mountWorkbench();

    expect(wrapper.get(".paper-code strong").text()).toBe("K-20260802-001");
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
    await buttonByText(wrapper, "进一步").trigger("click");
    await wrapper.get(".advanced-panel select").setValue("whisper");
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

    expect(wrapper.findAll(".page-navigation > button")).toHaveLength(4);
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
    expect(wrapper.text()).toContain("1 / 1");
    expect(document.activeElement).toBe(wrapper.get(".page-title-field input").element);

    await buttonByText(wrapper, "删除本页").trigger("click");
    await buttonByText(wrapper, "确认删除").trigger("click");
    expect(wrapper.get(".page-title-field input").element.value).toBe("");
    expect(wrapper.get(".page-content-field textarea").element.value).toBe("");
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

  it.each(["stale", "repair_required", "commit_unknown"])(
    "retains the draft and blocks Save in %s",
    async (state) => {
      const wrapper = mountWorkbench({ state });
      expect(wrapper.get(".workbench-state").text()).not.toBe("");
      expect(buttonByText(wrapper, "保存").attributes("disabled")).toBeDefined();
    },
  );
});
