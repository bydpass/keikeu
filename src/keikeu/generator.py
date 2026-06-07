import re

from .models import Memo, Ticket

_CP_PATTERN = re.compile(r"[A-Za-z一-鿿]+\s*[/×x&]\s*[A-Za-z一-鿿]+")
_AU_KEYWORDS = (
    "现paro", "现 paro", "古风", "ABO", "abo", "校园", "末世", "玄幻",
    "异能", "废土", "歌剧", "悬疑", "灵异", "破镜重圆", "穿越", "重生",
    "都市", "无限流",
)
_MOOD_KEYWORDS = (
    "HE", "BE", "be", "he", "虐", "甜", "暗恋", "双向", "暧昧", "be美学",
    "破镜", "追妻", "病娇", "救赎", "黑化",
)
_VINEGAR_TRIGGERS = ("想看", "一定", "必", "最想", "画面", "瞬间", "要", "！", "?", "？", "「", "『", "*")

_SENT_SPLIT = re.compile(r"[。！？!?\n]+")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENT_SPLIT.split(text) if p.strip()]
    return parts


def _extract_tags(raw: str) -> list[str]:
    tags: list[str] = ["同人"]

    for m in _CP_PATTERN.findall(raw):
        tags.append(_normalize(m))

    for kw in _AU_KEYWORDS:
        if kw in raw:
            tags.append(kw.strip().replace(" ", ""))

    for kw in _MOOD_KEYWORDS:
        if kw in raw:
            tags.append(kw)

    seen: set[str] = set()
    deduped: list[str] = []
    for t in tags:
        key = t.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(t)
    return deduped[:8]


def _extract_jiaozi_cu(raw: str) -> list[str]:
    sentences = _split_sentences(raw)
    picked: list[str] = []

    for s in sentences:
        if any(trigger in s for trigger in _VINEGAR_TRIGGERS):
            picked.append(s)

    if not picked and sentences:
        picked.append(sentences[0])
        if len(sentences) > 1:
            picked.append(sentences[-1])

    fallbacks = [
        "原文中保留的核心画面",
        "情绪最重的那个瞬间",
        "结尾的余韵，不该被冲淡",
    ]
    for fb in fallbacks:
        if len(picked) >= 3:
            break
        picked.append(fb)

    seen: set[str] = set()
    deduped: list[str] = []
    for v in picked:
        if v in seen:
            continue
        seen.add(v)
        deduped.append(v)
    return deduped[:5]


def _build_summary(raw: str, tags: list[str]) -> str:
    snippet = _normalize(raw)
    if len(snippet) > 80:
        snippet = snippet[:80].rstrip() + "…"
    anchor = next((t for t in tags if t != "同人"), "这对 CP")
    return f"围绕「{anchor}」展开的同人创作：{snippet}"


def _build_jiaozi(raw: str) -> list[str]:
    base = [
        "前因 — 让饺子醋成立的人物状态与关系铺垫",
        "中段 — 把情绪和处境推到饺子醋爆点",
        "收尾 — 守住饺子醋余味，不强行翻案",
    ]
    if len(raw) > 200:
        base.append("番外 — 一段可有可无的支线，用来补全氛围")
    return base


def _pick_product(raw: str) -> str:
    length = len(_normalize(raw))
    if length < 200:
        return "短打片段（适合一口气写完）"
    if length < 800:
        return "中篇短打（建议拆 2–3 段推进）"
    return "长篇 / 多段（建议提前写大纲）"


def _build_taboo() -> list[str]:
    return [
        "OOC（角色失真）",
        "突然降智或破坏角色逻辑",
        "为了反转而强行 HE / BE 翻盘",
        "削弱饺子醋的多余配角戏份",
    ]


def _build_next_step(tags: list[str]) -> list[str]:
    steps = [
        "从饺子醋反推，开写第一段",
        "压缩成约文 Brief 发给写手 / 画师",
        "导出灵感名片存档或分享",
    ]
    if any(t in _AU_KEYWORDS or t == "ABO" or t == "abo" for t in tags):
        steps.append("补足缺失的 AU / 世界观设定细节")
    return steps


def make_memo(raw: str) -> Memo:
    """灵光池：先接住灵感，不整理、不审问，保留原文。"""
    return Memo(raw=raw)


def make_ticket(raw_idea: str) -> Ticket:
    """配方票：把裸灵感整理成可执行的创作 brief。"""
    if not raw_idea or not raw_idea.strip():
        raise ValueError("饼胚不能为空")

    raw = raw_idea  # preserve original verbatim
    tags = _extract_tags(raw)
    jiaozi_cu = _extract_jiaozi_cu(raw)
    summary = _build_summary(raw, tags)
    jiaozi = _build_jiaozi(raw)
    product = _pick_product(raw)
    taboo = _build_taboo()
    next_step = _build_next_step(tags)

    return Ticket(
        raw=raw,
        tags=tags,
        jiaozi_cu=jiaozi_cu,
        summary=summary,
        jiaozi=jiaozi,
        product=product,
        taboo=taboo,
        next_step=next_step,
    )
