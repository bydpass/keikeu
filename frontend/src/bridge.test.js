import { beforeEach, describe, expect, it, vi } from "vitest";

import { invoke } from "@tauri-apps/api/core";
import { bridgeRequest, openSystemTarget } from "./bridge.js";

vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(),
}));

describe("Tauri bridge envelope", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("returns only a successful JSONL result", async () => {
    invoke.mockResolvedValue({
      v: 1,
      id: 7,
      ok: true,
      result: { state: "ready" },
    });

    await expect(bridgeRequest("startup.load", {})).resolves.toEqual({
      state: "ready",
    });
    expect(invoke).toHaveBeenCalledWith("bridge_request", {
      method: "startup.load",
      params: {},
    });
  });

  it("rejects with the structured layer error", async () => {
    const error = {
      code: "stale_snapshot",
      layer: "application_service",
      message: "Paper changed externally",
      recovery: "reopen",
    };
    invoke.mockResolvedValue({ v: 1, id: 8, ok: false, error });

    await expect(bridgeRequest("paper.save", {})).rejects.toEqual(error);
  });

  it("passes only a validated action and relative target to the narrow host command", async () => {
    invoke.mockResolvedValue(undefined);

    await openSystemTarget("reveal", "cache/Ideas/K-001.md");

    expect(invoke).toHaveBeenCalledWith("open_system_target", {
      action: "reveal",
      relativeTarget: "cache/Ideas/K-001.md",
    });
  });
});
