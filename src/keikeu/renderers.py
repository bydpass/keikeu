from .models import Ticket


def _bullets(items: list[str]) -> str:
    if not items:
        return "_（暂无）_"
    return "\n".join(f"- {item}" for item in items)


def _status_from_length(raw: str) -> str:
    length = len(raw.strip())
    if length < 60:
        return "可收藏（饼还小，留着发酵）"
    if length < 300:
        return "可开写（饼胚已成形）"
    if length < 800:
        return "可约文 / 可扩纲"
    return "可扩纲（信息量已足够，建议先拉大纲）"


def render_sop(ticket: Ticket) -> str:
    return f"""# 饼胚 SOP

## 原始灵感 I

{ticket.raw.strip()}

## Tags

{_bullets(ticket.tags)}

## 饺子醋（必须保留的画面 / 瞬间）

{_bullets(ticket.jiaozi_cu)}

## Summary

{ticket.summary}

## 饺子（让饺子醋成立的铺垫）

{_bullets(ticket.jiaozi)}

## 成品形态

{ticket.product}

## 禁忌

{_bullets(ticket.taboo)}

## 下一步

{_bullets(ticket.next_step)}
"""


def render_brief(ticket: Ticket) -> str:
    cp_tags = [t for t in ticket.tags if any(sep in t for sep in ("/", "×", "x", "&"))]
    cp_line = "、".join(cp_tags) if cp_tags else "（待补充）"
    selling_points = ticket.jiaozi_cu[:3] if ticket.jiaozi_cu else ["（待补充）"]

    return f"""# 约文 Brief

## 想约什么

一篇以下列饺子醋为核心的同人短打 / 中篇，篇幅建议见下文。

## CP / 角色关系

{cp_line}

## 核心卖点

{_bullets(selling_points)}

## 必须出现的画面

{_bullets(ticket.jiaozi_cu)}

## 故事大意

{ticket.summary}

## 希望的风格

保留原文情绪密度，重点托住饺子醋；不要过度填充支线。

## 禁忌与雷点

{_bullets(ticket.taboo)}

## 可自由发挥部分

- 配角戏份与对话节奏
- 章节切分与场景转换
- 非饺子醋部分的氛围与文风修辞

## 篇幅建议

{ticket.product}
"""


def render_card(ticket: Ticket) -> str:
    headline_keyword = next((t for t in ticket.tags if t != "同人"), "饼胚")
    top_vinegar = ticket.jiaozi_cu[0] if ticket.jiaozi_cu else "（饺子醋待定）"

    return f"""# 灵感名片

## 一句话

{ticket.summary}

## 关键词

{_bullets(ticket.tags)}

## 我最想看到

> {top_vinegar}

## 适合做成

{ticket.product}

## 当前状态

{_status_from_length(ticket.raw)}

---

_关键词锚点：{headline_keyword}_
"""


# Ticket output modes — one Potion Ticket fans out into three Markdown views.
MODES = {
    "SOP": render_sop,
    "Brief": render_brief,
    "Card": render_card,
}


def render_ticket(ticket: Ticket, mode: str) -> str:
    """Render a Ticket in one of its output modes: 'SOP' | 'Brief' | 'Card'."""
    try:
        return MODES[mode](ticket)
    except KeyError as exc:
        raise ValueError(f"未知输出模式：{mode}") from exc
