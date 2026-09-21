# Road v09.01 原生 iOS 转交清单

状态：待另行实施。本文是 v09 的转交交付，不启动 SwiftUI 工程，不代表新设备验收。批准方向见 [v09](road-v09.md)，当前源码与证据见 [PROJECT](PROJECT.md) 和 [检查点记录](acceptance/road-v09/checkpoints.md)。

## 范围与顺序

v09.01 是独立 Road，从 CP0 起编号。移动端使用原生语言与组件，iOS 采用 SwiftUI，尽可能保留 Rust 业务规则。Mac 保留当前 Vue/Tauri/Python 与云端 Rust 路由；Windows 保留当前技术架构，适配另排；Android 原生实施不在这份 Road。桌面对等、Python 退役与外部 Alpha 各有独立 Gate。

| 检查点建议 | 工作与退出条件 |
| --- | --- |
| CP0：接口与证据冻结 | 审查宿主耦合；冻结 Swift／Rust 的数据、错误、任务取消、生命周期与内存所有权边界；以合成样本验证往返，不新增一套 Swift 业务规则 |
| CP1：运行核心与 Apple 适配 | 从 Tauri 宿主抽离保存、草稿恢复、冲突与存储会话；保留纯规则 crate；将文件协调／系统目录／provider 能力放入 Apple 适配；现有安全回归必须通过 |
| CP2：原生本地创作 | SwiftUI 创建、编辑、多页、Tags、保存、检索、恢复、导出；输入法、键盘、选区、后台和重启取得实机证据 |
| CP3：双端与失败恢复 | 与保留的 Mac 客户端往返、离线、并发、冲突保全、只读核对、存储切换；新客户端按新包重跑，不沿用旧通过结论 |
| CP4：候选验收 | 汇总源码／包绑定和真实场景，按新实现固定并完成验收场景，不继承旧 B14 补验要求；未解决的数据安全问题阻止相应写入与接受 |

以上是下一份计划的编排输入；具体退出条件须在 v09.01 开工计划中固定，不能用本文直接宣称阶段通过。FFI 工具、依赖、最低系统版本及签名方案尚未选定；按现有能力优先，新增依赖依当时授权处理。

## 可复用实现与必须拆开的部分

| 当前入口 | 可复用事实 | 原生接续要求 |
| --- | --- | --- |
| [`keikeu-core`](../crates/keikeu-core/src/lib.rs) | Paper/Page、parse/render、编号校验、NFC＋casefold、结构化错误；无文件访问或 Tauri | 复用相同规则及黄金样本；保持未知元数据、空字段和 Markdown 字节语义 |
| [`store.rs`](../apps/desktop/src-tauri/src/paper/store.rs) | 安全路径、快照、保存、只读核对与检索 | 先解开平台调用再接原生；不把文件与 provider 逻辑塞入纯规则 crate |
| [`host/mod.rs`](../apps/desktop/src-tauri/src/host/mod.rs) | 会话、草稿、请求分发；含 Tauri AppHandle 与 Python 路由 | 分离运行会话与界面 transport，保留未知结果、过期快照和离开保护语义 |
| [`router.rs`](../apps/desktop/src-tauri/src/host/router.rs) | 选定存储、generation、账号边界、云端和 Python 分流 | SwiftUI 只处理可见状态；切换失败保留旧路由，不绕过会话隔离 |
| [`private.rs`](../apps/desktop/src-tauri/src/host/private.rs)、[`conflicts.rs`](../apps/desktop/src-tauri/src/host/conflicts.rs) | 本机保全与冲突原字节恢复 | provider 不可用时仍能取回本机原文；不自动晋升、覆盖或丢弃副本 |
| [`platforms/apple`](../platforms/apple/) | 三份现有 Swift 宿主／文件协调实现 | 明确目录、下载状态、协调访问及系统分享完成／取消；保留原生 provider 错误 |
| [`Python 桌面后端`](../apps/desktop/python/)、[`Vue 工作面`](../apps/desktop/src/) | 桌面完整能力与现有安全回归 | 原生移动替换不能退化既有 Mac；Python 退役另行验收 |

## 新客户端必须重跑的验收

- 内容：多页、Tags、未知元数据、空字段、多语言与组合重音；错误格式保留原文并可人工修复。
- 编辑：中文／英文／韩文输入、候选词、软键盘、光标选区与滚动；未保存离开与普通关闭保护。
- 本地持久性：连续保存、后台／重启恢复、失败保留、导出成功与取消；不能只以提示文字证明落盘。
- 双端：Mac／iPhone 在线与离线往返、同稿并发、同编号新建、provider 自动改名和原生冲突分别记录。
- 恢复：原字节本机保全、明确晋升／恢复、保存结果未知后的只读核对；禁止自动重放写入。
- 隔离：验证新实现中的目标不可下载与存储切换失败，保留作者输入和旧路由；账号／容器／Drive 相关场景在新架构确定后重新判断，不直接继承旧 B14。

## v08 转交的证据边界

v08 已中断，CP5 未最终接受；原记录 [B01–B16](acceptance/road-v0-8/cp5-candidate.md) 中 15 组通过只对应旧候选和当时平台。安装版本 `83c4f60` 与后续源码 `deaece8` 不相同，不能把旧设备结果移给新包。

B10 两轮同编号新建实际得到 provider 改名副本；原生冲突保全由 B09／B11 的已有稿并发证明。“同编号新建同时产生原生冲突”没有实测证据，保留这个区别。

2026-09-20 开发者决定：旧候选 B14 不再需要解决或补验，事项关闭；不作为本 Road 的继承待办或验收阻点。[旧 SOP](acceptance/road-v0-8/b14-test-sop.md) 仅保留历史用途，不表示测试通过。相关问题可能随 iOS 重构再次出现，也可能因实现改变而消失；在新架构和实际行为明确后重新判断，必要时建立新的问题与验收项。

## 下一次开工最小读取路径

先核对 worktree、HEAD 与状态，读 PROJECT、v09 最终记录及本文；再按待拆部分读取上表源码和直接测试。重新构建新包，逐项绑定源码、包摘要、平台、日期、操作和保全证据。先起草 v09.01 的 CP0 接口冻结记录，再开始实现；不新增未来 Road 编号。
