<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from "vue";
import { bridgeRequest, confirmAction } from "./bridge.js";
import PaperV4Workbench from "./PaperV4Workbench.vue";

const props = defineProps({ capabilities: { type: Object, required: true } });
const locale = ref("en");
const t = (zh, en) => locale.value === "en" ? en : zh;
const paper = ref(null), rawDraft = ref(null), baseline = ref(undefined);
const repair = ref(null);
const state = ref("ready"), error = ref(""), notice = ref("");
const drafts = ref([]), entries = ref([]), fileErrors = ref([]), query = ref("");
const busy = ref(false), dirty = ref(false), protectedRevision = ref(0), revision = ref(0);
const editorKey = ref(0), draftId = ref(null);
let raw = null, timer, queue = Promise.resolve(), disposed = false, primed = false;
const protection = computed(() => revision.value > 0 && protectedRevision.value === revision.value);
const copy = (value) => JSON.parse(JSON.stringify(value));
const editable = (p) => ({ display_name: p.display_name, tags: p.tags, pages: p.pages });
function report(e) { error.value = `${t("操作未完成；草稿保留。", "Operation incomplete; draft retained.")} ${e?.code ?? "operation_failed"}`; }
async function request(method, params = {}) {
  const cap = props.capabilities;
  const result = await bridgeRequest(method, { ...params, storage_id: cap.storage_id, generation: cap.generation });
  if (disposed || props.capabilities.generation !== cap.generation || props.capabilities.storage_id !== cap.storage_id) {
    throw { code: "stale_session" };
  }
  return result;
}
async function refresh() {
  const [list, recovery] = await Promise.all([
    request("library.query", { query: query.value, scope: "active" }), request("host.draft.list"),
  ]);
  entries.value = list.entries; fileErrors.value = list.errors; drafts.value = recovery.drafts;
}
function acceptRaw(value) {
  const next = { code: value.code, display_name: value.display_name, tags_text: value.tags_text,
    pages: value.pages.map(({ name, content, type }) => ({ name, content, type })) };
  if (!primed) { primed = true; raw = copy(next); return; }
  if (JSON.stringify(raw) === JSON.stringify(next)) return;
  raw = copy(next); revision.value += 1;
  clearTimeout(timer); timer = setTimeout(() => flush().catch(report), 500);
}
function flush(settle = false) {
  clearTimeout(timer);
  if (!paper.value || !raw || revision.value === 0) return queue;
  const snapshot = { draft_id: draftId.value, revision: revision.value, raw: copy(raw), edit_token: paper.value.edit_token, settle };
  queue = queue.catch(() => {}).then(async () => {
    const result = await request("host.draft.put", snapshot);
    if (draftId.value === snapshot.draft_id && result.revision === snapshot.revision) {
      protectedRevision.value = Math.max(protectedRevision.value, result.revision);
    }
  });
  return queue;
}
async function confirmDeparture() {
  if (busy.value || state.value === "commit_unknown") return false;
  try { await flush(); } catch (e) { report(e); return false; }
  if (!dirty.value && revision.value === 0) return true;
  const identity = draftId.value;
  const allowed = await confirmAction(t("保留本机恢复草稿并离开？", "Keep the local recovery draft and leave?"), {
    okLabel: t("保留并离开", "Keep and leave"), cancelLabel: t("继续编辑", "Keep editing"),
  });
  if (!allowed || busy.value || draftId.value !== identity || state.value === "commit_unknown") return false;
  try { await flush(); return !busy.value && draftId.value === identity; }
  catch (e) { report(e); return false; }
}
defineExpose({ confirmDeparture });
function load(p, recovery = null) {
  repair.value = null;
  paper.value = p; rawDraft.value = recovery?.raw ?? null;
  baseline.value = recovery ? recovery.baseline ?? null : p.path ? editable(p) : null;
  state.value = recovery?.state ?? "ready";
  draftId.value = recovery?.token ?? crypto.randomUUID();
  revision.value = recovery?.revision ?? 0; protectedRevision.value = revision.value;
  raw = null; primed = false; editorKey.value += 1; notice.value = "";
}
async function act(operation) {
  if (busy.value) return;
  error.value = ""; busy.value = true;
  try { await operation(); } catch (e) { report(e); } finally { busy.value = false; }
}
async function create() {
  if (!(await confirmDeparture())) return;
  await act(async () => { load(await request("paper.create_draft")); await refresh(); });
}
async function open(path) {
  if (!(await confirmDeparture())) return;
  await act(async () => {
    const result = await request("paper.open", { path });
    if (result.state !== "opened") {
      repair.value = result.repair; paper.value = null; raw = null; revision.value = 0; dirty.value = false;
      return;
    }
    load(result.paper);
  });
}
async function recover(token) {
  if (!(await confirmDeparture())) return;
  await act(async () => {
    const result = await request("host.draft.read", { token });
    load(result.paper, result);
  });
}
async function discard(item) {
  if (busy.value || !await confirmAction(t("永久丢弃这一份本机恢复草稿？正式文件保持原样。", "Discard this local recovery draft? The saved file remains unchanged."),
    { okLabel: t("丢弃草稿", "Discard draft"), cancelLabel: t("取消", "Cancel") })) return;
  await act(async () => {
    // Flush current input first; never delete a stale revision displayed in the recovery list.
    if (draftId.value === item.token) await flush();
    await request("host.draft.discard", { token: item.token, revision: item.revision });
    if (draftId.value === item.token) { paper.value = null; raw = null; revision.value = 0; dirty.value = false; }
    await refresh();
  });
}
async function save(value) {
  await act(async () => {
    if (!revision.value) revision.value = 1;
    const submittedRevision = revision.value, submittedRaw = copy(raw), source = paper.value;
    await flush();
    try {
      const result = await request("paper.save", { ...value, edit_token: source.edit_token, vault_locator: source.vault_locator,
        draft_id: draftId.value, revision: submittedRevision });
      const newer = revision.value > submittedRevision;
      rawDraft.value = newer ? copy(raw) : null;
      baseline.value = editable(result.paper); paper.value = result.paper;
      primed = false; editorKey.value += 1;
      if (newer) {
        await flush();
      } else {
        await request("host.draft.discard", { token: draftId.value, revision: submittedRevision });
        revision.value = 0; protectedRevision.value = 0; raw = null;
      }
      state.value = "ready"; notice.value = t("已保存", "Saved"); await refresh();
    } catch (e) {
      state.value = e?.code === "commit_unknown" ? "commit_unknown" : e?.code === "stale_snapshot" ? "stale" : state.value;
      if (!raw) raw = submittedRaw;
      throw e;
    }
  });
}
async function reconcile() {
  await act(async () => {
    const result = await request("paper.reconcile_save", { draft_id: draftId.value });
    if (!["committed", "not_committed"].includes(result.state)) { state.value = "stale"; return; }
    rawDraft.value = copy(raw); baseline.value = result.paper.path ? editable(result.paper) : null;
    paper.value = result.paper; state.value = "ready"; primed = false; editorKey.value += 1;
    // A new protected revision acknowledges the read-only result; it never resends a save.
    revision.value += 1; await flush(true); await refresh();
    notice.value = result.state === "committed" ? t("已核对：保存已完成。", "Verified: the save completed.") : t("已核对：保存未提交，可手动保存。", "Verified: not committed. You may save manually.");
  });
}
async function exportCopy(source = "draft", token = null) {
  await act(async () => {
    if (!token && source === "draft") {
      if (!revision.value) revision.value = 1;
      try { await flush(); token = draftId.value; }
      catch {
        const result = await request("host.export", { source: "raw", raw: copy(raw) });
        notice.value = result.state === "exported" ? t("副本已交给系统", "Copy handed to the system") : t("已取消导出", "Export cancelled");
        return;
      }
    }
    const result = await request("host.export", { source, token: token ?? paper.value.edit_token });
    notice.value = result.state === "exported" ? t("副本已交给系统", "Copy handed to the system") : t("已取消导出", "Export cancelled");
  });
}
async function setLocale(event) {
  const selected = event.target.value;
  await act(async () => { locale.value = (await request("host.locale.set", { locale: selected })).locale; });
  event.target.value = locale.value;
}
function background(event) { if (event.type === "pagehide" || document.visibilityState === "hidden") flush().catch(report); }
onMounted(async () => {
  document.addEventListener("visibilitychange", background); window.addEventListener("pagehide", background);
  await act(async () => { locale.value = (await request("host.locale.get")).locale; await refresh(); });
});
onBeforeUnmount(() => { disposed = true; clearTimeout(timer); document.removeEventListener("visibilitychange", background); window.removeEventListener("pagehide", background); });
</script>

<template>
  <main class="core-workspace" :lang="locale">
    <header class="core-toolbar">
      <strong>keikeu</strong>
      <button :disabled="busy || state === 'commit_unknown'" @click="create">{{ t('新 Paper', 'New Paper') }}</button>
      <label><span class="sr-only">{{ t('语言', 'Language') }}</span><select :value="locale" :disabled="busy" @change="setLocale"><option value="zh-CN">中文</option><option value="en">English</option></select></label>
    </header>
    <p v-if="error" role="alert">{{ error }}</p>
    <p v-if="notice" role="status">{{ notice }}</p>
    <section v-if="drafts.length" class="core-recovery" :aria-label="t('本机恢复草稿', 'Local recovery drafts')">
      <h2>{{ t('本机恢复草稿', 'Local recovery drafts') }}</h2>
      <div v-for="item in drafts" :key="item.token">
        <button :disabled="busy" @click="recover(item.token)">{{ item.code }} · {{ item.revision }}</button>
        <button :disabled="busy" @click="exportCopy('draft', item.token)">{{ t('导出', 'Export') }}</button>
        <button :disabled="busy" @click="discard(item)">{{ t('丢弃', 'Discard') }}</button>
      </div>
    </section>
    <section v-if="repair" role="alert">
      <p>{{ repair.path }} · {{ t('文件需要人工修复，原字节保留。', 'This file needs manual repair; its original bytes are retained.') }}</p>
      <button :disabled="busy" @click="exportCopy('paper', repair.export_token)">{{ t('导出原文件', 'Export original file') }}</button>
    </section>
    <section v-if="paper">
      <div class="core-toolbar">
        <span role="status">{{ protection ? t('本机草稿已保护', 'Local draft protected') : revision ? t('草稿尚未保护', 'Draft not yet protected') : t('本机 Paper', 'Local Paper') }}</span>
        <button :disabled="busy" @click="exportCopy()">{{ t('导出草稿', 'Export draft') }}</button>
        <button v-if="paper.path" :disabled="busy" @click="exportCopy('paper')">{{ t('导出已保存 Paper', 'Export saved Paper') }}</button>
        <button v-if="state === 'commit_unknown'" :disabled="busy" @click="reconcile">{{ t('只读核对保存', 'Check save result') }}</button>
      </div>
      <PaperV4Workbench :key="editorKey" :paper="paper" :raw-draft="rawDraft" :baseline-editable="baseline" :locale="locale"
        :state="state" :saving="busy" :allow-input-during-save="true" @dirty-change="dirty = $event" @raw-change="acceptRaw" @save="save" />
    </section>
    <section class="core-library">
      <h2>Library</h2>
      <form @submit.prevent="act(refresh)"><label>{{ t('搜索全部页面', 'Search all pages') }}<input v-model="query" type="search"></label><button :disabled="busy">{{ t('搜索', 'Search') }}</button></form>
      <ul><li v-for="entry in entries" :key="entry.path"><button :disabled="busy" @click="open(entry.path)">{{ entry.display_name || entry.code }}</button><p>{{ entry.preview }}</p></li></ul>
      <p v-for="item in fileErrors" :key="item.path" role="alert"><button :disabled="busy" @click="open(item.path)">{{ item.path }}</button> · {{ t('需要修复', 'Needs repair') }} ({{ item.reason }})</p>
    </section>
  </main>
</template>
<style scoped>
.core-workspace { max-width: 960px; margin: auto; padding: max(12px, env(safe-area-inset-top)) max(12px, env(safe-area-inset-right)) max(24px, env(safe-area-inset-bottom)) max(12px, env(safe-area-inset-left)); }
.core-toolbar { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; margin-bottom: 16px; }
.core-toolbar strong { margin-right: auto; }
button, input, select { font: inherit; min-height: 44px; }
button { cursor: pointer; padding: 8px 12px; color: var(--ink); background: var(--paper); border: 1px solid var(--rule); border-radius: var(--radius-xs); }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
.core-library, .core-recovery { border-top: 1px solid var(--rule); margin-top: 24px; padding-top: 12px; }
.core-library ul { list-style: none; padding: 0; }
.core-library li { padding: 12px 0; border-bottom: 1px solid var(--rule); overflow-wrap: anywhere; }
.core-library p { white-space: pre-wrap; }
form { display: flex; gap: 8px; flex-wrap: wrap; }
form label { flex: 1; } input { display: block; width: 100%; box-sizing: border-box; }
[role=alert] { color: var(--danger, #9b3232); overflow-wrap: anywhere; }
</style>
