import { beforeEach, describe, expect, it, vi } from "vitest";

import { invoke } from "@tauri-apps/api/core";
import { bridgeRequest } from "./bridge.js";

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
});
