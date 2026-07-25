# Road v0.4 理解优先规约

> 状态：Active Road v0.4 execution gate
> 适用范围：Road v0.4 的 Application Service、Vue、Tauri、Rust、JSONL sidecar、PyInstaller 与 macOS 打包工作。
> 核心原则：开发者必须拥有项目的解释权。任何无法被开发者理解、检查和回滚的实现，都不算完成。

---

## 1. 开发者无需精通所有技术，但必须理解项目中的职责

Road v0.4 中的新技术只允许承担以下职责：

| 技术                         | 在 keikeu 中的唯一主要职责               |
| -------------------------- | ------------------------------- |
| Vue                        | 页面、表单、可见状态与用户交互                 |
| Vite                       | 前端开发服务器与生产构建                    |
| Tauri                      | 桌面窗口、应用生命周期与权限边界                |
| Rust                       | 管理 Tauri、Python sidecar 和少量系统动作 |
| JSONL                      | Rust 与 Python 之间的结构化消息协议        |
| Python application service | 编排现有业务能力，供 Flet 与 JSONL 共用      |
| Python Core                | Paper、Vault、Markdown、索引和安全规则    |
| PyInstaller                | 把 Python sidecar 冻结为可随应用分发的二进制  |

禁止用“框架推荐”“最佳实践”“大家都这么做”解释设计。

每个技术选择都必须回到 keikeu 的具体需求。

---

## 2. 每个 Checkpoint 开始前，必须先交付概念说明

Agent 在修改代码前，必须先提交一份简短说明，至少回答：

1. 本 Checkpoint 要解决什么具体问题？
2. 会引入或接触哪些新概念？
3. 每个概念在 keikeu 中承担什么职责？
4. 数据和控制从哪里进入，经过哪里，从哪里返回？
5. 哪些现有文件会修改？
6. 哪些作者资产和业务规则明确不会修改？
7. 最可能出现哪三类故障？
8. 怎样验证、调试和回滚？

说明必须使用项目中的真实文件、模块和操作举例。

禁止只给通用教程或术语定义。

---

## 3. 未通过“解释权检查”，不得进入编码

开始一个 Checkpoint 前，开发者应当能够用自己的话回答：

* 这一步增加了什么？
* 它为什么放在这一层？
* 它坏掉时，问题会表现在哪一层？
* 我要怎样退回上一个可运行状态？

只要其中一项仍然含糊，该 Checkpoint 就保持未开始。

Agent 应继续解释或缩小任务，不得用更多代码掩盖理解缺口。

---

## 4. 一次只引入一个主要未知变量

每个 Checkpoint 应尽量只验证一个新的技术边界。

推荐顺序：

```text
Application Service
→ Flet 通过新 Service 运行
→ JSONL 协议
→ Rust 管理 Python sidecar
→ Tauri 应用壳
→ Vue 读取数据
→ Vue 执行写入
→ 打包
```

禁止同时进行以下组合：

* 一边提炼 Application Service，一边重写 Vue 页面
* 一边设计 JSONL，一边修改 Core 业务规则
* 一边迁移功能，一边全面重做视觉
* 一边排查 sidecar，一边处理签名、公证或旧系统兼容

无法拆分时，必须先做不接触真实 Vault 的最小实验。

---

## 5. 新依赖必须经过开发者批准

引入任何运行时、构建或测试依赖前，Agent 必须说明：

* 包名与精确版本
* 直接用途
* 属于运行依赖、构建依赖还是测试依赖
* 为什么现有依赖无法完成
* 是否存在更轻的替代方案
* 移除它需要改动哪些文件
* 它会不会进入最终 `.app`

未经批准，不得修改：

```text
package.json
package-lock.json
Cargo.toml
Cargo.lock
pyproject.toml
Python build lock
Tauri plugins
capabilities / permissions
```

自动脚手架生成的新依赖也不例外。

---

## 6. Rust 必须保持为窄宿主层

Rust 只允许负责：

* Tauri 窗口和生命周期
* 启动、监控和停止 Python sidecar
* JSONL 请求队列与响应匹配
* 原生目录选择
* 经过 Python 再次验证的 open / reveal
* 阻塞错误页和 sidecar 重启

Rust 禁止负责：

* Paper 校验
* Markdown 解析或生成
* Vault 业务规则
* 搜索、排序或索引
* Trash、Branch、迁移判断
* 作者内容处理
* 任意 shell 执行
* 任意路径文件读写

若 Rust 中出现产品规则分支，立即停止并审查分层。

---

## 7. Tauri 权限必须逐项解释

修改 Tauri capability、plugin 权限或系统调用前，Agent 必须列出：

* 新增了什么权限
* 哪个用户动作需要它
* Vue 能否直接调用
* Rust 如何限制参数
* 最坏情况下该权限允许做什么
* 有没有权限更小的实现

Vue 不得获得以下通用能力：

```text
任意 shell
任意进程 spawn
任意文件读取
任意文件写入
任意路径 open
任意 URL open
```

权限配置修改必须单独展示 diff，不得藏在大量生成文件中。

---

## 8. JSONL 协议必须可人工阅读和手动模拟

每个 JSONL method 必须记录：

* method 名称
* params
* 成功结果
* 已知错误码
* 是否属于 mutation
* 是否允许重试
* 使用了什么 session token
* 对应的 Application Service 方法

至少提供一组真实但去标识化的请求和响应示例。

开发者应能通过终端手动向 sidecar 输入一条请求，并看懂返回结果。

禁止让协议只存在于 Rust 与 Python 实现代码中。

---

## 9. 所有错误都必须指出所属层级

错误反馈和诊断必须明确区分：

```text
Vue UI
Tauri / Rust host
JSONL transport
Python sidecar
Application Service
Python Core
Disk / external provider
```

禁止统一显示：

```text
Something went wrong
Operation failed
Unknown error
```

开发者日志必须帮助定位层级，同时不得记录：

* Paper 正文
* Summary
* Highlight 内容
* 用户绝对路径
* Vault 中的真实名称
* 未知 frontmatter 内容

---

## 10. 不允许用生成代码制造黑箱

使用官方脚手架可以接受，但 Agent 必须：

* 列出生成了哪些目录
* 标出哪些文件由项目长期维护
* 解释关键配置项
* 删除无关示例、欢迎页和默认资产
* 不得保留无法说明用途的配置
* 不得因为“模板默认存在”就保留权限或依赖

任何进入仓库的关键文件，都必须能在架构图或文件地图中找到职责。

---

## 11. 每个 Checkpoint 必须保持可回滚

每个 Checkpoint 遵循：

```text
一个明确目标
一组相关改动
一组验证证据
一个可独立提交的 diff
一个回滚点
```

结束时必须报告：

* 修改了什么
* 新增了什么
* 删除了什么
* 测试结果
* 手工 smoke 结果
* 已知限制
* 基线 commit，以及是否已获授权创建 checkpoint commit
* 回滚后什么功能仍然可用

本地 commit 仍需遵守 `docs/RULES.md` §7 的明确授权。等待授权时不得开始下一 Checkpoint；回滚说明必须列出撤销当前 diff 的精确范围。

---

## 12. Flet 在退场前必须始终可运行

在 Gate A 完成功能等价验收前：

* Flet 必须继续可启动
* Flet 必须调用同一个 Application Service
* Flet 是行为对照基线
* 不得删除 Flet 测试
* 不得删除 `flet` 依赖
* 不得修改作者数据格式来迁就 Vue 或 Tauri

新架构失败时，项目必须能退回 Flet，而不需要转换 Vault。

---

## 13. 真实 Vault 默认禁止进入开发实验

以下工作只允许使用 synthetic 或 copied Vault：

* JSONL 协议调试
* sidecar crash 测试
* migration 测试
* Rust open / reveal
* Tauri 目录选择
* 打包 smoke
* 外部修改冲突
* mutation response 丢失
* Trash 与永久删除

只有对应自动测试和 copied Vault smoke 通过后，才能执行明确列出的真实作者验收。

任何真实 Vault 操作前必须确认存在可恢复备份。

---

## 14. 工具链只使用稳定版并精确锁定

必须提交并维护：

```text
.node-version
package-lock.json
rust-toolchain.toml
Cargo.lock
.python-version
Python build lock
```

候选记录必须包含：

```text
Node / npm
Rust / Cargo
Python / PyInstaller
macOS
Xcode
target triple
```

禁止在生产开发环境中使用 beta：

* macOS
* Xcode
* Rust nightly
* Node 非稳定版本
* Tauri prerelease
* PyInstaller prerelease

实验性工具只能在隔离分支和隔离环境使用，不得成为 Road v0.4 的构建前提。

---

## 15. 功能迁移与视觉重建分别验收

### Gate A：Platform parity

只判断：

* 功能是否等价
* 错误是否清楚
* 数据是否安全
* 键盘路径是否可用
* Flet 与 Tauri 是否产生等价结果

### Gate B：Visual reconstruction

只在 Gate A 通过后判断：

* 信息层级
* 布局
* 字体
* 色彩
* 动效
* 视觉记忆点
* 创作者使用感受

禁止用新视觉的完成度掩盖功能缺陷。

禁止在功能故障中同时调整大规模视觉系统。

---

## 16. Agent 不得自行扩大技术范围

Road v0.4 未明确包含的内容一律不顺手加入：

* Vue Router
* Pinia
* TypeScript
* UI kit
* 图标库
* 网络 client
* localhost API
* WebSocket
* 数据库
* 文件监听器
* 自动更新
* 签名与公证
* App Sandbox
* DMG
* 跨平台构建
* 移动端

确有必要时，Agent 必须停止当前任务，先提交变更理由和影响分析。

---

## 17. 每个 Checkpoint 结束后必须交付理解摘要

摘要控制在一页内，至少包含：

### 现在发生了什么

用非术语语言描述本次结果。

### 新增概念

解释本次真正新增的概念，以及它在 keikeu 中的具体职责。

### 数据怎么走

给出一条从用户动作到磁盘结果的流程。

### 出错怎么查

列出第一检查点、日志位置和常见错误层级。

### 怎么撤销

给出回滚 commit 和恢复步骤。

### 下一步依赖什么

明确下一 Checkpoint 使用了本次哪个稳定接口。

---

## 18. 立即停止条件

出现以下任一情况，当前 Checkpoint 立即暂停：

* 开发者无法解释新增组件的职责
* Agent 无法说明某项依赖存在的必要性
* 同一业务规则同时出现在 Python 与 Rust/JavaScript
* Vue 获得任意 shell 或通用文件能力
* Core 开始依赖 Tauri、Rust、JSONL 或 Vue
* mutation 被自动重试
* 真实 Vault 在无备份状态下参与实验
* Flet 在 Gate A 前失去可运行状态
* 测试失败被标记为“与本次无关”后继续推进
* 为赶进度跳过概念说明、回滚点或 smoke
* 构建只能依赖未锁定或 beta 工具链
* Agent 用“以后再解释”处理当前黑箱

---

## 19. 完成标准

Road v0.4 的完成不只意味着 `.app` 可以启动。

开发者还必须能够：

1. 画出 Vue、Rust、JSONL、Python Service 和 Core 的关系。
2. 指出每类业务规则位于哪一层。
3. 手动识别一条 JSONL 请求和响应。
4. 判断一个故障属于 UI、宿主、传输、sidecar 还是 Core。
5. 说明 Flet 为什么可以安全删除。
6. 在不依赖 Agent 猜测的情况下完成基本启动、测试、调试和回滚。

做不到以上六点，项目仍然存在技术所有权缺口，Road 不应关闭。
