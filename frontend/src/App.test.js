import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App.vue";
import { getRuntimeStatus, restartSidecar } from "./bridge.js";

vi.mock("./bridge.js", () => ({
  getRuntimeStatus: vi.fn(),
  restartSidecar: vi.fn(),
}));

describe("CP4 runtime gate", () => {
  beforeEach(() => {
    vi.resetAllMocks();
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
});
