# ADR-0009：逐步统一 Rust Core，保留 Vue/Tauri

**日期：** 2026-09-04

**状态：** 方向与文档重构已批准；实施未开始，软件 CP0 seed 未批准

**决策者：** 开发者

> 2026-09-20 后续决定：[ADR-0010](0010-v09-engineering-continuation.md) 已将移动端改为原生组件并中断 v08；下文保留原决定历史，当前工程顺序以 [v09](../../road-v09.md) 为准。

## 背景

[ADR-0004](0004-vue-tauri-python-sidecar.md) 定义当前唯一已接受桌面运行链：
Vue/Tauri → JSONL protocol v2 → Python service/core。Paper v4 Markdown、Index v4、
现有桌面资料管理与安全合同已经接受，不能为移动端删减这些能力。

原 v0.8 草案在 macOS 本地保留 Python，在移动与共享 iCloud Vault 增加 Rust Paper Core，
没有双后端结束条件。开发者现要求降低长期成本，并让 iPhone 核心创作能够与 Mac 同步。
本次审计基于计划、权威文档及平台文档，不是产品源码审计或设备可行性验证。

## 方案比较

| 方案 | 收益 | 代价与决定 |
| --- | --- | --- |
| 保留双后端 | 桌面短期改动最少 | 长期维护两套业务语义与回归链；只作为临时过渡 |
| 嵌入 Python | 可复用既有 Core，减少语言迁移 | 需维护移动解释器打包、原生调用及文件适配；本路线不采用 |
| 逐步统一 Rust Core | 复用 Vue/Tauri，最终只维护一套产品 Core | 承担桌面对等迁移成本；采用，并设置退役 Gate |

不能把“当前子进程不可直接搬到 iOS”写成“Python 无法运行于 iOS”。
[Python 3.13 官方文档](https://docs.python.org/3.13/using/ios.html)支持嵌入解释器，
[Tauri Shell 文档](https://v2.tauri.app/plugin/shell/)则把 iOS／Android 能力限制为打开 URL。
选择 Rust 是本项目的维护决策；不从平台限制推导出唯一语言选择。

## 决定与过渡

1. 保留 Vue/Tauri；v0.8 iPhone 本地与 Mac/iPhone 云端共用非 GUI Rust Paper Core。
   iCloud 同步是必需交付，Apple 适配层负责原生发现、下载、协调与冲突版本访问。
2. v0.8 macOS 本地继续使用现有 Python sidecar，保留完整桌面能力。Paper v4 不变，
   不借语言迁移改写作者文件。对照样本须审阅，书面合同与实现冲突必须先裁定。
3. 保留 `bridgeRequest` 边界；共享业务 DTO、平台／存储能力和 host 新方法分开冻结。
   过渡期不扩展 Python protocol v2，不伪造移动端不存在的 Index 状态。
4. 每个客户端对所选 Vault 只启用一个受控写入后端，不双写，不在错误后自动切换后端。
   跨设备并发仍需处理；Rust 不以本机 CAS 代替 Apple 文件协调和冲突保全。
5. v0.8 候选通过后，独立迁移桌面剩余 Index、文件夹、Trash、历史迁移、恢复、设备状态
   与系统动作。完成桌面对等及副本切换验证后，移除 sidecar、产品 JSONL 调用与 Python 打包。
   Python 可以留作开发期对照工具，不能继续成为分发候选的运行依赖。
6. 首轮外部 Alpha 必须等待统一核心收口通过；v0.8 候选接受不代表可以直接招募或分发。

## 验证、代价与失效条件

- CP0 冻结合同，CP1 用合成数据及实际 Apple 能力验证两端往返，再投入 Core 与界面实现。
  必需设备、授权或能力缺失时记录阻塞；不得以文档、模拟器或 mock 代替实际证据。
- 原生协调不能用普通目录扫描替代；先保全并验证冲突原始字节，再标记已处理；提升版本前
  先保全当时活动版本。[Apple 同步说明](https://developer.apple.com/documentation/uikit/synchronizing-documents-in-the-icloud-environment)
- 临时双后端增加对照测试成本；最终迁移必须覆盖全部既有桌面能力，不能用移动端窄范围
  代替桌面对等。数据安全、未知结果、旧格式迁移和真实分发均各有证据，不因换语言自动成立。
- 如果 CP1 否定原生能力可行性，或对等／安全切换无法成立，停止后续阶段并重新评审本决策；
  不自动采用嵌入 Python、改换 UI 框架、删去同步，或带双后端进入外部 Alpha。

## 对现有决策的效力

本 ADR 批准未来方向，不立即取代 ADR-0004 对当前运行时的约束，也不授予软件实施权限。
只有开发者接受相应替换阶段后，新增 Rust 路径才获得该阶段约定的产品与文件所有权；
候选后收口的完整桌面对等、安全切换及无 Python 产品依赖 Gate 通过后，才完成对 ADR-0004
运行架构的替代。旧 ADR 与历史验收记录保留原文，不把未来目标改写为过去事实。

施工顺序、收口条件和当前批准边界以 [当前 v09 计划](../../road-v09.md)、
[SPEC](../../SPEC.md)、[RULES](../../RULES.md) 与 [PROJECT](../../PROJECT.md) 为准。
