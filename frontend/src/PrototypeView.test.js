import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import PrototypeView from "./PrototypeView.vue";
import prototypeSource from "./PrototypeView.vue?raw";

function buttonByText(wrapper, text) {
  const button = wrapper.findAll("button").find((item) => item.text() === text);
  if (!button) throw new Error(`button not found: ${text}`);
  return button;
}

describe("Road v0.7 development-only prototype", () => {
  it("shows the compact Shell and marks the current daily location semantically", async () => {
    const wrapper = mount(PrototypeView);
    expect(wrapper.text()).toContain("ROAD V0.7 · CP8 · DEVELOPMENT ONLY");
    expect(wrapper.text()).toContain("合成样张 · 不连接 Vault");
    expect(wrapper.text()).toContain("3 synthetic Papers");
    expect(wrapper.text()).not.toContain("草稿与合成基线一致");
    expect(wrapper.text()).not.toContain("草稿有未保存修改");
    expect(wrapper.findAll(".prototype-v07-topbar button").map((button) => button.text())).toEqual([
      "编辑 Paper",
      "新 Paper",
      "Library",
      "Vault",
    ]);
    expect(buttonByText(wrapper, "编辑 Paper").attributes("aria-current")).toBe("page");
    expect(wrapper.get(".prototype-v07-context-switch").text()).toBe("Vault");
    expect(wrapper.get(".prototype-v07-new-paper").text()).toBe("新 Paper");
    expect(wrapper.get("[aria-label='合成编辑 Paper 工作面']").exists()).toBe(true);

    const libraryButton = buttonByText(wrapper, "Library");
    await libraryButton.trigger("click");
    expect(libraryButton.attributes("aria-current")).toBe("page");
    expect(buttonByText(wrapper, "编辑 Paper").attributes("aria-current")).toBeUndefined();
    expect(wrapper.get(".library-v4-projection").exists()).toBe(true);
  });

  it("keeps the development Shell on the same fixed row", () => {
    const shellbarCss = prototypeSource.match(/\.prototype-v07-topbar \{([\s\S]*?)\}/)?.[1];
    const buttonCss = prototypeSource.match(/\.prototype-v07-topbar button \{([\s\S]*?)\}/)?.[1];
    expect(shellbarCss).toContain("grid-template-rows: 56px;");
    expect(shellbarCss).toContain("height: 56px;");
    expect(buttonCss).toContain("white-space: nowrap;");
    expect(prototypeSource).toMatch(
      /@media \(max-width: 479px\)[\s\S]*?\.prototype-v07-topbar \{[\s\S]*?gap: 0 2px;[\s\S]*?padding-inline: 8px;/,
    );
  });

  it("uses one candidate component for synthetic save and Library reopen", async () => {
    const wrapper = mount(PrototypeView);
    await wrapper.get(".page-title-field input").setValue("新页名");
    await buttonByText(wrapper, "保存").trigger("click");
    expect(wrapper.text()).toContain("合成保存完成");

    await buttonByText(wrapper, "Library").trigger("click");
    const second = wrapper.findAll(".library-v4-list > li")[1];
    await second.get(".library-paper-trigger").trigger("click");
    await second.get(".open-paper").trigger("click");
    expect(wrapper.get(".paper-code strong").text()).toBe("K-20260801-004");
  });

  it("starts and saves a new Paper only in synthetic memory", async () => {
    const wrapper = mount(PrototypeView);
    await buttonByText(wrapper, "新 Paper").trigger("click");
    expect(wrapper.get(".paper-code strong").text()).toBe("K-SYNTHETIC-NEW");
    expect(wrapper.get(".paper-name-input").element.value).toBe("");

    await wrapper.get(".page-title-field input").setValue("合成新页");
    await buttonByText(wrapper, "保存").trigger("click");
    expect(wrapper.text()).toContain("4 synthetic Papers");
    expect(wrapper.text()).toContain("合成保存完成；没有调用 Vault。");
  });

  it("separates normal Vault context from blocking recovery", async () => {
    const wrapper = mount(PrototypeView);
    const vaultButton = buttonByText(wrapper, "Vault");
    await vaultButton.trigger("click");
    expect(vaultButton.attributes("aria-current")).toBe("page");
    expect(wrapper.text()).toContain("环境入口 · 不是第三个日常位置");

    await buttonByText(wrapper, "查看阻塞恢复样张").trigger("click");
    expect(wrapper.get("#prototype-blocked-title").text()).toBe("保存结果暂时无法确认");
    expect(wrapper.text()).toContain("没有自动重发保存");
    expect(wrapper.find(".paper-v4-workbench").exists()).toBe(false);

    await buttonByText(wrapper, "返回 Vault 环境").trigger("click");
    expect(wrapper.get("#prototype-vault-title").text()).toBe("示例 Vault");
  });
});
