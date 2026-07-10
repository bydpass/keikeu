# keikeu 对照审计：review v0.1 × 当前代码

日期：2026-07-04 ・ 代码基线：`5948c0d init:pre-alpha_macos_build`（2026-06-20，此后 src/ 无改动）
核心测试：70 passed（`tests/test_app_pages.py` 需 Flet 环境，未在本次沙盒运行）

## 一、六项 0 号用户反馈逐条判定

| # | 反馈 | 判定 | 依据 |
|---|---|---|---|
| 1 | 画面太安卓 | **未动**（方向已探索） | `main.py` 仍是默认 Material NavigationRail + Material icons + 英文按钮文案；但 7-2 新增 `keikeu-ui-prototype.html`（未提交），视觉方向已在纸面上，未落进 Flet |
| 2 | 不能快捷删除 | **未动** | 全代码库无任何 delete 路径；`vault.py` 布局无 `.trash/` |
| 3 | 逻辑关系繁琐 | **未动** | `outline_editor_page.py` 关系行仍要求手填 `target path` 文本框——正是 review 明令禁止的形态 |
| 4 | outline 格式偏差 | **部分完成** | 见下方 P0-001 细目 |
| 5 | archive 与 status 重合 | **未动** | `cache_page.py` 同时存在含 `archived` 的 status 下拉与 Archive 按钮 |
| 6 | 不能导出 Markdown | **未动** | 只有 vault 内保存，无「另存到用户选定位置」 |

## 二、P0-001 outline schema 现状细目

已达标：七个章节 header 与设计 byte-exact；空字段可留白；纯文本编辑器可读；frontmatter 手写转义无 PyYAML；round-trip 有测试覆盖。

仍偏差（对照 appdesign.md §5.1）：

1. **§4 观前提醒**是自由文本，设计要求三行结构：`- 原作 / AU / IF / PA：` `- CP 结构：` `- 情节元素：`
2. **§6 Ending Type** 正文只写 `custom_ending`——HE/BE/OE 时正文该节为空，ending 只藏在 frontmatter，纯文本读者看不见结局类型
3. **§7 关系行**是 `- prequel | 路径 | 备注` 管道格式，设计是 `- 关系：/ - 关联对象：/ - 说明：` 标签行
4. §3 冒号为半角 `- Fandom: `，设计示例为全角 `- Fandom：`（小，需定夺后统一）

## 三、Road v0.1 各 Phase 状态

| Phase | 内容 | 状态 |
|---|---|---|
| 0 | 提交绿色状态 | **部分**：代码已提交，但 7 个文档/原型文件仍未提交（CLAUDE.md、ethics.md、readmedesign.md、UI 原型等） |
| 1 | 修 outline schema | **部分**（见上） |
| 2 | 导出 Markdown | 未动 |
| 3 | 删除/归档重构（.trash 软删除） | 未动 |
| 4 | 逻辑关系 picker | 未动 |
| 5 | 视觉气质修正 | 原型 HTML 已有，未落地 |

另：Library 页缺 review §8.3 要求的「打开文件」「在系统文件夹中显示」两项。

## 四、已立住的骨头（不需要动）

- 架构契约成立：`keikeu_core` 零 Flet 依赖，序列化只在 `markdown_io.py`
- 不变量 1（原文逐字保留）与不变量 2（索引可弃、Markdown 为本体）均有实现与测试
- 索引损坏静默重建，`list_*` 永不崩
- 文件名防碰撞、frontmatter 转义、CJK slug 均处理干净

## 五、建议动线（与 review 优先级一致）

1. 提交当前文档态（Phase 0 收尾，一个干净 commit）
2. P0-001 收尾：修 §4/§6/§7 三处偏差 + 冒号定夺 → 改测试 → 一个 commit
3. 依序：导出 → .trash 软删除 + archive 去重合 → 关系 picker → 视觉落地
