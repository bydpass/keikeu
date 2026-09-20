# Road v09 执行记录

## CP0：基线集成

日期：2026-09-20。分支：`codex/road-v09-cp0-baseline`。开发者已批准 CP0–CP4 YOLO 与本地提交，不含推送、发布或 v09.01 实施。

输入：候选 `deaece8`；原工作区 `78eb755` 手册；`0447e16` 清理；`670142d` 批准计划。归档清理提交同时包含此前 PROJECT 顶部的转交提示，其余规划在后一提交中保存。两份原工作区保留，四份权威冲突按新候选事实与批准方向逐项解决。

工程接续例外见 [ADR-0010](../../architecture/decisions/0010-v09-engineering-continuation.md)。不把中断的 v08 或 B14 记为通过；现有安装 `83c4f60` 不代表后续主题 HEAD。

规划阶段原工作区工具测试 18 通过、1 失败：已删除归档引用，按计划留待 CP3。整合后全量 Python 300 通过、1 已知失败；首次缺少临时目录产生环境错误，创建隔离目录后复跑所得此结果。文档检查 86 active / 14 required 通过，差异空白检查通过。产品源码未修改，CP0 按批准的已知失败转交 CP3 边界完成。历史包、私有运行数据、签名和设备均未移动或操作。

## CP1：目录与构建入口

从 CP0 `e2c36d4` 建立 `codex/road-v09-cp1-layout`。仅搬 tracked 源码：`frontend/` → `apps/desktop/`，`src/` → `apps/desktop/python/`，三个 Swift 文件 → `platforms/apple/`。Python 导入名不变，业务代码不变；更新脚本、构建、测试与活动文档路径，历史验收只修源码链接。修复新工作区 pytest 缺少隔离临时目录父级的问题，Rust 测试路径统一回根目录 `tests/test-vault/`。

CP1 检查：前端 Vitest 142/10 通过、Vite 生产构建通过、Cargo 21 项通过、Python wheel 构建通过。独立 `.venv` 重建 sidecar，并检查 PyInstaller TOC：15 个项目模块全部来自 v09 新目录。共享旧 venv 的首轮包不作为交付证据；新环境安装项目后复验 Python。目录页 288 路径、链接、搜索及切换检查通过，文档 86/14 通过。npm/Cargo 离线缓存不足后按原锁定版本补齐；首次 npm 解析到错误引擎，改用项目固定 Node 22.23.2/npm 10.9.8 后通过。未做设备操作。

独立环境最终 Python 全量：300 通过、1 已知归档引用失败；compileall 通过。CP1 按已批准转交 CP3 的边界完成。

首次 CP1 提交被本机凭据钩子误报旧测试占位值阻止；将该占位值改为 `test-fresh`，保留迁移重启不重放场景，定向复验后重试 aic；未禁用钩子。

## CP2：独立纯规则核心

从 CP1 `32001ef` 建立 `codex/road-v09-cp2-core`。独立 Paper codec、Unicode 比较及错误类型，宿主薄重新导出保持调用链。根 Cargo workspace 统一锁文件，保存／恢复／云端运行代码未改。仅将宿主需要的 `code_sequence` 和错误构造器公开；JSON 字段及错误语义不变。黄金样本及 Unicode 表按原字节搬迁，不重生成。

独立核心测试 2 项通过、Python 黄金样本测试通过；依赖树不含 Tauri/Apple。逐项核对 Cargo 注册表依赖版本与校验和完全未变；黄金样本和 Unicode 表与 `deaece8` 字节一致。

完整 Cargo workspace 22 项通过（独立核心 2、宿主 20）；格式检查在新路径换行调整后通过，文档 86/14 和目录树 291 路径检查通过。CP2 工程完成，不证明新原生客户端或新 provider 验收。
