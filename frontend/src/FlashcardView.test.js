import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import FlashcardView from "./FlashcardView.vue";
import { bridgeRequest } from "./bridge.js";

vi.mock("./bridge.js", () => ({
  bridgeRequest: vi.fn(),
}));

const runtime = {
  state: "ready",
  app_version: "0.1.0",
  core_version: "paper-v3/index-v3",
};

const firstDeck = {
  path: "cache/K-20260725-001.md",
  paper_label: "Night Train (K-20260725-001)",
  cards: [
    { title: "Summary", content: "Current Summary." },
    { title: "Window", content: "First writing anchor." },
    { title: "Platform", content: "Second writing anchor." },
  ],
  options: [
    {
      path: "cache/K-20260725-001.md",
      code: "K-20260725-001",
      display_name: "Night Train",
      label: "Night Train (K-20260725-001)",
    },
    {
      path: "cache/K-20260725-002.md",
      code: "K-20260725-002",
      display_name: "Blue Hour",
      label: "Blue Hour (K-20260725-002)",
    },
  ],
};

const secondDeck = {
  path: "cache/K-20260725-002.md",
  paper_label: "Blue Hour (K-20260725-002)",
  cards: [
    { title: "Summary", content: "Second Summary." },
    { title: "Signal", content: "Only anchor." },
  ],
  options: firstDeck.options,
};

describe("CP7 Flashcard slice", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    bridgeRequest.mockResolvedValue(firstDeck);
  });

  it("opens Summary first, shows context on Highlights, and returns to the Paper", async () => {
    const wrapper = mount(FlashcardView, {
      props: { runtime, initialPath: firstDeck.path },
    });
    await flushPromises();

    expect(bridgeRequest).toHaveBeenCalledWith("flashcard.open", {
      path: firstDeck.path,
    });
    expect(wrapper.text()).toContain("Current Summary.");
    expect(wrapper.text()).toContain("1 / 3");
    expect(wrapper.find(".summary-context").exists()).toBe(false);

    await wrapper.findAll(".flashcard-list button")[1].trigger("click");
    expect(wrapper.text()).toContain("First writing anchor.");
    await wrapper.get(".summary-tools > button").trigger("click");
    expect(wrapper.get(".summary-context").text()).toContain("Current Summary.");

    await wrapper.findAll(".flashcard-controls > button").at(-1).trigger("click");
    expect(wrapper.emitted("open-paper")[0]).toEqual([firstDeck.path]);
    wrapper.unmount();
  });

  it("keeps a long card list inside the fixed context rail", async () => {
    const longDeck = {
      ...firstDeck,
      cards: Array.from({ length: 36 }, (_, cardIndex) => ({
        title: cardIndex === 0 ? "Summary" : `Highlight ${cardIndex}`,
        content: `Card content ${cardIndex}`,
      })),
    };
    bridgeRequest.mockResolvedValue(longDeck);
    const wrapper = mount(FlashcardView, { props: { runtime } });
    await flushPromises();
    const context = wrapper.get(".flashcard-context");
    const buttons = wrapper.findAll(".flashcard-list button");

    expect(context.classes()).toContain("fixed-context-rail");
    expect(buttons).toHaveLength(36);

    await buttons.at(-1).trigger("click");

    expect(buttons.at(-1).attributes("aria-current")).toBe("page");
    expect(wrapper.text()).toContain("Card content 35");
    wrapper.unmount();
  });

  it("supports arrow keys and validated page jumps without leaving the deck", async () => {
    const wrapper = mount(FlashcardView, { props: { runtime } });
    await flushPromises();
    const controls = wrapper.findAll(".flashcard-controls > button");

    expect(controls[0].attributes("disabled")).toBeDefined();
    expect(controls[1].attributes("disabled")).toBeUndefined();

    const right = new KeyboardEvent("keydown", {
      key: "ArrowRight",
      cancelable: true,
    });
    window.dispatchEvent(right);
    await flushPromises();
    expect(right.defaultPrevented).toBe(true);
    expect(wrapper.text()).toContain("First writing anchor.");

    await wrapper.get("#flashcard-jump-page").setValue("3");
    await wrapper.get(".flashcard-controls form").trigger("submit");
    expect(wrapper.text()).toContain("Second writing anchor.");
    expect(wrapper.text()).toContain("3 / 3");
    expect(controls[0].attributes("disabled")).toBeUndefined();
    expect(controls[1].attributes("disabled")).toBeDefined();

    await wrapper.get("#flashcard-jump-page").setValue("0");
    await wrapper.get(".flashcard-controls form").trigger("submit");
    expect(wrapper.text()).toContain("页码范围是 1..3");
    expect(wrapper.text()).toContain("Second writing anchor.");
    wrapper.unmount();
  });

  it("resets to page 1 whenever the selected Paper changes", async () => {
    bridgeRequest.mockImplementation(async (_method, { path }) =>
      path === secondDeck.path ? secondDeck : firstDeck,
    );
    const wrapper = mount(FlashcardView, {
      props: { runtime, initialPath: firstDeck.path },
    });
    await flushPromises();

    await wrapper.findAll(".flashcard-list button")[2].trigger("click");
    expect(wrapper.text()).toContain("3 / 3");

    await wrapper.get(".flashcard-selector select").setValue(secondDeck.path);
    await flushPromises();

    expect(bridgeRequest).toHaveBeenLastCalledWith("flashcard.open", {
      path: secondDeck.path,
    });
    expect(wrapper.text()).toContain("Second Summary.");
    expect(wrapper.text()).toContain("1 / 2");
    wrapper.unmount();
  });

  it("keeps host failures at the blocking runtime layer", async () => {
    bridgeRequest.mockRejectedValue({
      code: "sidecar_unavailable",
      layer: "tauri_host",
      message: "Sidecar stopped",
      recovery: "restart_sidecar",
    });
    const wrapper = mount(FlashcardView, { props: { runtime } });
    await flushPromises();

    expect(wrapper.emitted("runtime-blocked")[0][0]).toMatchObject({
      code: "sidecar_unavailable",
      layer: "tauri_host",
    });
    wrapper.unmount();
  });

  it("opens Library without persisting the current card position", async () => {
    const wrapper = mount(FlashcardView, { props: { runtime } });
    await flushPromises();

    await wrapper.get('button[aria-label="打开 Library"]').trigger("click");
    expect(wrapper.emitted("open-library")).toHaveLength(1);
    wrapper.unmount();
  });
});
