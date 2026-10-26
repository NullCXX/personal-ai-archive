# AI-INDEX: 跨 AI 个人记忆档案

私有仓库：https://github.com/NullCXX/personal-ai-archive

本仓库以 UTF-8 Markdown 保存长期个人信息，GitHub 为共享来源。不同 AI 在授权后读取同一份档案，不代表各平台内置“记忆”会自动互通。模板中的占位符尚未填写，不构成个人事实。

## 内容导航

| 目录 | 内容 | 使用方法 |
| --- | --- | --- |
| identity/ | 身份、目标、价值观 | 仅根据本人明确提供的信息填写 |
| workflow/ | 习惯、工具、沟通、优先级 | 任务开始时读取；变更追加到 updates/ |
| memory/ | 偏好、经验、决策 | 任务结束后追加带来源的记录 |
| skills/ | 技能、学习计划、能力差距 | 随已验证的学习成果更新 |
| archive/ | 历史项目、旧文档、完成任务 | 保存完成状态与交付物索引 |

## 最短使用路径

1. AI 首先读取 [AGENTS.md](AGENTS.md)，再读取 identity/、workflow/ 和相关 memory/ 记录。
2. 支持命令行的 Agent 使用 `python scripts/archive_sync.py snapshot` 获取固定提交上的 Markdown 档案。
3. 完成任务后，按 [ai-integration.md](ai-integration.md) 生成记录 JSON，调用 `record --input <文件> --auto-merge`。脚本会新增文件、创建提交和 PR；只有指定 CI 校验成功后才合并。未完成时返回 PR 链接，不能宣称已经同步。
4. 查看或恢复历史：见 [docs/version-control.md](docs/version-control.md)。恢复通过新增提交保留历史。

## 当前边界

- 当前 GitHub 账户不支持私有仓库分支保护：API 返回 403，要求 GitHub Pro。校验工作流和客户端限制不能阻止持有写权限者直接修改 main。
- AI 识别标签是约定，不能替代 GitHub 权限控制。通用写入工具只新增记录，不修改核心身份文件。
- 接入配置、CLI、MCP 服务与任务结束钩子已随仓库提供；ChatGPT、Gemini、Claude、Meta Muse、OpenAI Dots 的账户连接需要各自授权。未授权的平台不会自动读取此私有仓库。
- 本仓库不自动调用付费模型，不保存密码、令牌、完整聊天记录或不相关的第三方信息。

[完整接入指南](ai-integration.md) · [安全说明](SECURITY.md) · [快速提示词](docs/quick-start-prompt.md)
