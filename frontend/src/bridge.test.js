import { beforeEach, describe, expect, it, vi } from "vitest";

import { invoke, isTauri } from "@tauri-apps/api/core";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { confirm } from "@tauri-apps/plugin-dialog";
import {
  bridgeRequest,
  chooseVaultDirectory,
  confirmDiscardChanges,
  openSystemTarget,
  registerWindowCloseGuard,
} from "./bridge.js";

vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(),
  isTauri: vi.fn(),
}));

vi.mock("@tauri-apps/api/window", () => ({
  getCurrentWindow: vi.fn(),
}));

vi.mock("@tauri-apps/plugin-dialog", () => ({
  confirm: vi.fn(),
}));

describe("Tauri bridge envelope", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    isTauri.mockReturnValue(false);
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

  it("opens only the registered native Vault directory picker", async () => {
    invoke.mockResolvedValue("/Users/creator/Vault");

    await expect(chooseVaultDirectory()).resolves.toBe("/Users/creator/Vault");
    expect(invoke).toHaveBeenCalledWith("choose_vault_directory");
  });

  it("uses browser confirm only outside Tauri", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);

    await expect(confirmDiscardChanges()).resolves.toBe(true);

    expect(window.confirm).toHaveBeenCalledWith(
      "当前有未保存的更改。要放弃更改并继续吗？",
    );
    expect(confirm).not.toHaveBeenCalled();
  });

  it("uses the native two-option dialog with the required labels in Tauri", async () => {
    isTauri.mockReturnValue(true);
    confirm.mockResolvedValue(false);

    await expect(confirmDiscardChanges()).resolves.toBe(false);

    expect(confirm).toHaveBeenCalledWith(
      "当前有未保存的更改。要放弃更改并继续吗？",
      {
        title: "keikeu",
        kind: "warning",
        okLabel: "放弃更改",
        cancelLabel: "继续编辑",
      },
    );
  });

  it("prevents close until the shared guard allows a forced destroy", async () => {
    isTauri.mockReturnValue(true);
    const destroy = vi.fn().mockResolvedValue(undefined);
    let closeHandler;
    const unlisten = vi.fn();
    getCurrentWindow.mockReturnValue({
      destroy,
      onCloseRequested: vi.fn(async (handler) => {
        closeHandler = handler;
        return unlisten;
      }),
    });
    const requestDeparture = vi.fn()
      .mockResolvedValueOnce(false)
      .mockResolvedValueOnce(true);

    await expect(registerWindowCloseGuard(requestDeparture)).resolves.toBe(unlisten);
    const firstEvent = { preventDefault: vi.fn() };
    await closeHandler(firstEvent);
    expect(firstEvent.preventDefault).toHaveBeenCalledOnce();
    expect(destroy).not.toHaveBeenCalled();

    const secondEvent = { preventDefault: vi.fn() };
    await closeHandler(secondEvent);
    expect(secondEvent.preventDefault).toHaveBeenCalledOnce();
    expect(destroy).toHaveBeenCalledOnce();
  });
});
