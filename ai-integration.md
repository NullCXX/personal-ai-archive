# AI-INTEGRATION: 跨平台读取与任务结束回写

仓库：`NullCXX/personal-ai-archive`；分支：`main`；内容：UTF-8 Markdown；配置版本：1；核查日期：2026-10-27。

## 能力与实际连接状态

| 平台 | 接入路径 | 本次交付状态 |
| --- | --- | --- |
| ChatGPT | 账号可用的 GitHub 应用用于读取；支持自定义 API 工具的环境可用下方 GitHub API / OpenAPI | 适配说明和只读 OpenAPI 已生成；未登录或绑定该平台账户，不能宣称连接完成 |
| Gemini | 通过 API function calling 调用 archive_read / archive_snapshot / archive_record，由宿主执行脚本 | 函数定义和执行工具已提供；普通网页聊天不因此自动获得私有仓库权限 |
| Claude | 支持本地 stdio MCP 的客户端可启动本仓库 MCP 服务；API 客户端可用函数工具 | MCP 服务和配置示例已提供；未修改你现有的客户端配置 |
| OpenAI Dots | 如账户提供 GitHub/命令行/兼容 MCP 能力，按同一读写协议接入 | 未核实该账户功能和可用官方接入文档；保留通用适配，不承诺产品原生自动同步 |
| Meta Muse | 如产品支持授权 HTTP、命令行或兼容 MCP，按同一协议接入 | 未核实对应产品的官方 GitHub 同步接口；不能承诺原生支持 |

各平台首次授权受平台自身机制控制，无法靠一个 Markdown 文件或提示词替代。已授权并配置工具/任务钩子的 Agent 可复用同一数据格式；跨设备不需要重建档案，但设备仍需独立获得权限。不要将私有仓库改公开来解决读取失败。

## 直接使用 GitHub API

请求发送至 `https://api.github.com`，认证放在 `Authorization: Bearer <运行环境中的令牌>` 请求头。不要将令牌粘贴到聊天、仓库、URL 或命令历史。

1. `GET /repos/NullCXX/personal-ai-archive/git/ref/heads/main`，获取 `object.sha`。
2. `GET /repos/NullCXX/personal-ai-archive/contents/AGENTS.md?ref=<SHA>`，随后读取相关目录。使用 `Accept: application/vnd.github.raw+json` 可直接返回 Markdown；JSON 模式的 `content` 则是 Base64，需要工具解码后交给 AI。
3. `GET /repos/NullCXX/personal-ai-archive/git/trees/<SHA>?recursive=1` 获取文件索引，检查 `truncated`。只读取任务相关 `.md` 文件。
4. 写入使用独立分支 + 新文件 + PR，不直接覆写 main；完整实现见 `scripts/archive_sync.py`。

`integrations/github-read.openapi.json` 可供支持 OpenAPI 导入的工具宿主使用，只提供读取接口；宿主必须单独配置认证。不是所有聊天页面都支持导入 OpenAPI。

## 命令行适配：无需安装第三方 Python 包

需要 Python 3.10+。授权从 `ARCHIVE_GITHUB_TOKEN`、`GH_TOKEN`、`GITHUB_TOKEN` 或 Git Credential Manager 读取。读取/写入分别使用所需的最小权限，见 SECURITY.md。

```sh
python scripts/archive_sync.py read --path workflow/preferences.md
python scripts/archive_sync.py snapshot
python scripts/archive_sync.py record --input integrations/example-record.json --auto-merge
```

示例记录包含占位符，工具会拒绝直接写入；Agent 应根据真实任务生成自己的输入文件。成功读取时输出 Markdown 和固定 SHA；成功写入时输出路径、提交 SHA、PR URL、merged 标记。

## MCP 适配

`python scripts/mcp_server.py` 提供本地 stdio MCP，支持 `archive_read`、`archive_snapshot` 和 `archive_record`。默认只读；需设置 `ARCHIVE_ALLOW_WRITE=1` 才暴露记录工具。需要自动合并时另设 `ARCHIVE_AUTO_MERGE=1`。不暴露删除、恢复和修改核心资料的工具。

参照 `integrations/mcp-config.example.json`，将 `args` 中的路径替换为实际绝对路径，配置于支持 stdio MCP 的客户端；密钥通过客户端的秘密管理或继承环境提供。示例不是所有产品共用的配置文件，远程网页 Agent 也不能直接连接本机 stdio；需要其自己的授权工具宿主，或单独部署 HTTPS MCP 网关。本次未部署公开服务器。

`integrations/tool-definitions.json` 提供平台中立 JSON Schema；不同厂商 SDK 的包装格式由宿主转换。不得把 API 密钥当作模型消息发送。

## 自动更新规则

| 信息类型 | category | 新记录位置 |
| --- | --- | --- |
| 明确偏好或待确认偏好 | preference | memory/preferences/ |
| 可复用经验 | lesson | memory/lessons/ |
| 决策与依据 | decision | memory/decisions/ |
| 工作习惯或规则 | workflow | workflow/updates/ |
| 技能成果/学习进展 | skill | skills/updates/ |
| 完成任务/历史项目 | archive | archive/entries/ |

任务开始调用 snapshot 或按需 read；任务结束时宿主将真实记录传给 `archive_record`，或执行 `python scripts/task_complete.py <record.json>`。该钩子调用同一受限写入逻辑，只有设置 `ARCHIVE_AUTO_MERGE=1` 才请求自动合并。

每条记录必须有 category、title、detail、source、evidence、status；status 是 confirmed 或 proposed。只有本人明确表达或已验证结果才能 confirmed。无新信息则不调用写入。输入内容一致时记录 ID 一致，重复任务不会新增副本。更正使用 supersedes 引用旧记录 ID。

自动合并检查本次 head SHA 的 GitHub Actions `archive-validate` 结果，校验成功且 SHA 未变化后才合并。超时、失败、合并冲突和限流会留下 PR，回报实际状态；下次用相同记录重试即可。待合并 PR 不会被主分支读取工具当成已同步事实。

**触发边界：** GitHub 不知道其他 AI 的聊天何时结束。本仓库工作流负责提交校验和手动恢复；任务完成触发器必须由各 Agent 宿主调用。仅复制仓库不会产生跨平台后台监控，也不会自动把档案灌入各平台内置记忆。

## 官方资料与核实边界

- 已读取：[GitHub Contents API](https://docs.github.com/en/rest/repos/contents#get-repository-content)、[分支保护与套餐](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)、[Gemini Function calling](https://ai.google.dev/gemini-api/docs/function-calling)。
- 本环境访问 OpenAI 官方文档域名出现 TLS 连接错误；[OpenAI tools/MCP](https://developers.openai.com/api/docs/guides/tools-connectors-mcp) 和 [Claude tool use](https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview) 仅作为待核对入口，未据此声称当前账户已支持某项功能。
- Meta Muse / OpenAI Dots 的专用同步接口、权限选项与地区/套餐可用性尚未核实，不编造配置键或 API 地址。
