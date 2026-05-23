from .models import KeikeuSpec


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


def render_sop(spec: KeikeuSpec) -> str:
    return f"""# 饼胚 SOP

## 原始灵感 I

{spec.raw_idea.strip()}

## Tags

{_bullets(spec.tags)}

## 饺子醋（必须保留的画面 / 瞬间）

{_bullets(spec.vinegar)}

## Summary

{spec.summary}

## 饺子（让饺子醋成立的铺垫）

{_bullets(spec.dumplings)}

## 成品形态

{spec.final_form}

## 禁忌

{_bullets(spec.taboos)}

## 下一步

{_bullets(spec.next_steps)}
"""


def render_brief(spec: KeikeuSpec) -> str:
    cp_tags = [t for t in spec.tags if any(sep in t for sep in ("/", "×", "x", "&"))]
    cp_line = "、".join(cp_tags) if cp_tags else "（待补充）"
    selling_points = spec.vinegar[:3] if spec.vinegar else ["（待补充）"]

    return f"""# 约文 Brief

## 想约什么

一篇以下列饺子醋为核心的同人短打 / 中篇，篇幅建议见下文。

## CP / 角色关系

{cp_line}

## 核心卖点

{_bullets(selling_points)}

## 必须出现的画面

{_bullets(spec.vinegar)}

## 故事大意

{spec.summary}

## 希望的风格

保留原文情绪密度，重点托住饺子醋；不要过度填充支线。

## 禁忌与雷点

{_bullets(spec.taboos)}

## 可自由发挥部分

- 配角戏份与对话节奏
- 章节切分与场景转换
- 非饺子醋部分的氛围与文风修辞

## 篇幅建议

{spec.final_form}
"""


def render_card(spec: KeikeuSpec) -> str:
    headline_keyword = next((t for t in spec.tags if t != "同人"), "饼胚")
    top_vinegar = spec.vinegar[0] if spec.vinegar else "（饺子醋待定）"

    return f"""# 灵感名片

## 一句话

{spec.summary}

## 关键词

{_bullets(spec.tags)}

## 我最想看到

> {top_vinegar}

## 适合做成

{spec.final_form}

## 当前状态

{_status_from_length(spec.raw_idea)}

---

_关键词锚点：{headline_keyword}_
"""
