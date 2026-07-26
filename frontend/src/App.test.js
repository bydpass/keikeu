import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App.vue";
import PrototypeView from "./PrototypeView.vue";
import { getRuntimeStatus, restartSidecar } from "./bridge.js";

vi.mock("./bridge.js", () => ({
  getRuntimeStatus: vi.fn(),
  restartSidecar: vi.fn(),
}));

describe("desktop shell gates", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    window.history.replaceState({}, "", "/");
  });

  it("unblocks only after the host is ready", async () => {
    getRuntimeStatus.mockResolvedValue({
      state: "ready",
      app_version: "0.1.0",
      core_version: "paper-v3/index-v3",
    });

    const wrapper = mount(App);
    await flushPromises();

    expect(wrapper.text()).toContain("Python Core 已连接");
    expect(wrapper.text()).toContain("paper-v3/index-v3");
  });

  it("shows the host layer and can request a restart", async () => {
    getRuntimeStatus.mockResolvedValue({
      state: "blocked",
      error: {
        code: "protocol_mismatch",
        layer: "tauri_host",
        message: "Sidecar 协议不兼容。",
        recovery: "restart_sidecar",
      },
    });
    restartSidecar.mockResolvedValue({
      state: "ready",
      app_version: "0.1.0",
      core_version: "paper-v3/index-v3",
    });

    const wrapper = mount(App);
    await flushPromises();
    expect(wrapper.text()).toContain("protocol_mismatch");
    expect(wrapper.text()).toContain("tauri_host");

    await wrapper.get("button").trigger("click");
    await flushPromises();

    expect(restartSidecar).toHaveBeenCalledOnce();
    expect(wrapper.text()).toContain("Python Core 已连接");
  });

  it("keeps the synthetic prototype isolated from the bridge", async () => {
    window.history.replaceState({}, "", "/?prototype=1");

    const wrapper = mount(App);
    await flushPromises();

    expect(wrapper.find(".runtime-gate").exists()).toBe(false);
    expect(getRuntimeStatus).not.toHaveBeenCalled();
  });

  it("renders the CP5 specimen with synthetic data only", () => {
    const wrapper = mount(PrototypeView);

    expect(wrapper.text()).toContain("合成样张");
    expect(wrapper.text()).toContain("不连接 Vault");
    expect(wrapper.text()).toContain("3 synthetic Papers");
  });

  it("keeps specimen filtering, selection, and reordering in memory", async () => {
    const wrapper = mount(PrototypeView);

    await wrapper.get('input[type="search"]').setValue("角色");
    const matchingPapers = wrapper.findAll(".paper-list button");
    expect(matchingPapers).toHaveLength(1);
    await matchingPapers[0].trigger("click");
    expect(wrapper.get(".workspace-header h2").text()).toBe("角色动机");

    const menuButtons = wrapper.findAll(".row-actions > button");
    expect(menuButtons).toHaveLength(2);
    await menuButtons[1].trigger("click");
    const moveButtons = wrapper.findAll(".row-menu button");
    expect(moveButtons.map((button) => button.text())).toEqual(["上移", "下移"]);
    await moveButtons[0].trigger("click");

    expect(
      wrapper.findAll(".highlight-row strong").map((highlight) => highlight.text()),
    ).toEqual(["行动压力", "表层理由"]);
    expect(getRuntimeStatus).not.toHaveBeenCalled();
  });
});
