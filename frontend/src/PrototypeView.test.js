import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import PrototypeView from "./PrototypeView.vue";

function buttonByText(wrapper, text) {
  const button = wrapper.findAll("button").find((item) => item.text() === text);
  if (!button) throw new Error(`button not found: ${text}`);
  return button;
}

describe("Road v0.6 development-only prototype", () => {
  it("labels the synthetic no-Vault boundary and exposes Paper plus Library", async () => {
    const wrapper = mount(PrototypeView);
    expect(wrapper.text()).toContain("合成样张 · 不连接 Vault");
    expect(wrapper.text()).toContain("3 synthetic Papers");
    await buttonByText(wrapper, "Library").trigger("click");
    expect(wrapper.get(".library-v4-projection").exists()).toBe(true);
  });

  it("uses one candidate component for synthetic save and Library reopen", async () => {
    const wrapper = mount(PrototypeView);
    await wrapper.get(".page-title-field input").setValue("新页名");
    await buttonByText(wrapper, "保存").trigger("click");
    expect(wrapper.text()).toContain("合成保存完成");

    await buttonByText(wrapper, "Library").trigger("click");
    await wrapper.findAll(".library-v4-list button")[1].trigger("click");
    await wrapper.get(".open-paper").trigger("click");
    expect(wrapper.get(".paper-code strong").text()).toBe("K-20260801-004");
  });

  it("renders every approved synthetic recovery state", async () => {
    const wrapper = mount(PrototypeView);
    const selector = wrapper.get(".prototype-toolbar select");
    for (const state of ["stale", "repair_required", "index_degraded", "commit_unknown"]) {
      await selector.setValue(state);
      expect(wrapper.get(".workbench-state").text()).not.toBe("");
    }
  });
});
