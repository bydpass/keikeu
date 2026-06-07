# Agentic

结论先钉死：Agentic coding 不是“让 AI 写代码”，而是“你当产品导演 + 架构审判官，Agent 当会执行、会犯错、但速度极快的码农群”。
你要做“画饼工具”，最适合用这个时代的流程：先做能跑的垂直小工具，不要一上来搞平台梦。平台梦是创业 PPT 的鸦片。💊

1. 先定义：你的“画饼工具”到底是什么

我建议 MVP 定义成：

一个把模糊想法转成结构化项目饼图/路线图/行动拆解的本地或网页小工具。

核心输入：

我想做一个 X，它服务 Y，目标是 Z，限制是 A/B/C。

核心输出：

1. 愿景一句话
2. 用户是谁
3. 需求拆解
4. MVP 范围
5. 非 MVP 范围
6. 里程碑
7. 风险清单
8. 下一步任务

这玩意儿别叫“AI创业神器”。低级。
更准确的定位是：Idea Compiler / 饼编译器 / Vision-to-Roadmap Engine。

2. Agentic coding 的基本生产线

传统开发像这样：

想法 → 需求文档 → 设计 → 写代码 → 测试 → 部署 → 迭代

Agentic coding 时代变成：

想法 → 规格说明 → 让 Agent 生成方案 → 人类审查 → Agent 实现 → 自动/手动测试 → Git 提交 → 继续切任务

区别很硬核：

阶段	旧时代你做什么	Agentic 时代你做什么
需求	自己写很久	写清楚验收标准
架构	自己查资料	让 Agent 提案，你裁决
编码	自己逐行写	让 Agent 改文件
Debug	自己盯报错	把报错喂回 Agent
测试	经常懒得写	强迫 Agent 写测试
Review	看自己代码	审 Agent 的 diff

官方工具也基本朝这个方向走。Claude Code 的定位就是能读代码库、改文件、跑命令、接入开发工具；OpenAI Codex CLI 也是本地终端里的 coding agent，可以读、改、运行选中目录里的代码；Codex Cloud/应用还强调并行 agent、多 worktree、云环境这套工作流。 ￼

3. 你作为人类，真正该抓的不是代码，而是“边界”

Agent 最容易死在三件事：

1. 需求边界不清：它会脑补。
2. 代码边界不清：它会乱改。
3. 验证边界不清：它会说“应该好了”，然后其实没好。

所以你每次给 Agent 的任务，都要像发军令：

## Task
实现一个最小可运行的画饼工具首页。
## Scope
只允许修改：
- src/App.tsx
- src/components/*
- src/lib/*
不允许：
- 引入数据库
- 引入登录系统
- 改 package manager
- 做复杂后端

## Acceptance Criteria

- 页面可以输入一个 idea
- 点击按钮后生成结构化 roadmap
- 输出至少包含：Vision、MVP、Milestones、Risks、Next Actions
- npm run build 通过

这就是 Agentic coding 的第一心法：别让 Agent 猜你的脑子。它不是读心术，是外骨骼。

4. 推荐你的第一版技术栈

别搞复杂。你现在要的是“能返工、能理解、能交给 Agent 改”。

我建议：

前端：React + Vite + TypeScript
样式：Tailwind
状态：先用 useState
数据：localStorage
AI：第一版先 mock，不接 API
部署：GitHub Pages / Vercel
版本管理：GitHub
Agent：Claude Code 或 Codex CLI

为什么第一版不接 AI API？因为你现在学的是软件开发流程，不是烧 token 炼丹。先做一个假生成器，确认产品结构成立，再接模型。否则你会被 API、鉴权、prompt、账单、CORS 这些杂兵围殴。

5. 仓库结构：别让 repo 长成垃圾堆

第一版可以这样：

keikeu/
  README.md
  SPEC.md
  AGENTS.md 或 CLAUDE.md
  package.json
  src/
    App.tsx
    components/
      IdeaInput.tsx
      RoadmapOutput.tsx
      SectionCard.tsx
    lib/
      generateRoadmap.ts
      types.ts
  docs/
    decisions.md
    changelog.md

关键文件：

SPEC.md

写产品要做什么。

AGENTS.md / CLAUDE.md

写 Agent 该怎么干活。
这类 repo 级配置正在变成 agentic coding 的核心资产。研究者也已经注意到，Claude Code、Copilot、Cursor、Gemini、Codex 等工具都越来越依赖版本化的 Markdown/JSON 配置文件来约束 agent 行为。 ￼

docs/decisions.md

记录你每次为什么这么设计。
这东西以后救命。否则三周后你看自己项目，会像考古异星文明。

6. 一次标准 Agentic Coding 回合

你以后就按这个循环走：

1. 写 Issue / Task
2. 让 Agent 先读代码，不许动
3. 让 Agent 给计划
4. 你砍掉过度设计
5. 让 Agent 实现
6. 跑测试 / build
7. 看 diff
8. 修 bug
9. commit

对应指令可以是：

Read the repository and summarize the current architecture. Do not modify files.

然后：

Implement Task 001 from SPEC.md. Keep changes minimal. After editing, run npm run build and report the result.

然后：

Review your own diff. Identify unnecessary complexity, possible bugs, and missing tests. Do not edit yet.

最后：

Apply only the necessary fixes. Then produce a concise commit message.

OpenAI 对 Codex 的解释里也把核心称为 agent loop：模型接收上下文，调用工具，观察结果，再更新计划，直到产出结果；这和你实际操作中的“读库→计划→改文件→跑命令→看结果→再改”是一回事。 ￼

7. 对“画饼工具”的开发路线

我给你定一个四阶段路线，别飘。

Phase 0：纸面规格(DONE)

产物：

SPEC.md
README.md

目标：
讲清楚这个工具解决什么问题，不写一行代码。

Phase 1：静态原型

产物：

一个 React 页面
输入框
生成按钮
假数据输出

目标：
看起来像个工具，而不是一坨 TODO。

Phase 2：本地生成逻辑

产物：

generateRoadmap(input: string): Roadmap

目标：
先用规则生成。比如识别关键词、套模板。
这一步非常重要，因为它逼你定义数据结构。

Phase 3：接 AI

产物：

prompt template
schema validation
API call
error handling

目标：
让 AI 只负责“生成内容”，不要让它掌控整个程序。

Phase 4：保存与导出

产物：

localStorage 保存
Markdown 导出
复制按钮
历史记录

目标：
让工具进入你的 Obsidian/GitHub 知识流。

8. 你的第一个任务应该长这样

直接开一个 repo，然后写：

# Task 001: Create MVP UI

Build a minimal single-page React app for an “Idea Compiler”.

## User Flow

1. User enters a vague project idea.
2. User clicks “Compile”.
3. App displays a structured roadmap.

## Output Sections

- Vision
- Target User
- MVP Scope
- Non-MVP Scope
- Milestones
- Risks
- Next Actions

## Constraints

- No backend
- No API call
- Use mock generation logic
- Keep code beginner-readable
- TypeScript types must be explicit

## Done When

- `npm run build` succeeds
- The app works locally
- Components are split cleanly

这就是你喂给 Claude Code / Codex 的“任务弹药”。不是“帮我做个 app”这种废话 prompt。

9. 你要避免的五个新手坑

第一，别让 Agent 一次做太多。
“做一个完整创业工具平台”这种 prompt 会生成一座纸糊赛博烂尾楼。

第二，别跳过 Git。
每完成一个小任务就 commit。Agent 写崩了，你能回滚。不然就是裸奔。

第三，别迷信 AI 的自测报告。
它说 build passed，你也要自己跑。机器不骗你，Agent 会幻觉。

第四，别一开始就上数据库/登录/支付。
那是第十集剧情。第一集先让主角会走路。

第五，别把 prompt 当产品。
真正的产品是：数据结构、交互、约束、导出、版本化。Prompt 只是发动机里的燃油。

10. 你现在的最佳下一步

我建议你下一步不是写代码，而是让我帮你产出这三个文件：

README.md
SPEC.md
AGENTS.md / CLAUDE.md

然后你把它们丢进 repo，再让 Claude Code 或 Codex 开工。

我的判断很明确：
你的“画饼工具”第一版应该做成本地单页工具，而不是后端应用。先用 mock 逻辑跑通产品骨架，再接 AI。 这条路线最稳、最适合返工、最不容易被复杂度反杀。🧩