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
  core_version: "paper-v3/index-v3",
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
};

const readyStartup = {
  state: "ready",
  show_daily_card: true,
  message: "",
  configured_path: "",
  migration: null,
  preview: null,
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
    ...overrides,
  };
}

function preflight(overrides = {}) {
  return {
    token: migrationHandle,
    ready: true,
    backup_path: "/Users/creator/keikeu-backups",
    cache_count: 2,
    trash_cache_count: 1,
    outline_count: 1,
    trash_outline_count: 0,
    issues: [],
    ...overrides,
  };
}

describe("CP9 Vault and migration gate", () => {
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
    expect(bridgeRequest).toHaveBeenCalledWith("vault.open", {
      preview_token: previewHandle,
    });
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

    expect(bridgeRequest).toHaveBeenCalledWith("vault.relocate", {
      preview_token: previewHandle,
      destination_path: "/Users/creator/SafeCopy",
    });
    wrapper.unmount();
  });

  it("runs migration once after confirmation and opens the migrated Vault", async () => {
    const migration = preflight();
    bridgeRequest.mockImplementation(async (method) => {
      if (method === "migration.run") {
        return {
          converted_count: 2,
          backup_path: "/Users/creator/backups/Vault-v01",
          report_path: "/Users/creator/Vault/keikeu_migration_report.json",
          paper_paths: ["cache/K-001.md", "cache/K-002.md"],
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

    expect(bridgeRequest).toHaveBeenCalledWith("migration.run", {
      preflight_token: migrationHandle,
    });
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
        return preview({ kind: "create", paper_count: 0, source_kind: "" });
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
    expect(wrapper.emitted("runtime-blocked")[0][0]).toMatchObject({
      code: "commit_unknown",
      layer: "tauri_host",
    });
    wrapper.unmount();
  });
});
