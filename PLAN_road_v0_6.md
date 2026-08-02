# Road v0.6 受邀 Alpha 实施计划

> 按照 `docs/RULES.md` §7 和项目本地 `keikeu-routine` 逐项执行；
> 复选框（`- [ ]`）用于跟踪实施状态。

**目标：** 交付一个私下分发的 macOS Apple Silicon 受邀 Alpha，使开发者能够
独立复现其 Developer ID 发布流程，并在 `n = 1` 时对二号用户 MVP Gate 作出结论。

**架构：** 保持已接受的 Vue/Tauri/JSONL/Python 运行时不变。使用锁定的本地工具链、
Tauri 现有的 macOS bundle 路径、Apple Keychain 身份和 Apple 原生公证工具。
Markdown 继续作为持久的权威与证据格式；DMG、原始日志、凭据和作者内容绝不进入 Git。

**技术栈：** Python 3.13 / pytest / PyInstaller 6.21.0、Node 22.23.1 / npm
10.9.8 / Vue / Vitest、Rust 1.88 / Tauri CLI 2.11.4 / Tauri crate 2.11.5，
以及 macOS `security`、`codesign`、`notarytool`、`stapler`、`spctl`、
`hdiutil`、`lipo`、`vtool` 和 `plutil`。

## 全局约束

- 与本计划配套、且已由开发者批准的设计书是
  `docs/design/road-v0-6-invited-alpha-design.md`。
  任务 0 的批准会冻结本计划及其中对外层 DMG 的窄范围澄清。
  如果本计划与该设计书、`docs/SPEC.md` 或 `docs/RULES.md` 冲突，
  必须停止实施并先解决冲突。
- Road v0.6 有五个顺序检查点（checkpoint）。每个检查点都需要审查当前证据，
  并由开发者明确判定通过。YOLO 不是 Gate。
- 已接受的本地 `.gitignore` 修改不进入任何暂存或提交。
  发现其他意外修改路径时，停止当前任务。
- 除非另有独立且明确的指示，否则不得推送（push）、更改远端、打标签、发布、
  删除分支或改写历史。
- 每次提交前都要获得明确授权、只暂存精确路径、检查 `git diff --cached`、
  确认没有秘密信息或作者内容被暂存、识别已配置的 `aic` 提供方，并遵循
  `docs/RULES.md` §7。不得退回使用 `git commit`。
- 不得增加依赖、CI 签名、更新器、App Store 打包、PKG、自定义 DMG 样式、
  遥测、云端行为或其他平台运行时。
- 不得修改真实 Vault 或使用未发表的作者内容。运行时冒烟测试使用专用的合成
  Vault；启动前要披露任何已选 Vault 或本地应用状态变化。
- 绝不把 Apple ID、密码、API 密钥、私钥材料、完整签名身份、
  Keychain 凭据配置名称、原始公证日志、本地绝对路径、稳定设备标识符、
  Vault 路径或测试者正文写入 Git。
- 候选包名称不可变：`keikeu-0.6.0-alpha.N-macos-arm64.dmg`。CP2 从
  `alpha.1` 开始，每次已经绑定哈希的重试都递增编号。CP3 使用已接受 CP2
  候选包之后的下一个未使用编号，通常是 `alpha.2`。候选包一旦绑定哈希
  或被分享，任何发生变化的产物都必须递增 `N`。
- 发布产物和原始证据保存在已忽略的本地目录 `build/road-v0-6/`，
  或开发者选择的其他非 Git 位置。
- 如果 `/Applications/keikeu.app` 已存在，安装前必须停止，并询问开发者
  应如何精确处置。绝不覆盖它。
- 不得给 shell 的 `HOME` 赋值。需要隔离时，创建任务专用临时目录，
  并仅通过待测子进程的启动命令把它传给该子进程。
- 签名、内部 bundle 校验、公证、Gatekeeper、架构、安装或运行时任一失败，
  都意味着按计划停止并重新构建。绝不移除 quarantine 元数据、
  绕过 Gatekeeper、使用临时（ad-hoc）签名，或以
  `codesign --deep --force` 修复。

---

## 任务 0：审查并冻结 Road 开始前的文档

**文件：**

- 修改：`AGENTS.md`
- 归档：把 `PLAN_revised.md` 的完整正文移至
  `docs/archive/road-v0-5/PLAN_revised.md`，并把根文件改为历史链接兼容入口
- 审查：
  `docs/design/road-v0-6-invited-alpha-design.md`
- 审查：
  `PLAN_road_v0_6.md`
- 修改：`docs/PROJECT.md`
- 修改：`docs/SPEC.md`
- 修改：`docs/archive/README.md`
- 修改：`docs/design/design.html`
- 修改：`docs/design/interaction.html`
- 修改：`scripts/check_docs.py`

- [ ] **步骤 1：核验规划工作树**

运行：

```bash
git status --short --branch
git branch --show-current
git diff -- .gitignore
git diff -- docs/PROJECT.md
sed -n '1,9999p' \
  docs/design/road-v0-6-invited-alpha-design.md
sed -n '1,9999p' \
  PLAN_road_v0_6.md
```

预期：分支为 `docs/road-v0-6-design`；`.gitignore` 是已点名的用户修改；
其余工作仅包括 Road v0.5 计划书归档与兼容入口、活跃引用切换、
Road v0.6 设计书、计划书、中文计划规则和 `PROJECT.md`。

- [ ] **步骤 2：审查已锁定的决策**

确认两份文档都包含以下内容：

- Road 结果是一个私下分发的 macOS Apple Silicon 受邀 Alpha，
  加一次二号用户 MVP Gate。
- 发布身份是 `0.6.0` / `app.keikeu.desktop` / macOS 15.7+ / 仅 arm64。
- 不支持 Intel Mac、Linux 和 watchOS；带日期的 iOS/iPadOS、Android、
  HarmonyOS 和 Windows 条目都是需要各自 Gate 的未来目标，不代表当前支持。
- 发布路径是本地 Developer ID 签名、手动 `notarytool`、staple、默认 DMG、
  Gatekeeper 和精确哈希证据。
- CP3 仅由开发者执行，Agent 零介入。
- CP4 把测试者设备问题推迟到准入 Gate，只修复观察到的 P0/P1；
  缺乏正向价值信号时判为产品 Gate 失败，而不是授权增加功能。

- [ ] **步骤 3：使 PROJECT 保持在当前行数预算内**

把其中现有的 Road v0.6 工作材料句替换为一句话，同时链接设计书和本计划，
并说明两者已经开发者批准，但 CP0 和发布工作均未开始。不得增加行数。

- [ ] **步骤 4：运行规划文档检查**

运行：

```bash
.venv/bin/python scripts/check_docs.py
git diff --check
```

如果以下两个已知的既有文档错误仍存在，就记录它们：
`docs/design/working-materials.md` 中一个因移动而失效的链接，以及已归档
Road v0.5 HTML 缺少归档标记。任何新错误都会阻止批准。

- [ ] **步骤 5：取得设计书与计划书批准**

开发者审查实际差异，然后提出修改要求，或明确批准实施计划以及已批准设计书中
对外层 DMG 的窄范围澄清。此批准不代表 CP0 通过，也不授权推送。

- [ ] **步骤 6：仅在另行明确授权后提交**

只暂存：

```bash
git add -- AGENTS.md \
  PLAN_revised.md \
  PLAN_road_v0_6.md \
  docs/PROJECT.md \
  docs/SPEC.md \
  docs/archive/README.md \
  docs/archive/road-v0-5/PLAN_revised.md \
  docs/design/design.html \
  docs/design/interaction.html \
  docs/design/road-v0-6-invited-alpha-design.md \
  scripts/check_docs.py
git diff --cached --check
git diff --cached
git status --short
```

开发者批准已暂存差异和获准的 `aic` 提供方后，创建一个意图为
`docs: prepare Road v0.6 execution baseline` 的聚焦 Road 交接提交。检查生成的提交。
保持 `.gitignore` 未暂存。不要推送。

---

## 任务 1：CP0 — 发布契约与身份就绪

**分支：** `docs/cp0-release-contract`

**文件：**

- 修改：`docs/design/working-materials.md`
- 修改：`docs/archive/road-v0-5/road-v0-5-planbook.html`
- 修改：`pyproject.toml`
- 修改：`src/keikeu_bridge/protocol.py`
- 修改：`frontend/package.json`
- 修改：`frontend/package-lock.json`
- 修改：`frontend/src-tauri/Cargo.toml`
- 修改：`frontend/src-tauri/Cargo.lock`
- 修改：`frontend/src-tauri/tauri.conf.json`
- 修改：`requirements-build.lock`
- 创建：`tests/test_release_identity.py`
- 修改：`docs/SPEC.md`
- 修改：`docs/RULES.md`
- 修改：`docs/PROJECT.md`
- 修改：`README.md`
- 修改：`README_EN.md`
- 创建：`docs/manual/forfresh/macos-developer-id-release.md`
- 修改：`docs/manual/README.md`
- 仅当 CP0 beta 条件成立时创建：
  `docs/architecture/decisions/0006-beta-toolchain-release-exception.md`
- 创建：`docs/acceptance/road-v0-6/README.md`
- 创建：
  `docs/acceptance/road-v0-6/cp0-release-contract/report.md`
- 修改：`docs/acceptance/README.md`

- [ ] **步骤 1：从已批准的规划提交开始**

运行：

```bash
git status --short --branch
git branch --show-current
git rev-parse HEAD
```

预期：只有已接受的 `.gitignore` 修改尚未提交，且 HEAD 是开发者批准的规划
提交。然后创建：

```bash
git switch -c docs/cp0-release-contract
```

- [ ] **步骤 2：修复已知文档基线**

只进行以下纠正：

- 在 `docs/design/working-materials.md` 中，把 HTML 链接指向
  `../archive/road-v0-5/road-v0-5-planbook.html`。
- 在 `docs/archive/road-v0-5/road-v0-5-planbook.html` 开头附近加入：

```html
<!-- ARCHIVE · READ ONLY · Road v0.5 frozen planbook -->
```

这是对紧邻此前那次归档移动的窄范围纠正。必须明确审查；
除此之外不要改写 Road v0.5 历史。

运行：

```bash
.venv/bin/python scripts/check_docs.py
git diff --check
```

预期：在 CP0 增加更多文档前，两条命令都通过。

- [ ] **步骤 3：增加一个会失败的发布身份测试**

创建 `tests/test_release_identity.py`，其中包含一个一致性测试：

```python
from __future__ import annotations

import json
import tomllib
from pathlib import Path

from keikeu_bridge.protocol import APP_VERSION


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_VERSION = "0.6.0"


def _toml(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def test_release_versions_are_0_6_0() -> None:
    package = json.loads(
        (ROOT / "frontend" / "package.json").read_text(encoding="utf-8")
    )
    package_lock = json.loads(
        (ROOT / "frontend" / "package-lock.json").read_text(encoding="utf-8")
    )
    cargo = _toml(ROOT / "frontend" / "src-tauri" / "Cargo.toml")
    cargo_lock = _toml(ROOT / "frontend" / "src-tauri" / "Cargo.lock")
    tauri = json.loads(
        (ROOT / "frontend" / "src-tauri" / "tauri.conf.json").read_text(
            encoding="utf-8"
        )
    )
    cargo_package = next(
        item
        for item in cargo_lock["package"]
        if item["name"] == "keikeu-desktop"
    )
    versions = {
        "python-project": _toml(ROOT / "pyproject.toml")["project"]["version"],
        "python-runtime": APP_VERSION,
        "npm-package": package["version"],
        "npm-lock-root": package_lock["version"],
        "npm-lock-package": package_lock["packages"][""]["version"],
        "cargo-package": cargo["package"]["version"],
        "cargo-lock-package": cargo_package["version"],
        "tauri-config": tauri["version"],
    }
    assert versions == {name: EXPECTED_VERSION for name in versions}
```

运行：

```bash
.venv/bin/python -m pytest tests/test_release_identity.py -q
```

预期：失败，因为仓库仍报告 `0.1.0`。测试收集或解析错误不是预期失败，
必须先修复。

- [ ] **步骤 4：应用已锁定的发布身份**

进行以下精确的版本修改：

- `pyproject.toml`：项目版本改为 `0.6.0`。
- `src/keikeu_bridge/protocol.py`：后备 `APP_VERSION` 改为 `0.6.0`。
- `frontend/package.json` 以及 `frontend/package-lock.json` 中仅根
  package 字段改为 `0.6.0`，通过以下命令生成：

```bash
npm --prefix frontend version 0.6.0 --no-git-tag-version
```

- `frontend/src-tauri/Cargo.toml` 以及 `Cargo.lock` 中仅本地
  `keikeu-desktop` package 条目改为 `0.6.0`。
- `frontend/src-tauri/tauri.conf.json`：版本改为 `0.6.0`；保持
  identifier `app.keikeu.desktop`、`minimumSystemVersion` `15.7`、target
  `app` 和现有 sidecar 路径；在 `bundle.macOS` 下明确增加
  `"hardenedRuntime": true`。
- `requirements-build.lock`：只修改第一条注释，说明它针对 Road v0.6
  在 Python 3.13.14 / macOS arm64 上解析。不要修改任何依赖版本。

检查 lockfile，确保没有依赖漂移：

```bash
git diff -- frontend/package-lock.json frontend/src-tauri/Cargo.lock \
  requirements-build.lock
cargo metadata --manifest-path frontend/src-tauri/Cargo.toml \
  --no-deps --format-version 1
```

- [ ] **步骤 5：刷新已忽略的可编辑安装元数据**

运行命令前，披露它会修改已忽略的本地 `.venv` 可编辑安装元数据。
如果后端尚不可用，PEP 517 构建隔离还可能创建临时构建环境并请求访问
软件包索引；发生这种情况时先取得网络授权。
它不得修改已追踪的依赖文件或 lockfile。

```bash
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/python -m pytest tests/test_release_identity.py -q
```

预期：聚焦测试通过，导入的运行时版本为 `0.6.0`。

- [ ] **步骤 6：更新当前权威文档，不扩大产品范围**

进行以下有界的文档修改：

- `docs/SPEC.md`：保留已接受的 Road v0.5 产品行为和作者控制；写明
  Road v0.6 当前结果、macOS arm64 15.7+ 发布契约、no-YOLO CP0–CP4
  Gates、受邀用户 MVP 标准和明确排除项。
- `docs/RULES.md`：增加持久保障，涵盖仅限 Keychain 的凭据、命名且不可变/
  已绑定哈希的产物、排除原始日志、quarantine 与 Gatekeeper 完整性、
  精确目标清理，以及禁止包含秘密信息的命令。Road 特定的 no-YOLO 规则
  不得进入全局规则。
- `docs/PROJECT.md`：把 CP0 标为当前阶段，把规划提交列为基线，
  并把 CP0 人工 Gate 标为下一步。通过替换或压缩现有行维持 200 行上限。
- `README.md` 和 `README_EN.md`：区分当前产品行为与 Road v0.6 分发状态，
  并公布锁定的平台矩阵：macOS Apple Silicon 为主力、不支持 Intel Mac、
  iOS/iPadOS 为 2026 年 8 月工程目标、Android 为 2026 年 Q4 目标、
  HarmonyOS 为 2026 年 Q4 可行性目标且须先在 NEXT-native 与
  Android-compatible 之间作出选择、Windows 为 2027 年目标，
  Linux/watchOS 暂无计划。每个非 macOS 日期都必须标为目标，
  而不是支持承诺。

不要修改运行时架构、交互或视觉设计文档。

- [ ] **步骤 7：创建发布手册的 CP0 章节**

创建 `docs/manual/forfresh/macos-developer-id-release.md`，包含以下章节：

1. 权威与范围；
2. 支持的主机与产物；
3. 停止条件；
4. 签名、公证、stapling 与 Gatekeeper 的区别；
5. 一次性的 Apple Developer 会员资格、Developer ID Application
   证书/私钥和 Keychain 凭据配置设置；
6. 凭据与证据的隐私边界；
7. 每个候选包的预检；
8. 为实际验证命令保留的 CP1 构建流程；
9. 为实际验证命令保留的 CP2 信任链流程；
10. 收件人式安装与冒烟测试；
11. 候选包编号、不可变文件名、staple 前后哈希记录，
    以及保留 quarantine 的私下测试者传输；
12. 故障排除与安全清理。

保留的 CP1/CP2 章节必须写明“尚未验证；不得用于发布”，
而不是包含占位命令。从 `docs/manual/README.md` 链接该手册。

一次性 profile 设置是已披露的持久 Keychain 修改，
只有人在明确批准后才能运行：

```bash
read -r "KEIKEU_NOTARY_PROFILE?Local Keychain profile name: "
xcrun notarytool store-credentials "$KEIKEU_NOTARY_PROFILE"
xcrun notarytool history \
  --keychain-profile "$KEIKEU_NOTARY_PROFILE"
unset KEIKEU_NOTARY_PROFILE
```

让 `notarytool` 安全地提示输入。不要把 Apple ID、Team ID 或密码放入
shell 历史、文件或 Git。

- [ ] **步骤 8：盘点实际发布工作站**

运行并总结，但不提交机器绝对路径：

```bash
read -r "KEIKEU_NOTARY_PROFILE?Local Keychain profile name: "
uname -m
sw_vers
xcodebuild -version
.venv/bin/python --version
node --version
npm --version
rustc --version --verbose
cargo --version
.venv/bin/python -m PyInstaller --version
npm --prefix frontend run tauri -- info
security find-identity -v -p codesigning
xcrun notarytool history \
  --keychain-profile "$KEIKEU_NOTARY_PROFILE"
unset KEIKEU_NOTARY_PROFILE
```

预期：

- 原生主机架构是 `arm64`；
- 有效的 `Developer ID Application` 身份具有匹配的私钥；
- Keychain profile 能查询公证历史；
- 已安装工具链匹配已锁定的项目工具链，或具有明确且已审查的例外。

如果发布 OS 或 Xcode 是 beta，立即停止。只有在开发者批准后，才创建
`docs/architecture/decisions/0006-beta-toolchain-release-exception.md`，
写明背景、精确例外、后果、到期/重新审查条件和生效状态。
不得静默继承旧的、仅用于开发的例外。

- [ ] **步骤 9：创建去标识化的 CP0 证据**

创建：

- `docs/acceptance/road-v0-6/README.md` 作为索引，只链接实际存在的记录；
- `docs/acceptance/road-v0-6/cp0-release-contract/report.md`，包含实际日期、
  源代码提交、发布身份、已脱敏的工具链摘要、已脱敏的 Developer ID/
  私钥/凭据配置就绪状态、四个概念的理解审查、执行过的命令、
  未覆盖项、风险和通过状态；
- 从 `docs/acceptance/README.md` 添加链接。

不要粘贴 `security` 输出、公证历史、账户数据或本地路径。

- [ ] **步骤 10：运行 CP0 检查**

运行：

```bash
.venv/bin/python -m pytest tests/test_release_identity.py \
  tests/test_bridge_protocol.py
.venv/bin/python -m pytest
.venv/bin/python -m compileall -q src
npm --prefix frontend test
npm --prefix frontend run build
cargo test --manifest-path frontend/src-tauri/Cargo.toml --locked
.venv/bin/python scripts/check_docs.py
git diff --check
```

记录实际结果，不得复制通过数量。发布身份、账户、私钥、凭据配置、
target、工具链、文档或测试任一失败，都会阻止 CP0。

- [ ] **步骤 11：人工 CP0 Gate 与提交**

开发者必须检查差异/证据，用自己的话解释签名、公证、stapling
和 Gatekeeper，并明确判定 CP0 通过。然后，在另行明确授权提交后，
只暂存 CP0 列出的文件、检查已暂存差异，并调用已批准的 `aic` 提供方，
意图为 `release: lock Road v0.6 contract`。检查提交；
保持 `.gitignore` 未暂存；不要推送。

---

## 任务 2：CP1 — 可重复构建的 arm64 候选包

**分支：** `build/cp1-arm64-candidate`

**文件：**

- 修改：`scripts/build_sidecar.py`
- 创建：`tests/test_build_sidecar.py`
- 修改：`docs/manual/forfresh/macos-developer-id-release.md`
- 修改：`docs/PROJECT.md`
- 创建：
  `docs/acceptance/road-v0-6/cp1-arm64-candidate/report.md`
- 修改：`docs/acceptance/road-v0-6/README.md`

- [ ] **步骤 1：从已通过的 CP0 提交创建分支**

运行：

```bash
git status --short --branch
git branch --show-current
git rev-parse HEAD
git switch -c build/cp1-arm64-candidate
```

切换前预期：只有 `.gitignore` 尚未提交，HEAD 是已检查的 CP0 提交，
且 CP0 已明确通过。

- [ ] **步骤 2：编写会失败的原生 arm64 构建守卫测试**

在 `scripts/build_sidecar.py` 中规划一个纯守卫，其约定如下：

```python
EXPECTED_RELEASE_TARGET = "aarch64-apple-darwin"


def _require_release_host(
    target: str,
    *,
    system: str | None = None,
    machine: str | None = None,
) -> None:
    actual_system = sys.platform if system is None else system
    actual_machine = platform.machine() if machine is None else machine
    if actual_system != "darwin":
        raise RuntimeError("the release sidecar must be built on macOS")
    if actual_machine != "arm64":
        raise RuntimeError("the release Python process must be native arm64")
    if target != EXPECTED_RELEASE_TARGET:
        raise RuntimeError(
            f"Rust host must be {EXPECTED_RELEASE_TARGET}, got {target}"
        )
```

`system=None` 读取 `sys.platform`；`machine=None` 读取
`platform.machine()`。当系统不是 Darwin、Python 进程不是原生 `arm64`，
或 Rust host 不是 `aarch64-apple-darwin` 时，它会在 PyInstaller 之前抛出
`RuntimeError`。

创建 `tests/test_build_sidecar.py`，包含：

- 一个原生 Darwin/arm64/正确 target 的通过用例；
- 参数化的 system、machine 和 target 失败用例；
- 一个 `main()` 测试：patch `_target_triple()` 和 `platform.machine()`
  来模拟 Rosetta，并让任何 PyInstaller `subprocess.run()` 调用导致测试失败。

运行：

```bash
.venv/bin/python -m pytest tests/test_build_sidecar.py -q
```

预期：失败，因为守卫尚不存在。

- [ ] **步骤 3：实现最小构建守卫**

导入标准库 `platform`，实现上述约定，并在 `_target_triple()` 之后、
构造或调用 PyInstaller 命令之前立即调用 `_require_release_host(target)`。
不要增加依赖、target 抽象、发布编排器或其他平台行为。

运行：

```bash
.venv/bin/python -m pytest tests/test_build_sidecar.py -q
```

预期：通过。

- [ ] **步骤 4：创建产物前运行源代码检查**

运行：

```bash
.venv/bin/python -m pytest
.venv/bin/python -m compileall -q src
npm --prefix frontend test
npm --prefix frontend run build
cargo test --manifest-path frontend/src-tauri/Cargo.toml --locked
.venv/bin/python scripts/check_docs.py
git diff --check
```

任一失败都会停止候选包构建。

- [ ] **步骤 5：构建前冻结精确的 CP1 源代码**

候选包必须来自一个提交，而不是未提交的代码差异。明确审查并授权提交后，
只暂存 `scripts/build_sidecar.py` 和 `tests/test_build_sidecar.py`，
检查已缓存差异，并使用已批准的 `aic` 提供方，意图为
`build: guard arm64 sidecar release`。

检查提交并运行：

```bash
git rev-parse HEAD
git status --short
```

预期：源代码冻结提交是 HEAD，且只有 `.gitignore` 尚未提交。
该提交不代表 CP1 通过，也不能作为 CP2 的起点。

- [ ] **步骤 6：构建全新 sidecar，并证明其运行时身份**

运行：

```bash
.venv/bin/python scripts/build_sidecar.py
file frontend/src-tauri/binaries/keikeu-sidecar-aarch64-apple-darwin
lipo -archs frontend/src-tauri/binaries/keikeu-sidecar-aarch64-apple-darwin
printf '%s\n' \
  '{"v":1,"id":1,"method":"system.hello","params":{}}' \
  | frontend/src-tauri/binaries/keikeu-sidecar-aarch64-apple-darwin
```

预期：仅 arm64；hello 报告应用版本 `0.6.0`、protocol `1`、
Paper schema `paper-v3` 和 index schema `index-v3`。
不得仅因文件名匹配就复用旧的已忽略 sidecar。

- [ ] **步骤 7：构建未签名/临时签名的 CP1 应用候选包**

首先确保没有 Apple 签名或公证变量会改变 CP1 的含义。
只检查变量名；绝不打印值：

```bash
for variable in \
  APPLE_SIGNING_IDENTITY APPLE_CERTIFICATE APPLE_CERTIFICATE_PASSWORD \
  APPLE_ID APPLE_PASSWORD APPLE_TEAM_ID APPLE_API_ISSUER \
  APPLE_API_KEY APPLE_API_KEY_PATH
do
  if printenv "$variable" >/dev/null
  then
    echo "$variable is set; stop before the CP1 build"
    exit 1
  fi
done
npm --prefix frontend run tauri:build -- \
  --target aarch64-apple-darwin \
  --bundles app
```

使用以下精确输出路径：

```bash
KEIKEU_APP=frontend/src-tauri/target/aarch64-apple-darwin/release/bundle/macos/keikeu.app
KEIKEU_MAIN="$KEIKEU_APP/Contents/MacOS/keikeu-desktop"
KEIKEU_SIDECAR="$KEIKEU_APP/Contents/MacOS/keikeu-sidecar"
```

CP1 不得设置 Developer ID 身份，也不得声称已公证。

- [ ] **步骤 8：核验架构、身份字段和最低 macOS 版本**

运行：

```bash
file "$KEIKEU_MAIN" "$KEIKEU_SIDECAR"
lipo -archs "$KEIKEU_MAIN"
lipo -archs "$KEIKEU_SIDECAR"
xcrun vtool -show-build "$KEIKEU_MAIN"
xcrun vtool -show-build "$KEIKEU_SIDECAR"
plutil -extract CFBundleShortVersionString raw -o - \
  "$KEIKEU_APP/Contents/Info.plist"
plutil -extract CFBundleIdentifier raw -o - \
  "$KEIKEU_APP/Contents/Info.plist"
plutil -extract LSMinimumSystemVersion raw -o - \
  "$KEIKEU_APP/Contents/Info.plist"
shasum -a 256 "$KEIKEU_MAIN" "$KEIKEU_SIDECAR"
```

预期：应用和 sidecar 仅为 arm64；版本为 `0.6.0`；identifier 为
`app.keikeu.desktop`；plist minimum 为 `15.7`；Mach-O minimum deployment
值不要求晚于 15.7 的版本。

- [ ] **步骤 9：执行隔离的已安装应用合成冒烟测试**

首先披露向 `/Applications` 复制以及隔离的本地应用状态边界。检查：

```bash
if [ -e /Applications/keikeu.app ]
then
  echo "/Applications/keikeu.app already exists; stop before copying"
  exit 1
fi
KEIKEU_TEST_HOME="$(mktemp -d /private/tmp/keikeu-cp1-home.XXXXXX)"
ditto "$KEIKEU_APP" /Applications/keikeu.app
```

如果应用已存在，立即停止。否则把精确的 CP1 应用复制到
`/Applications/keikeu.app`，不得覆盖，然后用以下命令启动子进程：

```bash
env HOME="$KEIKEU_TEST_HOME" \
  /Applications/keikeu.app/Contents/MacOS/keikeu-desktop
```

只使用合成文本：

1. 创建专用测试 Vault；
2. 创建并保存一个 Paper；
3. 打开其 Flashcard；
4. 退出；
5. 使用相同的、仅对子进程生效的 `HOME` 重新启动；
6. 找回 Paper。

记录观察结果。清理是另一个需要开发者确认的精确目标操作；
绝不删除既有应用或宽泛目录。

- [ ] **步骤 10：用已验证的构建路径替换手册中的 CP1 警告**

用刚刚实际运行的精确命令、预期输出、架构/版本/最低 OS
检查、合成冒烟测试、安全安装边界更新手册，并声明 CP1 不证明
Developer ID、公证、Gatekeeper 或收件人兼容性。

创建 CP1 报告，包含源代码提交、实际工具版本和命令结果、
main/sidecar 哈希、隔离冒烟测试结果、未覆盖项和风险。
从 Road 证据索引链接它。把 `docs/PROJECT.md` 更新到 CP1 Gate，
并保持在 200 行以内。

- [ ] **步骤 11：运行最终 CP1 文档与回归检查**

运行：

```bash
.venv/bin/python -m pytest
.venv/bin/python -m compileall -q src
npm --prefix frontend test
npm --prefix frontend run build
cargo test --manifest-path frontend/src-tauri/Cargo.toml --locked
.venv/bin/python scripts/check_docs.py
git diff --check
```

如果源代码、测试、构建配置或产物输入在源代码冻结提交后发生变化，
立即停止：取得新源代码冻结提交的批准，并重复步骤 6–9。
只涉及文档的证据修改无需重建已经记录哈希的 CP1 产物。

- [ ] **步骤 12：人工 CP1 Gate 与提交**

开发者检查当前证据并明确判定 CP1 通过。在另行提交授权下，只暂存 CP1
手册、PROJECT 和去标识化证据路径；源代码/测试文件对已位于经过审查的
源代码冻结提交中。绝不暂存 sidecar、应用 bundle、构建输出、日志、
`.venv`、临时状态或 `.gitignore`。使用已批准的 `aic` 提供方，
意图为 `docs: record repeatable arm64 candidate`；检查提交，不要推送。

---

## 任务 3：CP2 — Developer ID 信任链

**分支：** `build/cp2-developer-id-trust`

**文件：**

- 修改：`docs/manual/forfresh/macos-developer-id-release.md`
- 修改：`docs/PROJECT.md`
- 创建：
  `docs/acceptance/road-v0-6/cp2-developer-id-trust/report.md`
- 修改：`docs/acceptance/road-v0-6/README.md`

CP2 不计划修改源代码、依赖、entitlement 或 bundle 配置。
一旦发现需要此类修改，就停止该检查点，返回进行聚焦修复并生成全新候选包。

- [ ] **步骤 1：从已通过的 CP1 提交创建分支**

核验状态、HEAD、CP1 明确通过，且只有 `.gitignore` 尚未提交。然后运行：

```bash
git switch -c build/cp2-developer-id-trust
```

- [ ] **步骤 2：准备不可变的 CP2 候选包工作区**

从仓库根目录运行：

```bash
read -r "KEIKEU_ALPHA_NUMBER?Unused candidate number (digits only): "
case "$KEIKEU_ALPHA_NUMBER" in
  ""|*[!0-9]*|0*)
    echo "candidate number must be a positive integer without a leading zero"
    exit 1
    ;;
esac
KEIKEU_CANDIDATE_ID="alpha.$KEIKEU_ALPHA_NUMBER"
KEIKEU_RELEASE_DIR="build/road-v0-6/$KEIKEU_CANDIDATE_ID"
KEIKEU_LOCAL_EVIDENCE="$KEIKEU_RELEASE_DIR/local-evidence"
KEIKEU_DMG="$KEIKEU_RELEASE_DIR/keikeu-0.6.0-$KEIKEU_CANDIDATE_ID-macos-arm64.dmg"
if [ -e "$KEIKEU_RELEASE_DIR" ]
then
  echo "$KEIKEU_CANDIDATE_ID already exists; stop instead of overwriting it"
  exit 1
fi
mkdir -p "$KEIKEU_LOCAL_EVIDENCE"
git rev-parse HEAD
git status --short
```

预期：CP2 第一次尝试使用 `1`；已退役/已绑定哈希的重试使用下一个未使用编号。
该目录和不可变候选包名称此前不存在，状态除已接受的 `.gitignore` 行外
没有其他修改。

- [ ] **步骤 3：选择本地身份，不暴露凭据**

运行：

```bash
read -r "KEIKEU_NOTARY_PROFILE?Local Keychain profile name: "
security find-identity -v -p codesigning
xcrun notarytool history \
  --keychain-profile "$KEIKEU_NOTARY_PROFILE"
```

在本地选择有效的 Developer ID Application SHA-1。如果身份重复，
使用精确 SHA-1，而不是有歧义的名称。仅在当前 Terminal 中导出：

```bash
read -r "APPLE_SIGNING_IDENTITY?Developer ID Application SHA-1: "
export APPLE_SIGNING_IDENTITY
```

不要记录该值。

- [ ] **步骤 4：防止意外触发 Tauri 自动公证**

检查变量名，不打印值：

```bash
for variable in \
  APPLE_CERTIFICATE APPLE_CERTIFICATE_PASSWORD \
  APPLE_ID APPLE_PASSWORD APPLE_TEAM_ID APPLE_API_ISSUER \
  APPLE_API_KEY APPLE_API_KEY_PATH
do
  if printenv "$variable" >/dev/null
  then
    echo "$variable is set; stop before build"
    exit 1
  fi
done
```

使用 Keychain profile 的手动 `notarytool` 是唯一公证路径。

- [ ] **步骤 5：构建已签名应用与默认 DMG**

确认构建来自干净且已通过的 CP1 提交，然后运行：

```bash
git rev-parse HEAD
git status --short
.venv/bin/python -m pytest
.venv/bin/python -m compileall -q src
npm --prefix frontend test
npm --prefix frontend run build
cargo test --manifest-path frontend/src-tauri/Cargo.toml --locked
.venv/bin/python scripts/check_docs.py
git diff --check
.venv/bin/python scripts/build_sidecar.py
```

除 `.gitignore` 外的任何已追踪修改，或任何检查失败，都会停止构建。
然后运行：

```bash
npm --prefix frontend run tauri:build -- \
  --target aarch64-apple-darwin \
  --bundles app,dmg \
  --verbose
```

使用：

```bash
KEIKEU_TAURI_APP=frontend/src-tauri/target/aarch64-apple-darwin/release/bundle/macos/keikeu.app
KEIKEU_TAURI_DMG=frontend/src-tauri/target/aarch64-apple-darwin/release/bundle/dmg/keikeu_0.6.0_aarch64.dmg
test -d "$KEIKEU_TAURI_APP"
test -f "$KEIKEU_TAURI_DMG"
cp -p -n "$KEIKEU_TAURI_DMG" "$KEIKEU_DMG"
test -f "$KEIKEU_DMG"
```

- [ ] **步骤 6：确保外层 DMG 在首次计算哈希前已签名**

首先核验：

```bash
codesign --verify --verbose=4 "$KEIKEU_DMG"
```

当且仅当 Tauri 留下的外层 DMG 未签名时，才把这次 DMG 签名作为
候选包创建的一部分执行一次：

```bash
codesign --force \
  --sign "$APPLE_SIGNING_IDENTITY" \
  --timestamp \
  "$KEIKEU_DMG"
```

不要手动签名内部内容。应用/main/sidecar 的任一签名失败都意味着退役当前候选包，
并用下一个未使用编号修复/重建；不得原地修复。

- [ ] **步骤 7：核验提交前的完整产物**

运行：

```bash
codesign --verify --verbose=4 "$KEIKEU_DMG"
hdiutil verify "$KEIKEU_DMG"
KEIKEU_PRE_MOUNT_DIR="$(
  mktemp -d /private/tmp/keikeu-cp2-precheck.XXXXXX
)"
hdiutil attach -readonly -nobrowse \
  -mountpoint "$KEIKEU_PRE_MOUNT_DIR" \
  "$KEIKEU_DMG"
KEIKEU_PACKAGED_APP="$KEIKEU_PRE_MOUNT_DIR/keikeu.app"
KEIKEU_PACKAGED_MAIN="$KEIKEU_PACKAGED_APP/Contents/MacOS/keikeu-desktop"
KEIKEU_PACKAGED_SIDECAR="$KEIKEU_PACKAGED_APP/Contents/MacOS/keikeu-sidecar"
codesign --verify --strict --verbose=4 "$KEIKEU_PACKAGED_MAIN"
codesign --verify --strict --verbose=4 "$KEIKEU_PACKAGED_SIDECAR"
codesign --verify --deep --strict --verbose=4 "$KEIKEU_PACKAGED_APP"
codesign -d --verbose=4 "$KEIKEU_PACKAGED_MAIN" \
  > "$KEIKEU_LOCAL_EVIDENCE/codesign-main.txt" 2>&1
codesign -d --verbose=4 "$KEIKEU_PACKAGED_SIDECAR" \
  > "$KEIKEU_LOCAL_EVIDENCE/codesign-sidecar.txt" 2>&1
codesign -d --verbose=4 "$KEIKEU_PACKAGED_APP" \
  > "$KEIKEU_LOCAL_EVIDENCE/codesign-app.txt" 2>&1
codesign -d --verbose=4 "$KEIKEU_DMG" \
  > "$KEIKEU_LOCAL_EVIDENCE/codesign-dmg.txt" 2>&1
codesign --display --entitlements - --xml "$KEIKEU_PACKAGED_MAIN" \
  > "$KEIKEU_LOCAL_EVIDENCE/entitlements-main.plist" \
  2> "$KEIKEU_LOCAL_EVIDENCE/entitlements-main.stderr.txt"
codesign --display --entitlements - --xml "$KEIKEU_PACKAGED_SIDECAR" \
  > "$KEIKEU_LOCAL_EVIDENCE/entitlements-sidecar.plist" \
  2> "$KEIKEU_LOCAL_EVIDENCE/entitlements-sidecar.stderr.txt"
lipo -archs "$KEIKEU_PACKAGED_MAIN"
lipo -archs "$KEIKEU_PACKAGED_SIDECAR"
xcrun vtool -show-build "$KEIKEU_PACKAGED_MAIN"
xcrun vtool -show-build "$KEIKEU_PACKAGED_SIDECAR"
hdiutil detach "$KEIKEU_PRE_MOUNT_DIR"
rmdir "$KEIKEU_PRE_MOUNT_DIR"
```

这些检查针对将被计算哈希并提交的精确 DMG 内部应用，而不是独立的 Tauri
应用目录。即便只读诊断失败，也要在停止前卸载，并仅移除精确的挂载目录。

手动确认：

- 应用、主可执行文件、sidecar 和 DMG 都使用 Developer ID Application；
- 应用/主程序/sidecar 共用相同 TeamIdentifier；
- 可执行代码报告安全时间戳和 `runtime` 标志；
- 两个可执行文件都没有 `get-task-allow`；
- main 和 sidecar 仅为 arm64；
- 磁盘映像核验成功。

`--deep` 仅用于核验，绝不能与强制签名结合使用。

- [ ] **步骤 8：绑定不可变的 staple 前哈希**

运行：

```bash
shasum -a 256 "$KEIKEU_DMG" \
  > "$KEIKEU_LOCAL_EVIDENCE/dmg-pre-staple.sha256"
```

检查该文件，然后在提交前不得修改 DMG。

- [ ] **步骤 9：提交一次，并审查同一次公证**

运行：

```bash
xcrun notarytool submit "$KEIKEU_DMG" \
  --keychain-profile "$KEIKEU_NOTARY_PROFILE" \
  --wait \
  --output-format json \
  > "$KEIKEU_LOCAL_EVIDENCE/notary-submit.json"
KEIKEU_SUBMISSION_ID="$(
  plutil -extract id raw -o - \
    "$KEIKEU_LOCAL_EVIDENCE/notary-submit.json"
)"
xcrun notarytool info "$KEIKEU_SUBMISSION_ID" \
  --keychain-profile "$KEIKEU_NOTARY_PROFILE" \
  --output-format json \
  > "$KEIKEU_LOCAL_EVIDENCE/notary-info.json"
xcrun notarytool log "$KEIKEU_SUBMISSION_ID" \
  --keychain-profile "$KEIKEU_NOTARY_PROFILE" \
  "$KEIKEU_LOCAL_EVIDENCE/notary-log.json"
```

预期：状态精确为 `Accepted`；日志中的 SHA-256 与 staple 前 DMG 匹配；
没有错误；每个警告都已明确审查并确认不阻塞。如果 submission ID
已存在，就查询它，而不是再次上传。

- [ ] **步骤 10：证明已提交字节未变化并执行 staple**

运行：

```bash
shasum -a 256 -c "$KEIKEU_LOCAL_EVIDENCE/dmg-pre-staple.sha256"
xcrun stapler staple -v "$KEIKEU_DMG"
xcrun stapler validate -v "$KEIKEU_DMG"
```

如果 stapling 在字节已变化后失败，退役当前候选包。
否则遵循设计书中的有界重试规则。

- [ ] **步骤 11：重新核验并计算最终哈希**

运行：

```bash
hdiutil verify "$KEIKEU_DMG"
codesign --verify --verbose=4 "$KEIKEU_DMG"
xcrun stapler validate -v "$KEIKEU_DMG"
spctl --assess --type open \
  --context context:primary-signature \
  --verbose=4 "$KEIKEU_DMG"
shasum -a 256 "$KEIKEU_DMG" \
  > "$KEIKEU_LOCAL_EVIDENCE/dmg-final.sha256"
```

预期 Gatekeeper 文本明确标识已公证的 Developer ID 结果，
而不只是退出码为零。最终哈希通常与 staple 前哈希不同。

- [ ] **步骤 12：以只读方式挂载并评估其中应用**

运行：

```bash
KEIKEU_MOUNT_DIR="$(mktemp -d /private/tmp/keikeu-cp2-mount.XXXXXX)"
hdiutil attach -readonly -nobrowse \
  -mountpoint "$KEIKEU_MOUNT_DIR" \
  "$KEIKEU_DMG"
KEIKEU_FINAL_APP="$KEIKEU_MOUNT_DIR/keikeu.app"
KEIKEU_FINAL_MAIN="$KEIKEU_FINAL_APP/Contents/MacOS/keikeu-desktop"
KEIKEU_FINAL_SIDECAR="$KEIKEU_FINAL_APP/Contents/MacOS/keikeu-sidecar"
spctl --assess --type execute --verbose=4 \
  "$KEIKEU_FINAL_APP"
codesign --verify --strict --verbose=4 "$KEIKEU_FINAL_MAIN"
codesign --verify --strict --verbose=4 "$KEIKEU_FINAL_SIDECAR"
codesign --verify --deep --strict --verbose=4 \
  "$KEIKEU_FINAL_APP"
lipo -archs "$KEIKEU_FINAL_MAIN"
lipo -archs "$KEIKEU_FINAL_SIDECAR"
xcrun vtool -show-build "$KEIKEU_FINAL_MAIN"
xcrun vtool -show-build "$KEIKEU_FINAL_SIDECAR"
hdiutil detach "$KEIKEU_MOUNT_DIR"
rmdir "$KEIKEU_MOUNT_DIR"
```

预期：被接受，来源是已公证的 Developer ID，且最终 DMG 的 main、
sidecar、应用签名、arm64 架构和最低 OS 证据仍通过。
即使诊断失败，也要在停止前卸载精确挂载点。

- [ ] **步骤 13：在本地安装并运行最终哈希候选包**

使用正常的 Finder DMG 到 Applications 复制路径；不得使用 `sudo`、覆盖、
右键“打开”或移除 quarantine。复制或启动前：

```bash
if [ -e /Applications/keikeu.app ]
then
  echo "/Applications/keikeu.app already exists; stop before copying"
  exit 1
fi
KEIKEU_TEST_HOME="$(mktemp -d /private/tmp/keikeu-cp2-home.XXXXXX)"
```

通过 Finder 复制后，只用隔离的主目录启动已安装子进程：

```bash
env HOME="$KEIKEU_TEST_HOME" \
  /Applications/keikeu.app/Contents/MacOS/keikeu-desktop
```

这样可防止读取现有 `~/.keikeu_config.json`，或写入真实
`~/.keikeu_state.json`。使用专用合成 Vault 并执行：

1. 首次启动；
2. 创建/打开/保存 Paper；
3. 打开 Flashcard；
4. 移交外部编辑器；
5. 退出并重新启动；
6. 找回 Paper。

记录精确的最终哈希和实际观察。Gatekeeper 评估不能代替此运行时冒烟测试。

- [ ] **步骤 14：完成已验证手册和 CP2 记录**

用精确的成功路径替换手册中的 CP2 警告：预检、一次已校验的数字候选包输入、
从 `alpha.N` 派生的路径、身份选择、构建、有条件的外层 DMG 签名、提交前检查、
staple 前哈希、单次提交、日志审查、staple、最终核验、staple 后哈希、安装、
隔离冒烟测试、失败恢复、脱敏、保留 quarantine 的私下传输，以及精确目标清理。
同一份手册必须接受
`1` 作为 CP2 首个候选包编号，并接受下一个未使用编号用于 CP3；
绝不能硬编码 `alpha.1`。
它还必须包含 CP3 步骤 4 中精确的 arm64、macOS 15.7.x、最终哈希，
以及仅对子进程生效的 `HOME` 兼容性命令，确保演练绝不因缺少命令而依赖
本计划或 Agent。

创建 CP2 报告，包含去标识化源代码提交、候选包名称、staple 前后哈希、
submission-ID 绑定、已脱敏身份一致性、Accepted/日志审查、staple、
Gatekeeper、磁盘映像、架构和运行时结果。
从 Road 索引链接它。原始文件保留在本地。把 PROJECT 更新到 CP2 Gate。

- [ ] **步骤 15：人工 CP2 Gate 与提交**

开发者审查本地原始证据和适合进入 Git 的摘要，确认没有发生绕过或内部补丁，
并明确判定 CP2 通过。运行：

```bash
.venv/bin/python scripts/check_docs.py
git diff --check
```

两项都必须通过。然后清除本地发布会话值：

```bash
unset APPLE_SIGNING_IDENTITY
unset KEIKEU_NOTARY_PROFILE
unset KEIKEU_SUBMISSION_ID
```

另行授权后，只提交手册、PROJECT、索引和报告，使用已批准的 `aic`
提供方，意图为 `release: prove Developer ID trust chain`。
绝不暂存构建输出、DMG、原始证据、秘密信息或 `.gitignore`。
检查提交；不要推送。

---

## 任务 4：CP3 — 开发者独立发布演练

**分支：** `docs/cp3-release-rehearsal`

**文件：**

- 仅当独立执行失败时修改：
  `docs/manual/forfresh/macos-developer-id-release.md`
- 修改：`docs/PROJECT.md`
- 创建：
  `docs/acceptance/road-v0-6/cp3-release-rehearsal/report.md`
- 修改：`docs/acceptance/road-v0-6/README.md`

- [ ] **步骤 1：从已通过的 CP2 提交创建分支**

核验只有 `.gitignore` 尚未提交、CP2 已明确通过，且 CP2 手册已提交。
然后：

```bash
git switch -c docs/cp3-release-rehearsal
```

- [ ] **步骤 2：冻结手册与候选包身份**

独立尝试使用：

- 分支开始时精确的 CP2 提交；
- 已提交的手册，尝试期间保持不变；
- 已接受 CP2 候选包后的下一个未使用编号，通常为 `2`，通过手册中
  已校验的数字输入；
- 一个全新派生目录和不可变的
  `keikeu-0.6.0-alpha.N-macos-arm64.dmg` 名称；
- 除已接受的 `.gitignore` 修改外，没有未提交的已追踪内容。

开发者在开始前记录源代码提交。执行期间不得提供任何 Agent 生成的命令、
纠正或先决条件。

- [ ] **步骤 3：在新的 Terminal 中完整执行手册**

开发者打开新的 Terminal，独立执行手册中从身份检查到最终 staple 后哈希及
已安装应用合成冒烟测试的每一步。
开发者要把每条核验命令映射到其结论：

- 源代码/版本/target；
- 架构/最低 OS；
- 身份/签名/hardened runtime/时间戳；
- 磁盘映像完整性；
- 公证状态和日志；
- staple；
- Gatekeeper；
- 运行时和重新启动。

如果开发者需要 Agent 帮助或未记录在文档中的命令，CP3 失败。
按要求退役当前候选包并结束该次尝试。用聚焦差异修复手册，然后运行：

```bash
.venv/bin/python scripts/check_docs.py
git diff --check
```

然后取得明确审查和提交授权，并用已批准的 `aic` 提供方提交纠正。
只有在修正后的手册已提交、状态再次除 `.gitignore` 外没有已追踪
修改后，开发者才能冻结新的源代码提交、选择下一个未使用候选包编号、
打开另一个新 Terminal，并重新开始完整的零介入尝试。

- [ ] **步骤 4：在真实 macOS 15.7 上运行精确的最终哈希 DMG**

把独立生成的最终哈希 DMG 传输到运行 macOS 15.7.x 的真实 Apple Silicon
主机。在该主机上运行：

```bash
read -r "KEIKEU_RECEIVED_DMG?Exact local DMG path: "
uname -m
sw_vers -productVersion
shasum -a 256 "$KEIKEU_RECEIVED_DMG"
if [ -e /Applications/keikeu.app ]
then
  echo "/Applications/keikeu.app already exists; stop before copying"
  exit 1
fi
KEIKEU_TEST_HOME="$(mktemp -d /private/tmp/keikeu-cp3-home.XXXXXX)"
```

预期：`arm64`、以 `15.7` 开头的 OS 版本，以及独立记录的精确最终哈希。
正常安装 DMG，不覆盖、不绕过 Gatekeeper，然后仅启动已安装的子进程：

```bash
env HOME="$KEIKEU_TEST_HOME" \
  /Applications/keikeu.app/Contents/MacOS/keikeu-desktop
```

这会隔离现有已选 Vault 和本地状态。使用相同的、仅对子进程生效的
`HOME` 完成合成 Paper／保存／Flashcard／外部编辑器／退出／重新启动／找回流程。

如果没有真实 macOS 15.7 主机，CP3 暂停。旧证据、更新的 OS 或不同 DMG
都不能替代。修改支持下限需要另行作出设计决策并批准。

- [ ] **步骤 5：创建 CP3 证据记录**

记录：

- 精确源代码提交和最终候选包名称/哈希；
- 实际主机 OS/架构，不含设备标识符；
- Agent 零介入；
- 完整手册执行结果；
- 从命令到结论的理解审查；
- 精确哈希的 macOS 15.7 安装/核心流程/重新启动结果；
- 未覆盖项、风险和通过状态。

不要提交原始公证日志、本地路径、包含账户数据的截图或 DMG。
从 Road 索引链接报告，并把 PROJECT 更新到 CP3 人工 Gate。

- [ ] **步骤 6：人工 CP3 Gate 与提交**

开发者明确确认已独立复现并理解概念，审查当前证据，并判定 CP3 通过。运行：

```bash
.venv/bin/python scripts/check_docs.py
git diff --check
```

两项都必须通过。另行授权后，使用已批准的 `aic` 提供方，只提交报告、
证据索引和 PROJECT，意图为
`docs: record independent release rehearsal`。任何手册纠正必须已位于
成功重跑所用的干净源代码提交中。检查提交；不要推送。

---

## 任务 5：CP4 — 受邀 Alpha 与二号用户 MVP Gate

**分支：** `test/cp4-invited-alpha-gate`

**文件：**

- 创建：`docs/manual/invited-alpha-test-guide.md`
- 修改：`docs/manual/README.md`
- 修改：`docs/PROJECT.md`
- 创建：
  `docs/acceptance/road-v0-6/cp4-invited-alpha-gate/report.md`
- 修改：`docs/acceptance/road-v0-6/README.md`
- 仅通过后修改：`README.md`
- 仅通过后修改：`README_EN.md`

- [ ] **步骤 1：从已通过的 CP3 提交创建分支**

核验只有 `.gitignore` 尚未提交、CP3 已明确通过，且已接受的 CP3
产物/哈希不可变。然后：

```bash
git switch -c test/cp4-invited-alpha-gate
```

- [ ] **步骤 2：收集此前推迟的测试者准入事实**

现在，而不是更早，确认：

- Apple Silicon Mac；
- macOS 15.7 或更高版本；
- 设备是否由学校/公司管理；
- 设备策略允许 Developer ID DMG；
- 设备策略允许移交外部编辑器；
- 测试者能创建专用测试 Vault，并使用一条由其自愿选择的真实灵感。

如果任何边界未知或受阻，CP4 不启动。只记录支持/受阻结论，
不记录硬件序列号、账户、组织或设备标识符。

- [ ] **步骤 3：编写单页测试者指南**

创建 `docs/manual/invited-alpha-test-guide.md`，只包含：

1. 私下 Alpha 范围和 macOS Apple Silicon 15.7+ 边界；
2. 隐私：专用测试 Vault、自愿内容，不收集正文或路径；
3. 停止条件以及如何停止；
4. 用于比对的精确最终 SHA-256；
5. 正常的 DMG 到 Applications 安装与 Gatekeeper 启动；
6. 唯一任务：使用一条真实灵感帮助自己开始写作；
7. 不做功能介绍；
8. 将观察的内容：完成情况、犹豫点、介入次数和去标识化反馈；
9. 两个任务后价值问题。

从手册索引链接它。不要包含主持人的点击指示。

- [ ] **步骤 4：私下传输精确的 CP3 产物**

使用一个已经可用、由用户选择的私下传输渠道。本计划不增加或背书新服务；
可观察 Gate 是接收文件保留了 quarantine 元数据。

在测试者 Mac 上比较：

```bash
read -r "KEIKEU_RECEIVED_DMG?Exact local DMG path: "
shasum -a 256 "$KEIKEU_RECEIVED_DMG"
xattr -p com.apple.quarantine "$KEIKEU_RECEIVED_DMG"
```

主持人可以通过拖放协助设置本地路径变量，但不得记录它。
哈希必须匹配 CP3，且 quarantine 元数据必须存在。
绝不移除该属性或绕过 Gatekeeper。

- [ ] **步骤 5：执行无引导安装和核心任务**

在不做功能介绍的情况下观察：

1. 通过 Finder 正常拖到 Applications；
2. 首次 Gatekeeper 启动；
3. 创建专用测试 Vault；
4. 整理并保存 Paper；
5. 打开 Flashcard；
6. 测试者独立选择外部编辑器；
7. 撰写约十分钟正文；
8. 退出并重新启动；
9. 找回 Paper。

主持人可以解释隐私、任务和停止条件。每条 keikeu 点击路径指示都计为一次介入。
绝不记录屏幕内容、正文、灵感、关系、Vault 路径、账户或设备 ID。
主持人对常见核心点击路径的任何救援都视为 P1，直到修复并重新测试。

- [ ] **步骤 6：提出非引导式价值问题**

任务完成后，提出一个包含两个子问的非引导式问题：

1. keikeu 是否让开始写作变得更容易？具体发生了什么变化？
2. 你会选择再用它处理另一条灵感吗？为什么？

确认不含敏感内容后，才记录简短、去标识化的原话。

- [ ] **步骤 7：严格应用 Gate 决策**

- **通过：** 核心安全流程完成、没有未解决的 P0/P1，且至少存在一个具体的
  正向价值信号。
- **P0：** 立即停止写入和重复实验，保留测试 Vault 和当前产物，
  不再修改；只记录去标识化步骤，并保持 CP4 失败/开放。
- **P1：** 记录最短复现路径和频率；在常见主流程修复并重新核验前，
  保持 CP4 失败/开放。
- **P0/P1 纠正：** 明确批准后，只在以该问题命名的聚焦分支上修复
  观察到的问题；递增候选包编号，对变化后的产物重跑 CP1、CP2 和
  CP3 操作 Gate，再重新测试 CP4。不要创建重复检查点记录。
- **P2/P3：** 记录一个去标识化的下一 Road 候选项；现在不要加入。
- **流程成功但没有正向价值信号：** MVP Gate 失败；这不会自动成为 P1，
  也不授权任何功能范围；工作暂停，另行作出产品决策，判断此前考虑的
  Road v0.5.5 纠正范围是否合理。
- **设备不受支持或被策略阻止：** CP4 从未开始；等待符合要求的测试者，
  不得削弱平台或安全边界。

在 `n = 1` 时通过只构成受邀用户 MVP 证据，不是市场验证或产品市场契合。

- [ ] **步骤 8：分别记录工程与产品结论**

创建 CP4 报告，包含：

- 精确产物名称/哈希和受支持设备/策略结论；
- quarantine、安装、Gatekeeper、启动/重新启动结果；
- 每项核心任务的完成状态；
- 介入次数和去标识化犹豫点；
- P0/P1 状态；
- 去标识化价值回答；
- 单独的工程发布结论；
- 单独的 `n = 1` 产品 Gate 结论；
- 未覆盖项和风险。

从 Road 索引链接它。仅通过时，把两份 README 从“Road v0.6 目标”
更新为精确的已接受受邀 Alpha 状态，不得声称公开或跨平台可用。
把 PROJECT 更新到 CP4 人工 Gate。

- [ ] **步骤 9：人工 CP4 Gate 与提交**

开发者审查当前去标识化证据，并明确判定通过、失败，或记录 CP4 无法开始。
运行：

```bash
.venv/bin/python scripts/check_docs.py
git diff --check
```

两项都必须通过。

- 通过时，且仅在另行授权提交后，暂存测试者指南、索引、报告、
  PROJECT 和仅通过时才有的 README 修改。使用已批准的 `aic` 提供方，
  意图为
  `test: record invited alpha MVP gate`.
- 如果结果是负价值、P0/P1 或准入受阻，另行明确授权后，可以只提交
  已存在且去标识化的指南/索引/报告/PROJECT 路径，意图为
  `test: record failed invited alpha MVP gate`。该提交不代表 CP4 通过，
  也不能作为收尾的起点。

检查任何生成的提交。绝不暂存 DMG、测试者内容、本地日志、标识符或
`.gitignore`；不要推送。

---

## 任务 6：独立的 Road v0.6 收尾

**分支：** `docs/road-v0-6-closeout`

**准入条件：** CP4 已明确通过，且其聚焦提交已检查。

**文件：**

- 创建：`docs/archive/snapshots/road-v0-6.html`
- 修改：`docs/archive/README.md`
- 修改：`docs/PROJECT.md`

- [ ] **步骤 1：创建独立的收尾分支**

运行：

```bash
git status --short --branch
git rev-parse HEAD
git switch -c docs/road-v0-6-closeout
```

预期：HEAD 是已通过的 CP4 提交，且只有 `.gitignore` 尚未提交。

- [ ] **步骤 2：创建只读快照**

创建 `docs/archive/snapshots/road-v0-6.html`，包含醒目的
`ARCHIVE · READ ONLY` 标记，以及以下内容的精简记录：

- CP0–CP4 分支和提交；
- 聚焦范围和实质修改；
- 实际检查和人工 Gate 结果；
- 不含本地路径的产物身份/哈希结论；
- 手册演练和 macOS 15.7 结论；
- 二号用户工程与产品结论；
- 未覆盖项和剩余风险；
- 明确声明这不意味着标签、推送、公开发布或非 macOS 支持。

不要嵌入完整 diff、原始日志、作者/测试者内容、凭据或敏感路径。

- [ ] **步骤 3：更新归档导航和当前状态**

从 `docs/archive/README.md` 链接快照。更新 `docs/PROJECT.md`，
说明 Road v0.6 实际接受或暂停结果，以及开发者的下一项决策。
保持 PROJECT 不超过 200 行。

- [ ] **步骤 4：运行收尾检查**

运行：

```bash
.venv/bin/python scripts/check_docs.py
git diff --check
```

这个仅文档的收尾不重新运行应用测试；必须明确说明。

- [ ] **步骤 5：人工收尾审查与提交**

明确授权后，只暂存快照、归档索引和 PROJECT；检查已暂存差异；
使用已批准的 `aic` 提供方，意图为 `docs: archive Road v0.6`；检查提交。
除非另有决策，不得打标签、推送、发布、删除分支或启动其他平台 Road。

---

## 设计覆盖检查

| 已锁定要求 | 实施位置 |
| --- | --- |
| `0.6.0`、bundle ID、arm64、macOS 15.7+、平台矩阵 | CP0 |
| 不扩展依赖/运行时架构 | 全局约束、CP1 |
| 可重复构建的 arm64 sidecar/应用与合成冒烟测试 | CP1 |
| Developer ID、手动公证、staple、Gatekeeper、哈希 | CP2 |
| 外层 DMG 签名边界；不对内部内容进行修复签名 | CP2 |
| 可用手册与 Agent 零介入独立复现 | CP3 |
| 精确最终哈希的真实 macOS 15.7 证据 | CP3 |
| 推迟收集测试者事实并保留 quarantine 传输 | CP4 |
| 真实灵感、外部编辑器、重新启动/找回 | CP4 |
| 仅纠正 P0/P1，并在负价值时暂停 | CP4 |
| 只声称 `n = 1` MVP | CP4 |
| 独立归档；不暗示标签/推送/公开发布 | 收尾 |
