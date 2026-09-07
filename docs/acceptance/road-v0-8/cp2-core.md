# Road v0.8 CP2：共享 Rust Paper Core

日期：2026-09-07；父提交 CP1 `69fb2f2`。提前 YOLO 覆盖工程退出；本记录随最终 CP2 源码提交。
本阶段 Core 可被宿主调用，但尚未切入手机创作或云端写入；Mac 本地继续使用既有 Python。

## 交付与合同核对

- `frontend/src-tauri/src/paper/` 提供 Paper／Page、严格 parse/render、受控 Vault 打开、
  创建／CAS 保存、列表／全页搜索和只读 reconcile。无 GUI、JSONL、Index 或桌面管理规则导入。
- 共享 corpus 为 `tests/fixtures/paper-v4-golden.json`，由审阅过的合成例子及当前 Python codec 生成。
  两端读取同一份固定文件；不是测试时自行生成“期待结果”。54 项包含 29 项可接受样本和 25 项损坏样本。
- 已逐项核对 Paper v4 设计 §8：frontmatter 顺序与 scalar codec、空 optional、marker 反斜线与连字符、
  多页／Summary、Tags 原有修剪去重、Unicode、LF／CRLF、严格损坏拒绝及日期规范序列化。
  保留 Python 接受的 Unicode 十进制 code 后缀，不悄悄重写为 ASCII。
- 文件操作固定 Home 内 Vault 和各级目录 fd，拒绝符号链接；同目录临时写入、fsync、
  排他创建及原子 exchange。检查被换出的精确字节和身份，发现外部竞争时安全回滚。
  无法证明提交／回滚结果时返回 `commit_unknown` 并保留副本，调用方不得重发。
- duplicate code 同时检查正式文件和已发现的 provider 改名副本内嵌 code；损坏源不部分打开。
  列表／搜索不写 Index，不改作者字符串；本次不实现原生云 metadata 发现，它仍属于 CP4。

## 依赖与维护选择

直接复用锁文件已有 `chrono 0.4.45`、`libc 0.2.189`、`sha2 0.10.9`、`uuid 1.24.0`。
开发者明确批准 Unicode 依赖后，新增并锁定纯 Rust `unicode-normalization 0.1.25` 用于 NFC 比较。
核查发现 `unicode-casefold 0.2.0` 使用 Unicode 9 数据，最终没有将它加入运行依赖；
改用同一生成器产出的 Python Unicode 15.1.0 casefold／十进制字符表。
这些表只用于比较与既有 code 校验，不会转换或重写正文；运行时不调用 Python。

## 实际检查

| 检查 | 本轮结果 |
| --- | --- |
| Python 全量 | `300 passed`，包含共享 corpus 校验 |
| Rust 全量 | `14 passed`；其中 codec 测试消费全部 54 项，文件测试执行真实合成文件工作流 |
| Vitest | `128 passed` |
| 聚焦复验 | 新增根／文件 symlink、provider sibling 和只读对账检查后，2 项 Core 测试通过 |
| 真正文件操作 | 新建、保存、重开、搜索第二页／组合重音／ß／中文类型、过期 snapshot、外部写入竞争回滚、重复 code、不可解析输出拒绝、目录变化与路径逃逸通过 |
| 未知响应 | 丢弃已成功保存响应后只读对账为 committed；未提交编辑对账为 not_committed；不执行重写 |
| 生成稳定性 | corpus 与 Unicode 表重新生成，SHA-256 与生成前一致 |
| iOS | 使用 CP1 局部 SwiftPM native 兼容入口，Tauri debug archive 通过 |
| 工程 | compileall、cargo fmt、文档检查与 `git diff --check` 通过 |

没有选择真实 Vault，没有修改 Python Core、协议或 DTO。测试写入限定为忽略的合成测试目录。
静态生成表较长但不手工维护；需要改变 Unicode 基线时，审阅生成差异并重跑两端 corpus。

## 下一 Gate 与边界

CP2 工程通过，允许进入 CP3：宿主能力分派、iPhone 本机创作、双语、系统导出和按修订恢复稿。
当前 Core 测试在 Mac 执行，iOS 为编译证据；真正手机 Paper 保存／输入／恢复必须在 CP3／CP5 补证。
云端还必须由 Apple 原生协调包住访问，并实现 metadata、下载、losing versions、sibling 保全与恢复；
不能把本地 POSIX 测试或 CP1 往返视为 CP4／CP5 产品同步通过。
