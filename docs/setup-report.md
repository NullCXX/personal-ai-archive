# AI-INDEX: 个人 AI 档案搭建与验收报告

> 历史记录：下文描述初次搭建时的私有状态。随后用户已要求改为公开，main 保护也已成功开启；当前状态见 [本次聊天整理报告](chat-import-report.md)。

交付日期：2026-10-27（Asia/Shanghai）  
GitHub 账户：NullCXX  
仓库：[NullCXX/personal-ai-archive](https://github.com/NullCXX/personal-ai-archive)  
可见性：**Private / 私有**；默认分支：`main`。

## 交付结论

仓库、Markdown 模板、通用读写工具、校验工作流和历史恢复入口已经创建并验证。第一条真实规则记录已通过校验并合并。

有两项外部条件尚未完成，不能将本次交付描述为“所有平台已自动接通”：

1. **私有仓库服务端分支保护未启用。** GitHub API 返回 403，明确要求升级 GitHub Pro。本次保持仓库私有，没有购买套餐。现有校验和写入工具不能阻止持有写权限的其他客户端直接修改主分支。
2. **其他 AI 平台尚未完成账户授权与任务钩子绑定。** 已提供接入文件与可运行工具，但未登录、绑定 ChatGPT、Gemini、Claude、Meta Muse 或 OpenAI Dots。平台授权无法通过仓库文件或一段提示词替代；Meta Muse / Dots 的专用接口还未核实。

## 目录与模板

每个 Markdown 文件第一行都有 `# AI-...:` 识别标签；所有模板以可直接阅读的正文保存，不需要转换。`{{...}}` 表示未填写信息，不能当作事实。

| 目录 | 已生成的模板/索引 | 使用方法 |
| --- | --- | --- |
| `identity/` | README、profile、goals、values | 填写身份、职业、核心标签、目标、决策原则；默认 AI-READONLY |
| `workflow/` | README、preferences、tools、priorities | 保存沟通风格、工具、工作习惯和优先级；自动新规则放入 updates/ |
| `memory/` | README、preferences、lessons、decision-template | 沉淀偏好、经验和重要决策；新增记录按类型分目录 |
| `skills/` | README、inventory、learning-plan、gaps | 技能清单、学习计划与能力差距；进展记录放入 updates/ |
| `archive/` | README、index、project-template、task-template | 保存旧项目、旧文档和完成任务索引；新归档放入 entries/ |

共 20 份核心目录模板/索引。已保留 `{{我的职业}}`、`{{常用沟通风格}}`、`{{核心决策原则}}` 等占位符，没有臆造个人信息。

## 已部署的读写与版本机制

- **GitHub API 客户端**：`scripts/archive_sync.py`，支持 read、snapshot、record、history、restore、protect。Python 3.10+，无需第三方包。
- **MCP 服务**：`scripts/mcp_server.py`，提供 archive_read、archive_snapshot、archive_record。默认只读；写入与自动合并由独立环境开关控制。
- **任务结束入口**：`scripts/task_complete.py`。Agent 宿主在任务完成时调用，把有依据的信息保存到对应目录。
- **可重试自动记录**：依据输入生成稳定 ID；每条新记录创建文件、提交和 PR。相同输入不会重复增加文件。
- **自动合并门槛**：核对本次 PR 的 head SHA，以及 GitHub Actions 的 archive-validate 成功结果；失败、超时或冲突保留 PR，返回未合并状态。
- **来源和确认状态**：记录保存 source、evidence、created_at、confirmed/proposed、可选 supersedes。推断不能冒充确认偏好。
- **恢复**：以新提交恢复五个档案目录，保留历史；不会通过强推重写主分支。目标必须是初始化后仍存在的完整档案版本。
- **权限**：仓库保持私有；Actions 默认令牌权限为只读，仅恢复工作流申请必要写权限。已允许 Actions 创建 PR，使恢复入口可用。凭据没有写入仓库或交付包。

AI-READONLY 是模型行为约定，不是 GitHub 权限机制。普通记忆工具只新增记录，既不覆盖 identity/，也不提供删除接口。获得仓库写权限的其他客户端仍可能绕过这些约定。

## 快速接入指南

详细步骤见 [ai-integration.md](https://github.com/NullCXX/personal-ai-archive/blob/main/ai-integration.md)。

**支持 GitHub API 的 AI 工具宿主：** 为该私有仓库单独授权；先查询 main SHA，再通过 Contents API 读取同一 SHA 下的 AGENTS.md、identity/、workflow/ 和相关 memory/。`integrations/github-read.openapi.json` 提供只读接口描述。

**支持命令行的 Agent：** 获取仓库，使用已有 Git 登录或秘密管理中的令牌执行：

```sh
python scripts/archive_sync.py snapshot
python scripts/archive_sync.py record --input <真实任务记录.json> --auto-merge
```

模板 `integrations/example-record.json` 中的占位符需由真实任务信息替换；工具会拒绝把模板直接当作记忆写入。没有新信息时跳过记录。

**支持本地 stdio MCP 的客户端：** 参照 `integrations/mcp-config.example.json` 指向 `scripts/mcp_server.py` 的实际绝对路径。使用账户自己的秘密管理保存凭据。需要回写时配置 `ARCHIVE_ALLOW_WRITE=1`，需要校验后自动合并时配置 `ARCHIVE_AUTO_MERGE=1`。

**任务完成触发器：** Agent 的宿主必须在任务结束时调用 archive_record 或 task_complete.py；GitHub 自身无法感知其他平台的聊天结束事件。通用函数定义在 `integrations/tool-definitions.json`。

**可复制的启动提示词：** [docs/quick-start-prompt.md](https://github.com/NullCXX/personal-ai-archive/blob/main/docs/quick-start-prompt.md)。已授权的工具环境可以直接使用；仅粘贴提示词不能授予私有仓库访问权限。

## 快速恢复

打开 [Restore archive](https://github.com/NullCXX/personal-ai-archive/actions/workflows/restore.yml)，点击 Run workflow，输入目标完整提交 SHA。工作流创建恢复 PR，显式触发校验，成功后合并；失败时保留 PR，不强制覆盖。

命令行等价操作：

```sh
python scripts/archive_sync.py history
python scripts/archive_sync.py restore --sha <完整40位历史SHA> --auto-merge
```

恢复范围为五个档案目录，工具和工作流维持当前版本。详见 [docs/version-control.md](https://github.com/NullCXX/personal-ai-archive/blob/main/docs/version-control.md)。

## 验收证据

| 检查 | 实际结果 |
| --- | --- |
| 私有仓库创建 | GitHub API 返回 201，private=true |
| 本地工具测试 | 14 项通过，覆盖去重、路径越界、疑似凭据、内容篡改、身份修改限制、CI 失败/伪造检查、SHA 变化、恢复范围及 MCP 握手 |
| Markdown 校验 | 所有已生成 Markdown 文件的首行标签、大小和内容规则通过 |
| 初次在线校验 | [GitHub Actions 成功](https://github.com/NullCXX/personal-ai-archive/actions/runs/40357645655) |
| 真实写入与合并 | [PR #1 已合并](https://github.com/NullCXX/personal-ai-archive/pull/1)；内容仅来自本次用户明确要求 |
| 重复写入 | 同一输入返回 duplicate=true，没有新增记录 |
| API 快照读取 | 成功读取固定提交上的完整档案 |
| MCP 实际读取 | stdio 请求成功读取 identity/profile.md，职业占位符完整保留 |
| 恢复版本在线校验 | [推送检查成功](https://github.com/NullCXX/personal-ai-archive/actions/runs/40358368926) |
| 显式校验触发 | [workflow_dispatch 成功](https://github.com/NullCXX/personal-ai-archive/actions/runs/40358425489) |
| 恢复工作流入口 | [当前版本无变更恢复成功](https://github.com/NullCXX/personal-ai-archive/actions/runs/40358432926)；不同历史版本的增删恢复算法已通过测试，未对真实档案做破坏性回滚演练 |
| 服务端分支保护 | 未通过：GitHub 套餐限制，HTTP 403 |

功能验收基准：`e873939f5ba218a619a55143287a3a7d9f16e8a7`。最终交付 SHA 与文件校验值另见交付包的 delivery-manifest.json。

## 交付文件与后续条件

本地提供完整仓库目录、源文件 ZIP、Git bundle 历史备份和本报告。Git bundle 保留主分支上可达的真实 Git 对象，导入时逐个验证 SHA；Git 凭据不属于这些对象。

若日后升级 GitHub Pro，仓库所有者可运行 `python scripts/archive_sync.py protect` 尝试启用禁止强推/删除、强制 PR 和校验的保护，并检查返回结果。各 AI 平台首次授权与工具注册后，才可开始自动同步；本次未购买任何服务，也未创建未经核实的产品专用接口。
