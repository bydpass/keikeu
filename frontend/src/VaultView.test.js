import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import VaultView from "./VaultView.vue";
import { bridgeRequest, chooseVaultDirectory } from "./bridge.js";

vi.mock("./bridge.js", () => ({
  bridgeRequest: vi.fn(),
  chooseVaultDirectory: vi.fn(),
}));

const runtime = {
  state: "ready",
  app_version: "0.1.0",
  core_version: "paper-v4/index-v4",
};
const previewHandle = ["preview", "handle"].join("-");
const migrationHandle = ["migration", "handle"].join("-");

const pickerStartup = {
  state: "vault_picker",
  show_daily_card: false,
  message: "",
  configured_path: "",
  migration: null,
  preview: null,
  vault_locator: null,
  index_state: "not_checked",
};

const readyStartup = {
  state: "ready",
  show_daily_card: true,
  message: "",
  configured_path: "",
  migration: null,
  preview: null,
  vault_locator: "vault-v1:test",
  index_state: "current",
};

function preview(overrides = {}) {
  return {
    token: previewHandle,
    kind: "paper",
    display_path: "/Users/creator/Vault",
    paper_count: 3,
    source_kind: "paper",
    message: "",
    migration: null,
    candidate_locator: "vault-v1:candidate",
    ...overrides,
  };
}

function preflight(overrides = {}) {
  return {
    token: migrationHandle,
    kind: "paper_to_v4",
    ready: true,
    vault_locator: "vault-v1:candidate",
    backup_path: "/Users/creator/keikeu-backups",
    cache_count: 2,
    trash_cache_count: 1,
    outline_count: 1,
    trash_outline_count: 0,
    issues: [],
    ...overrides,
  };
}

describe("Road v0.6 Vault and migration gate", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("inspects a typed path before confirming a Vault switch", async () => {
    bridgeRequest.mockImplementation(async (method) => {
      if (method === "vault.inspect") return preview();
      if (method === "vault.open") return readyStartup;
      throw new Error(`Unexpected method: ${method}`);
    });
    const wrapper = mount(VaultView, {
      props: { runtime, initialStartup: pickerStartup },
    });

    await wrapper.get('input[type="text"]').setValue("/Users/creator/Vault");
    await wrapper.get(".vault-actions .primary").trigger("click");
    await flushPromises();
    expect(bridgeRequest).toHaveBeenCalledWith("vault.inspect", {
      path: "/Users/creator/Vault",
    });
    expect(wrapper.text()).toContain("3 个活动 Paper");

    await wrapper.get(".vault-preview .primary").trigger("click");
    await flushPromises();
    expect(bridgeRequest).toHaveBeenCalledWith(
      "vault.open",
      { preview_token: previewHandle },
      expect.objectContaining({
        family: "vault",
        recovery_path: "/Users/creator/Vault",
      }),
    );
    expect(wrapper.emitted("ready")[0]).toEqual([readyStartup]);
    wrapper.unmount();
  });

  it("uses the registered directory picker and inspects its result", async () => {
    chooseVaultDirectory.mockResolvedValue("/Users/creator/Chosen");
    bridgeRequest.mockResolvedValue(
      preview({ display_path: "/Users/creator/Chosen" }),
    );
    const wrapper = mount(VaultView, {
      props: { runtime, initialStartup: pickerStartup },
    });

    await wrapper.get(".vault-actions button").trigger("click");
    await flushPromises();

    expect(chooseVaultDirectory).toHaveBeenCalledOnce();
    expect(bridgeRequest).toHaveBeenCalledWith("vault.inspect", {
      path: "/Users/creator/Chosen",
    });
    expect(wrapper.text()).toContain("/Users/creator/Chosen");
    wrapper.unmount();
  });

  it("requires the relocation acknowledgement and sends the opaque token", async () => {
    bridgeRequest.mockImplementation(async (method) => {
      if (method === "vault.inspect") {
        return preview({
          kind: "relocate",
          source_kind: "paper",
          message: "outside Home",
        });
      }
      if (method === "vault.relocate") return readyStartup;
      throw new Error(`Unexpected method: ${method}`);
    });
    const wrapper = mount(VaultView, {
      props: { runtime, initialStartup: pickerStartup },
    });
    await wrapper.get('input[type="text"]').setValue("/Volumes/Unsafe");
    await wrapper.get(".vault-actions .primary").trigger("click");
    await flushPromises();

    const destination = wrapper.get(".vault-preview input[type='text']");
    const confirmation = wrapper.get(".vault-check input");
    const relocate = wrapper.get(".vault-preview .primary");
    expect(relocate.attributes("disabled")).toBeDefined();

    await destination.setValue("/Users/creator/SafeCopy");
    await confirmation.setValue(true);
    await relocate.trigger("click");
    await flushPromises();

    expect(bridgeRequest).toHaveBeenCalledWith(
      "vault.relocate",
      {
        preview_token: previewHandle,
        destination_path: "/Users/creator/SafeCopy",
      },
      expect.objectContaining({
        family: "vault",
        recovery_path: "/Users/creator/SafeCopy",
      }),
    );
    wrapper.unmount();
  });

  it("runs migration once after confirmation and opens the migrated Vault", async () => {
    const migration = preflight();
    bridgeRequest.mockImplementation(async (method) => {
      if (method === "migration.run") {
        return {
          kind: "paper_to_v4",
          converted_count: 2,
          backup_path: "/Users/creator/backups/Vault-v01",
          report_path: "/Users/creator/Vault/keikeu_migration_report.json",
          paper_paths: ["cache/K-001.md", "cache/K-002.md"],
          warnings: [],
        };
      }
      if (method === "startup.load") return readyStartup;
      throw new Error(`Unexpected method: ${method}`);
    });
    const wrapper = mount(VaultView, {
      props: {
        runtime,
        initialStartup: {
          ...pickerStartup,
          state: "migration",
          migration,
        },
      },
    });
    await flushPromises();

    const run = wrapper.get(".migration-summary .danger");
    expect(run.attributes("disabled")).toBeDefined();
    await wrapper.get(".migration-summary input[type='checkbox']").setValue(true);
    await run.trigger("click");
    await flushPromises();

    expect(bridgeRequest).toHaveBeenCalledWith(
      "migration.run",
      { preflight_token: migrationHandle },
      expect.objectContaining({ family: "migration", vault_locator: "vault-v1:candidate" }),
    );
    expect(wrapper.text()).toContain("已转换 2 个 Paper");

    await wrapper.get(".migration-result .primary").trigger("click");
    await flushPromises();
    expect(bridgeRequest).toHaveBeenCalledWith("startup.load", {});
    expect(wrapper.emitted("ready")[0]).toEqual([readyStartup]);
    wrapper.unmount();
  });

  it("blocks on an unknown mutation commit and never retries it", async () => {
    bridgeRequest.mockImplementation(async (method) => {
      if (method === "vault.inspect") {
        return preview({
          kind: "create",
          display_path: "/Users/creator/New",
          paper_count: 0,
          source_kind: "",
        });
      }
      if (method === "vault.initialize") {
        throw {
          code: "commit_unknown",
          layer: "tauri_host",
          message: "response lost",
          recovery: "restart_then_reload",
        };
      }
      throw new Error(`Unexpected method: ${method}`);
    });
    const wrapper = mount(VaultView, {
      props: { runtime, initialStartup: pickerStartup },
    });
    await wrapper.get('input[type="text"]').setValue("/Users/creator/New");
    await wrapper.get(".vault-actions .primary").trigger("click");
    await flushPromises();
    await wrapper.get(".vault-preview .primary").trigger("click");
    await flushPromises();

    expect(
      bridgeRequest.mock.calls.filter(([method]) => method === "vault.initialize"),
    ).toHaveLength(1);
    expect(
      bridgeRequest.mock.calls.find(([method]) => method === "vault.initialize")[2],
    ).toMatchObject({
      family: "vault",
      recovery_path: "/Users/creator/New",
    });
    expect(wrapper.emitted("runtime-blocked")[0][0]).toMatchObject({
      code: "commit_unknown",
      layer: "tauri_host",
    });
    wrapper.unmount();
  });

  it("re-reads startup and settles an unknown Vault mutation after restart", async () => {
    const request = vi.fn(async (method) => {
      if (method === "startup.load") return readyStartup;
      if (method === "vault.inspect") {
        return preview({ candidate_locator: readyStartup.vault_locator });
      }
      throw new Error(method);
    });
    const wrapper = mount(VaultView, {
      props: {
        runtime,
        request,
        pendingIntent: {
          family: "vault",
          method: "vault.open",
          recovery_path: "/Users/creator/Vault",
        },
      },
    });
    await flushPromises();

    expect(request).toHaveBeenCalledWith("startup.load", {});
    expect(request).toHaveBeenCalledWith("vault.inspect", {
      path: "/Users/creator/Vault",
    });
    expect(wrapper.emitted("intent-settled")).toHaveLength(1);
    expect(wrapper.emitted("ready")[0]).toEqual([readyStartup]);
    wrapper.unmount();
  });

  it("re-reads migration state after restart without replaying migration", async () => {
    const migration = preflight({ token: "fresh-migration-token" });
    const request = vi.fn(async (method) => {
      if (method === "startup.load") {
        return { ...pickerStartup, state: "migration", migration };
      }
      throw new Error(method);
    });
    const wrapper = mount(VaultView, {
      props: {
        runtime,
        request,
        pendingIntent: { family: "migration", method: "migration.run" },
      },
    });
    await flushPromises();

    expect(request).toHaveBeenCalledWith("startup.load", {});
    expect(request.mock.calls.some(([method]) => method === "migration.run")).toBe(false);
    expect(wrapper.emitted("intent-settled")).toHaveLength(1);
    expect(wrapper.text()).toContain("迁移旧 Vault");
    expect(wrapper.get(".migration-summary .danger").attributes("disabled")).toBeDefined();
    wrapper.unmount();
  });

  it("shows an ambiguous unknown Vault target without replaying the mutation", async () => {
    const request = vi.fn(async (method) => {
      if (method === "startup.load") return pickerStartup;
      if (method === "vault.inspect") {
        return preview({
          kind: "paper",
          display_path: "/Users/creator/New",
          candidate_locator: "vault-v1:new",
        });
      }
      throw new Error(method);
    });
    const wrapper = mount(VaultView, {
      props: {
        runtime,
        request,
        pendingIntent: {
          family: "vault",
          method: "vault.initialize",
          recovery_path: "/Users/creator/New",
        },
      },
    });
    await flushPromises();

    expect(wrapper.text()).toContain("上次操作没有重放");
    expect(wrapper.text()).toContain("检测到可用 Paper Vault");
    expect(request.mock.calls.some(([method]) => method === "vault.initialize")).toBe(false);
    expect(wrapper.emitted("intent-settled")).toHaveLength(1);
    wrapper.unmount();
  });
});
