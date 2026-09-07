import { mount, flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import CoreWorkspace from "./CoreWorkspace.vue";
import PaperV4Workbench from "./PaperV4Workbench.vue";
import { bridgeRequest, confirmAction } from "./bridge.js";
vi.mock("./bridge.js", () => ({ bridgeRequest: vi.fn(), confirmAction: vi.fn() }));
const paper = {code:"K-20260907-001",path:null,target_path:"cache/K-20260907-001.md",edit_token:"edit",vault_locator:"storage",source_digest:null,
  created:"2026-09-07T01:00:00",updated:"2026-09-07T01:00:00",display_name:null,tags:[],pages:[{name:null,content:"",type:null}]};
let wrapper, records, calls, failPut, deferredSave;
beforeEach(() => {
  vi.useFakeTimers(); records = new Map(); calls = []; failPut = false; deferredSave = null;
  confirmAction.mockResolvedValue(true);
  bridgeRequest.mockImplementation(async (method,p) => {
    calls.push([method,p]);
    if (method === "host.locale.get") return {locale:"en"};
    if (method === "host.locale.set") return {locale:p.locale};
    if (method === "library.query") return {entries:[],errors:[]};
    if (method === "host.draft.list") return {drafts:[...records.entries()].map(([token,d]) => ({token,revision:d.revision,code:paper.code}))};
    if (method === "paper.create_draft") return structuredClone(paper);
    if (method === "host.draft.put") {
      if (failPut) throw {code:"recovery_unavailable"};
      records.set(p.draft_id,structuredClone(p)); return {token:p.draft_id,revision:p.revision};
    }
    if (method === "host.draft.discard") {
      if (records.get(p.token)?.revision !== p.revision) throw {code:"stale_revision"};
      records.delete(p.token); return {state:"removed"};
    }
    if (method === "host.export") return {state:"cancelled"};
    if (method === "paper.save") {
      if (!records.has(p.draft_id)) throw {code:"validation_failed"};
      if (deferredSave) await deferredSave;
      return {paper:{...paper,path:paper.target_path,edit_token:"saved",display_name:p.display_name,tags:p.tags,pages:p.pages},warnings:[]};
    }
    if (method === "host.draft.read") { const d=records.get(p.token);return {...d,token:p.token,paper,baseline:null,state:"ready"}; }
    throw new Error(method);
  });
});
afterEach(() => { wrapper?.unmount(); vi.useRealTimers(); });
async function start() {
  wrapper = mount(CoreWorkspace,{props:{capabilities:{backend:"rust",storage_id:"storage",generation:1}}});
  await flushPromises();
  await wrapper.findAll("button").find(b=>b.text()==="New Paper").trigger("click"); await flushPromises();
}
async function input(text) { await wrapper.get("textarea").setValue(text); }
it("protects raw invalid input after 500ms and restores it without parsing",async () => {
  await start(); await input("保存原文"); await wrapper.get(".paper-tags-input").setValue('"unclosed');
  await vi.advanceTimersByTimeAsync(499); expect(records.size).toBe(0);
  await vi.advanceTimersByTimeAsync(1); await flushPromises();
  const [token,d] = [...records.entries()][0]; expect(d.raw.tags_text).toBe('"unclosed');
  expect(d.raw.pages[0].content).toBe("保存原文");
  wrapper.unmount(); wrapper=mount(CoreWorkspace,{props:{capabilities:{backend:"rust",storage_id:"storage",generation:1}}});await flushPromises();
  await wrapper.findAll("button").find(b=>b.text().includes(paper.code)).trigger("click");await flushPromises();
  expect(wrapper.get(".paper-tags-input").element.value).toBe('"unclosed');
  expect(wrapper.get("textarea").element.value).toBe("保存原文");
  expect(records.has(token)).toBe(true);
});
it("blocks a formal save when recovery persistence fails",async () => {
  await start(); await input("keep me"); failPut=true;
  await wrapper.get(".save-action").trigger("click");await flushPromises();
  expect(calls.some(([m])=>m==="paper.save")).toBe(false);
  expect(wrapper.get("textarea").element.value).toBe("keep me");
  expect(wrapper.text()).toContain("recovery_unavailable");
  await wrapper.findAll("button").find(b=>b.text()==="Export draft").trigger("click");await flushPromises();
  const exported=calls.find(([m,p])=>m==="host.export" && p.source==="raw");
  expect(exported[1].raw.pages[0].content).toBe("keep me");
  expect(wrapper.get("textarea").element.value).toBe("keep me");
});
it("retains input entered while a save is in flight and does not clear its revision",async () => {
  await start();await input("submitted");let resolve;
  deferredSave=new Promise(r=>{resolve=r;});
  await wrapper.get(".save-action").trigger("click");await flushPromises();
  expect(calls.some(([m])=>m==="paper.save")).toBe(true);
  await input("newer input");await vi.advanceTimersByTimeAsync(500);await flushPromises();
  resolve();await flushPromises();
  expect(wrapper.get("textarea").element.value).toBe("newer input");
  expect([...records.values()][0].raw.pages[0].content).toBe("newer input");
  expect(calls.some(([m])=>m==="host.draft.discard")).toBe(false);
});
it("export cancellation retains the draft and all host calls carry scope",async () => {
  await start();await input("keep on cancel");
  await wrapper.findAll("button").find(b=>b.text()==="Export draft").trigger("click");await flushPromises();
  expect(records.size).toBe(1);expect(wrapper.text()).toContain("Export cancelled");
  for (const [,p] of calls) {expect(p.storage_id).toBe("storage");expect(p.generation).toBe(1);}
});
it("shows English validation and leaves author text unchanged",async () => {
  await start();await input("作者正文");await wrapper.get(".paper-tags-input").setValue('"unfinished');
  expect(wrapper.text()).toContain("A tag quote is not closed.");
  expect(wrapper.getComponent(PaperV4Workbench).props("locale")).toBe("en");
  expect(wrapper.get("textarea").element.value).toBe("作者正文");
});

it("flushes on pagehide before the idle timer elapses",async () => {
  await start();await input("background draft");window.dispatchEvent(new Event("pagehide"));await flushPromises();
  expect([...records.values()][0].raw.pages[0].content).toBe("background draft");
});
it("keeps local drafts and preserved conflict exports visible while the cloud provider is unavailable", async () => {
  const original = bridgeRequest.getMockImplementation();
  records.set("offline-draft", {revision:1});
  bridgeRequest.mockImplementation(async (method,p) => {
    if (method === "library.query" || method === "host.cloud.status") throw {code:"icloud_account_unavailable"};
    if (method === "host.conflict.list") return {copies:[{token:"copy",path:"cache/other.md",digest:"0123456789abcdef",valid:false}]};
    if (method === "host.conflict.export") return {state:"cancelled"};
    return original(method,p);
  });
  wrapper=mount(CoreWorkspace,{props:{capabilities:{backend:"rust",storage_kind:"icloud",storage_id:"storage",generation:1}}});
  await flushPromises();
  expect(wrapper.text()).toContain(paper.code);
  expect(wrapper.text()).toContain("cache/other.md");
  expect(wrapper.text()).toContain("icloud_account_unavailable");
  await wrapper.findAll("button").find(b=>b.text()==="Export original bytes").trigger("click");
  await flushPromises();
  expect(bridgeRequest).toHaveBeenCalledWith("host.conflict.export", {token:"copy",storage_id:"storage",generation:1});
  expect(records.has("offline-draft")).toBe(true);
});

it("protects unchanged and edited snapshots before saving again", async () => {
  const host = bridgeRequest.getMockImplementation();
  const rustJson = (value) => Array.isArray(value) ? value.map(rustJson)
    : value && typeof value === "object" ? Object.fromEntries(Object.keys(value).sort().map(key => [key, rustJson(value[key])])) : value;
  bridgeRequest.mockImplementation(async (method, params) => rustJson(await host(method, params)));
  await start(); await input("first save");
  await wrapper.get(".save-action").trigger("click"); await flushPromises();
  await wrapper.get(".save-action").trigger("click"); await flushPromises();
  expect(wrapper.text()).not.toContain("validation_failed");
  await input("edited after saving");
  await vi.advanceTimersByTimeAsync(500); await flushPromises();
  expect([...records.values()][0]?.raw.pages[0].content).toBe("edited after saving");
  const original = bridgeRequest.getMockImplementation();
  bridgeRequest.mockImplementation(async (method, p) => {
    if (method === "paper.save") {
      expect(records.get(p.draft_id)?.revision).toBe(p.revision);
      expect(records.get(p.draft_id)?.raw.pages[0].content).toBe("edited after saving");
    }
    return original(method, p);
  });
  await wrapper.get(".save-action").trigger("click"); await flushPromises();
  expect(calls.filter(([method]) => method === "paper.save")).toHaveLength(3);
  failPut = true;
  await wrapper.get(".save-action").trigger("click"); await flushPromises();
  expect(wrapper.text()).toContain("recovery_unavailable");
  expect(wrapper.text()).not.toContain("Saved");
  expect(wrapper.get("textarea").element.value).toBe("edited after saving");
});

it("blocks departure during a download request and ignores its completion after unmount", async () => {
  const original = bridgeRequest.getMockImplementation();
  let completeDownload;
  bridgeRequest.mockImplementation((method, params) => {
    if (method === "host.cloud.status") return Promise.resolve({items:[{path:"cache/pending.md",token:"pending",state:"not_downloaded"}]});
    if (method === "host.conflict.list") return Promise.resolve({copies:[],pending:null});
    if (method === "host.cloud.download") return new Promise(resolve => { completeDownload = resolve; });
    return original(method, params);
  });
  wrapper = mount(CoreWorkspace, {props:{capabilities:{backend:"rust",storage_kind:"icloud",storage_id:"cloud",generation:1}}});
  await flushPromises();
  await wrapper.findAll("button").find(button => button.text() === "Download").trigger("click");
  await flushPromises();
  expect(completeDownload).toBeTypeOf("function");
  await expect(wrapper.vm.confirmDeparture()).resolves.toBe(false);
  expect(confirmAction).not.toHaveBeenCalled();
  wrapper.unmount();
  await start();
  await input("new local input");
  const callsBeforeCompletion = bridgeRequest.mock.calls.length;
  completeDownload({state:"requested"});
  await flushPromises();
  expect(bridgeRequest.mock.calls).toHaveLength(callsBeforeCompletion);
  expect(wrapper.get("textarea").element.value).toBe("new local input");
  expect(wrapper.text()).not.toContain("Download requested");
});
