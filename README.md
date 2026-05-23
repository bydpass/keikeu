# keikeu

> 把「我想看这个」变成「这个该怎么写 / 怎么约 / 怎么展示」。
>
> Turn *"I want to see this"* into *"here is how to write / commission / display it."*

`keikeu` 是一个面向同人创作者的「口嗨 → 创作 brief」工具。输入一段 CP 口嗨、名场面或剧情梗（**饼胚**），生成三种 Markdown 视图：自用 SOP / 约文 Brief / 灵感名片。

`keikeu` is a fanwork *idea → brief* tool for shippers and fic-commissioners. One raw idea (**饼胚** / *peibei*) fans out into three Markdown views: self-use SOP, commission Brief, inspiration Card.

---

## 安装 / Install

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

Requires Python 3.11–3.13.

## 运行 / Run

```bash
python -m keikeu.app
```

会打开一个桌面窗口。粘贴一段饼胚 → 点击「生成饼胚」→ 在三个 tab 间切换 → 点击「复制当前 Markdown」。

A desktop window opens. Paste a raw idea → click **生成饼胚** → switch between tabs → click **复制当前 Markdown**.

## 测试 / Tests

```bash
pytest
```

## v0.1 不包含 / What v0.1 does NOT include

- 账号系统 / accounts
- 云同步 / cloud sync
- AI 模型接入 / AI API integration (uses a local rule-based generator)
- 社群发布 / community publishing
- 约稿交易 / commission marketplace
- 支付 / payments
- 图片生成 / image generation
- 多人协作 / multi-user collaboration
- 完整正文生成 / full-text fiction generation

详见 [SPEC.md](SPEC.md) 与 [TECH_SPEC.md](TECH_SPEC.md)。See [SPEC.md](SPEC.md) and [TECH_SPEC.md](TECH_SPEC.md) for product and tech contracts.
