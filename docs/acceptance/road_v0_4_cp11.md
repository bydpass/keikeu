# Road v0.4 CP11 — Gate B 视觉重建证据

> 状态：**Gate B 已通过**
> 日期：2026-07-26
> 基线：CP10 `992f9ca`

## 现在发生了什么

Gate A 的行为没有改变。CP11 把各切片重复的色彩定义收回到一组共享 CSS
tokens，并统一 Paper、Flashcard、Library、Vault 与 runtime gate 的标题、
上下文栏、状态色、焦点和低干扰过渡。Library 上下文栏从 230px 校准到冻结的
260px；旧 CP 编号不再出现在生产界面。

视觉方向仍是“编辑部工作台：安静、密集、可扫描”。记忆点只使用墨色全局栏、
serif 标题、Paper 边注和细窄校样线；没有新增图片、渐变、阴影、字体或依赖。

## 新增概念

- **共享 visual tokens：**`style.css` 是画布、纸张、墨色、强调、信号、危险、
  成功和焦点颜色的单一来源；组件继续拥有各自布局。
- **状态过渡：**只对边框、背景和文字色做 140ms 过渡，帮助识别 hover、focus
  和 selection；`prefers-reduced-motion` 会把非必要动画和过渡降到最低。
- **耐久界面标签：**生产界面使用 Paper、Flashcard、Library、Vault 职责名称，
  不再暴露实现阶段编号。

## 数据怎么走

```text
Python DTO → 现有 Vue 状态与模板 → 共享 tokens + scoped layout → 可见界面
```

bridge、Rust 队列、sidecar、application service、Core、Markdown 和索引路径均
未修改。

## 实际检查

- `.venv/bin/python -m pytest -q` → **321 passed**
- `npm --prefix frontend run test` → **48 passed**
- `cargo test --manifest-path frontend/src-tauri/Cargo.toml` → **10 passed**
- `.venv/bin/python -m compileall -q src` → passed
- `npm --prefix frontend run build` → passed
- `git diff --check` → passed
- 冻结样张在 1220×780、920×680、768×800、375×812 均无水平溢出、重复 ID、
  无名 button 或控制台 warning/error。
- token 对比度范围为 **5.41:1–15.48:1**；深色 rail 的 muted text 为
  **8.44:1**。
- 唯一 bundle ID `app.keikeu.cp11` 的临时 `.app` 在假 Home 和 copied Vault
  中实际显示 Vault、Paper、Flashcard、Library；键盘 Tab 有清楚的可见焦点。
- 开发者首次 Gate B 检查发现窗口滚动时全局功能栏会离开视口。Paper、
  Flashcard、Library 已改为固定在视口左侧的 rail，栏内内容过高时独立滚动；
  ≤520px 仍使用普通横向栏。重建后的隔离 `.app` 在 Paper 与 Library 页面底部
  仍完整显示 K、Paper、Flash、Library 和 LOCAL；开发者复核后确认通过。

## 已知限制

- `.app` 使用批准的 beta 工具链和一次性 `minimumSystemVersion=11.0` override，
  只算 CP11 工程视觉证据，不是 CP12 production bundle 或 CP13 兼容证据。
- 自动检查只能证明布局、状态和可访问性信号；开发者已独立确认视觉方向。
- Gate B 使用的临时应用只读取 copied fixture；通过后已退出并删除临时 Home
  与 bundle。

## 出错怎么查

1. 跨页面颜色或焦点不一致：先查 `frontend/src/style.css` 的共享 tokens。
2. 单页布局或 breakpoint：查对应 View 的 scoped `<style>`。
3. 行为、错误码或磁盘结果变化：视为越过 CP11 范围，回查 Gate A 基线。

## 怎么撤销

撤销 CP11 的 Vue/CSS 与文档 diff 即回到 CP10 `992f9ca`。Gate A 已通过的全部
行为、Flet 回退、Paper schema 和 Vault 内容保持可用。

## 下一步依赖什么

Gate B 已通过并允许提交 CP11。CP12 复用相同行为与视觉，在去标识化真实作者
场景和生产 bundle 中验证，不再重做设计系统。
