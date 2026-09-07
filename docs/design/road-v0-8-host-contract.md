# Road v0.8 CP0：宿主与共享 Paper 合同

状态：2026-09-07 合同冻结；开发者已授权本轮 CP0–CP5 工程与本地提交，并提前声明 YOLO。
来源：[施工计划](../../PLAN_road_v0_8.md)、[SPEC §13](../SPEC.md#13-documented-unified-core-target)。
本文件定义待实现增量，不宣称 Apple、Rust Core 或实体设备已经通过。

## 1. 路由与身份

- Vue 继续调用 `bridgeRequest(method, params)`，Tauri 宿主先分类后分派。
  新增 `host.*` 方法绝不转发 Python；其严格 JSONL protocol v2、`system.hello` 与 DTO 保持不变。
- 桌面本地走原 sidecar；iPhone 本地与双端 iCloud 走进程内 Rust。
  每个宿主以一个串行队列管理存储选择及正式写入，不双写、不在失败后回退另一后端。
- 启动先调用 `host.capabilities`，取得 `platform`（`macos`／`ios`）、`storage_id`、
  `generation`、`backend`（`python`／`rust`）与已启用方法名数组 `methods`。
  `storage_id` 是本机持久化的不透明身份，不含路径／账号；`generation` 每次成功切换递增。
  容器账号身份变化使旧会话失效，阻断云端操作并要求重新连接，不复用旧令牌。
- Rust 业务请求和与存储有关的 host 请求带 `storage_id`、`generation`；宿主校验后剥离，
  不改变共享业务参数。Python 请求保留原形，宿主为其绑定接收时身份。
  Vue 请求同时捕获 generation，晚到响应只能归还原请求，不可覆盖当前视图或清理新草稿。
- `host.capabilities` 在首次加载和成功切换后读取。方法不在能力表中时，界面不显示入口，
  宿主仍返回 `unsupported_method`；隐藏按钮不是权限校验。

## 2. 方法责任表

共同响应沿用 `{ok,result}`／`{ok:false,error}`，错误包含 `code,layer,message,recovery`。
表内参数省略上一节的存储身份。除只读操作外，不自动重放；结果不确定先检查状态。

| 方法／调用方 | 分类、唯一所有者 | 参数与成功结果 | 失败／未知结果 |
| --- | --- | --- | --- |
| `host.capabilities`／App | 只读，宿主 | 无参数；§1 能力声明 | 启动错误可见，可再次只读检查 |
| `host.storage.inspect`／存储选择 | 只读，宿主与 Apple | `kind: local/icloud`；`ready/unavailable/not_downloaded` 与候选 token | 不创建容器内容，不切换 |
| `host.storage.select`／App | 本机状态与首次专用 Vault 初始化，宿主 | `token`；新能力声明 | 先验证，后原子记录选择；未知时读 capabilities，不重放 |
| `paper.create_draft`／Paper | 会话只读，选定后端 | 复用当前业务参数；PaperDto | 不落正式文件，不预留文件名 |
| `paper.open`／Paper | 只读，选定后端 | `path`；`opened` 或 `repair_required` | 损坏文件不部分打开 |
| `paper.save`／Paper | 正式 Paper 写入，选定后端 | PaperSaveDto；PaperSaveResultDto | `stale_snapshot` 保稿；`commit_unknown` 冻结并只读对账 |
| `paper.reconcile_save`／App | 只读，选定后端 | 当前 reconcile 请求；§3 结果 | 不重写 Paper，不清理草稿 |
| `library.query`／Library | 只读，选定后端 | 当前查询／排序参数，Rust 仅活动区；§3 投影 | 局部坏稿列 errors；云端未下载不当作不存在 |
| `host.export`／Paper 或恢复界面 | 系统交付副本，宿主 | `source: paper/draft/conflict` 与对应 token；`exported/cancelled` | 只导出已选快照；取消／失败不改正式稿、不清稿；未知不重复弹面板 |
| `host.draft.put`／编辑状态 | 本机私有恢复区写入，宿主 | §4 恢复记录；已持久化 revision | 写失败可见；读回相同 revision 与摘要确认，不自动清理 |
| `host.draft.list`／启动恢复 | 本机只读，宿主 | 当前 storage_id；恢复摘要与不透明 token | 不向诊断返回正文 |
| `host.draft.read`／恢复界面 | 本机只读，宿主 | `token`；完整恢复记录 | 返回编辑草稿，不覆盖正式稿 |
| `host.draft.discard`／明确丢弃或保存成功回调 | 本机恢复记录删除，宿主 | 精确 token/revision；`removed/absent` | 只删匹配修订；未知先 list |
| `host.locale.get/set`／设置 | 本机读／写，宿主 | set 仅 `zh-CN/en`；当前语言 | 首次系统语言，未匹配用 en；保存失败显示，正文不变 |
| `host.cloud.status`／同步界面 | 原生发现／状态读取，Apple 薄层 | 当前 metadata 与冲突摘要 | 账号、容器、下载、协调失败分别显示 |
| `host.cloud.download`／明确打开未下载项 | provider 下载请求，Apple 薄层 | 不透明文件 token；`requested/available` | 用 status 观察；不据请求成功宣称下载或同步完成 |
| `host.conflict.preserve`／恢复界面 | 私有恢复副本写入与原生已处理标记，Apple 薄层 | 发现快照 token；已校验副本 token 集合 | 全部原字节持久化并回读校验后才标记；中断可检查，不覆盖旧副本 |
| `host.conflict.list`／恢复界面 | 只读，宿主与 Apple | 原生版本、改名 sibling、已保全副本摘要 | 两种发现路径并存，不能只数 NSFileVersion |
| `host.conflict.promote`／明确恢复 | 正式稿协调 CAS，Rust＋Apple | 保全副本 token、活动稿快照 token；新 Paper 或 repair 状态 | 先保全当前稿；未知只读 inspect/open；损坏副本只准原字节导出 |

原桌面 Vault、Index、文件夹、Trash、迁移、系统 open/reveal 方法继续由 Python／既有宿主处理，
仅在 macOS 本地模式提供。iPhone 与云端不接受这些方法；不建立通用插件或存储接口。

## 3. Paper 与无 Index 投影

- `CardPageDto`、可编辑字段及 PaperDto 沿用 `src/keikeu_bridge/dto.py` 的业务语义：
  `name/content/type`，`display_name/tags/pages`，及路径、code、时间、快照和不透明 edit_token。
  未知 frontmatter 留在 Core 打开快照内，UI 不回传也不能删掉；保存合并可编辑字段。
- Rust 保存复用 `paper/warnings`；open 保持互斥 `opened`／`repair_required` 标签。
  损坏全文仅经明确原字节导出交付，不进入普通编辑。
- Rust reconcile 复用 `committed/not_committed/stale/repair_required` 及各互斥字段，
  仅宿主 Rust 投影允许 `index_state: not_applicable`。Python DTO 不增加该值。
- Rust Library 复用 entries、errors、vault_locator、活动文件夹投影；`scope: active`、
  `trash_folders: []`、`trash_count: 0`、`index_state: not_applicable`。
  界面隐藏 Index 重建和 Trash，不能把空数组解释成桌面管理能力。
- Rust 扫描 `cache/` 根与一层普通文件夹，沿用 Paper v4 路径规则；云端枚举先经原生 metadata，
  未下载项保留状态。其他文件、未知目录和 sibling 不删除、不自动改名。
- CAS 对精确源字节摘要和文件身份核验；创建拒绝已存在及等价 code。
  原生协调包住云端读／比较／替换；本地同样防路径替换及符号链接逃逸。

## 4. 草稿、切换与恢复

- 恢复键为 `(storage_id, draft_id, revision)`；draft_id 在新建时生成，保存前后不变；
  revision 是该草稿会话单调递增整数。记录包含 editable、baseline、Paper 身份、
  source_digest、target_path 和待确认保存的 submitted；无正文日志、无同步。
- 输入静止 500ms 后保存当前修订；进入后台／页面隐藏立即尝试刷新。串行持久化，
  同目录临时文件、安全替换并回读摘要之后才显示已保护。更新不能回退 revision。
  本机 Application Support 私有区与 Vault 分开，Apple 标记排除云备份；配置身份同样本机保存。
- 显式保存前先持久化 submitted 恢复记录，失败则阻断正式保存并给出导出入口。
  已知保存成功后只清理该 submitted revision；新输入产生的新 revision 留存。
  失败、stale、repair 或未知结果都保留。重启恢复产生可编辑副本，正式文件仍需正常 CAS。
- 关闭／存储切换复用 App-root pending intent 和 dirty departure；存在未决正式写入禁止切换。
  新目标验证完成、所需专用目录安全建立、选择原子写入后才发布新 generation。
  失败保留旧选择；恢复区写失败不允许静默丢弃。
- 同 code sibling 不自动改名或改内嵌 code。先保全每份原字节，显示可导出版本；
  用户可选有效副本替换对应活动稿（先保全活动稿并 CAS），原 sibling 保持不动。
  未能证明冲突对象完整保全时仍显示待处理并阻断该 code 写入。
- 恢复副本用随机本机身份与校验摘要；中断时只恢复记录关联，不覆盖已有副本。
  NSFileVersion 标识视为会话句柄，重启重新发现，不假定可安全归档或版本 URL 可写。

## 5. 验证与阶段记录

CP0 校验：逐项追踪现有 `bridge.js → commands.rs → bridge.rs → protocol.py → dto.py`，
确认宿主方法不污染 Python 白名单；每个新增写操作在责任表中具有唯一所有者和未知结果路径。
共享合同以 Paper v4 书面规则及经审阅 golden 为裁定依据，不复制历史通过次数。

- CP1：实体双端探针、真实容器往返、协调与原字节保全；缺证据只继续独立准备。
- CP2：合法／非法／边界 golden、CAS、故障注入、路径逃逸与桌面回归。
- CP3：保存期间新修订、恢复写失败、重启恢复、导出取消、启动错误与原生 smoke。
- CP4：切换过期响应、未知写入不重放、系统版本与 sibling、多个冲突及中断保全。
- CP5：同源码双端候选、完整回归、批次 B 实体输入与真实 provider 矩阵、无 P0/P1。

CP0 不新增运行时依赖；Apple 薄层使用系统框架，CP1 按当前安装工具链验证具体构建。
Core 所需依赖先检查现有可用项；确有新增需求时明确说明用途、打包影响与风险，再按授权处理。

本阶段机器检查及提交结果记录在施工计划；应用、构建和设备检查不属于 CP0 文档通过证据。

## 6. CP3 宿主投影补充

Rust `host.draft.put` 使用 `draft_id/revision/edit_token/raw`；宿主绑定完整 Paper 基线和源摘要，
不接受 UI 删除未知 frontmatter。`paper.save` 在 Rust 路由额外携带 `draft_id/revision`，
宿主先保护精确 submitted，再执行正式写入；Python 保存参数保持不变。
Rust `paper.reconcile_save` 使用该恢复 `draft_id` 读取宿主保护的完整 submitted（含时间），
以避免由 UI 重建不同字节。恢复区版本为 1，后续改动必须显式兼容。

损坏 open 的 repair 投影附加 `export_token`，`host.export(source: paper)` 按该令牌交付原字节。
恢复区不可写时，`host.export(source: raw, raw: ...)` 可将当前编辑原文交给系统导出；
此入口不写正式稿、不清恢复稿，不把未通过 Paper 校验的输入伪装成 Markdown Paper。
只读核对后，`host.draft.put(settle: true)` 新修订可确认未提交结果；宿主会重新核对，绝不重放保存。
