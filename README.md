# AI-INDEX: NullCXX 的跨 AI 个人记忆档案

仓库：https://github.com/NullCXX/personal-ai-archive  
当前状态：**公开；main 已启用分支保护**。资料更新：2026-10-27。

以 UTF-8 Markdown 保存可公开的个人背景、协作偏好、学习与项目经验。GitHub 是共享资料来源；不同 AI 需具备网页/API/工具读取能力，不会因此自动共享各自内置记忆。

## 从这里开始

- [个人身份](identity/profile.md)、[目标](identity/goals.md)、[实践与决策原则](identity/values.md)
- [沟通与交付偏好](workflow/preferences.md)、[工具](workflow/tools.md)、[推进顺序](workflow/priorities.md)
- [生活咨询参考指南](workflow/reference-guides.md)：已关联 [HowToLiveBetter · 高性价比人生指南](https://github.com/eternity4719/HowToLiveBetter)，供相关咨询时按需参考。
- [偏好索引](memory/preferences.md)、[经验主题](memory/lessons.md)、[决策与开放项](memory/decisions-index.md)
- [能力证据](skills/inventory.md)、[学习路线](skills/learning-plan.md)、[待提升项](skills/gaps.md)
- [87 个聊天的逐项摘要](archive/conversations/2026-10-27/index.md)、[13 个项目主题](archive/index.md)

## 本次整理范围

本机可读的 81 个 Codex 用户聊天和 6 个有正文的 VS Code 聊天，共 **87 个会话**，开始日期为 2026-02-24—2026-10-27。另检查并列出 30 个空白 VS Code 容器；Copilot 的 4 个索引会话已包含其中，没有重复计算。145 个辅助子任务不当作新的本人陈述。所有来源均有编号和状态。

ChatGPT 云端会话当前无法通过应用接口读取，未找到常见导出；其他未取得的云端记录、附件独立内容未被冒称已覆盖。

## 目录职责

| 目录 | 保存内容 |
| --- | --- |
| identity/ | 本人明确自述的身份、目标和原则 |
| workflow/ | 工作方式、工具、沟通、优先级与交接 |
| memory/ | 有来源的偏好、经验和决策 |
| skills/ | 有证据的能力、正在学习的内容和待验证项 |
| archive/ | 逐聊天摘要与项目阶段快照；不等于项目已完成 |

## AI 读取与更新

先读 [AGENTS.md](AGENTS.md)，再按任务读取相关文件。未知项保留 `{{...}}`，用户明确表达、助手历史报告和建议分别处理。

```sh
python scripts/archive_sync.py read --path identity/profile.md
python scripts/archive_sync.py snapshot
python scripts/archive_sync.py record --input <真实记录.json> --auto-merge
```

公开文件可匿名读取；批量读取建议使用授权凭据以避免 GitHub 匿名限流。写入必须授权，新增记录经 PR 和 archive-validate 校验后合并。MCP 默认只读；详见 [ai-integration.md](ai-integration.md)。

## 公开与版本边界

- 公开的是整理后的摘要；不发布聊天原文、凭据、联系方式和内部财务/设备接入信息。历史聊天中的私人关系和第三方信息不自动公开；个人档案中本次由本人主动补充的恋爱状态、纪念日期和家庭职业仅限已提供的内容，详见 [公开数据范围](SECURITY.md)。
- main 已要求 PR、archive-validate 检查，并对管理员应用禁止强推/删除等保护；工具还核对被校验提交 SHA。
- 所有修改保留 Git 提交；[恢复入口与说明](docs/version-control.md)支持恢复完整档案历史版本。
- 日后转私有需重新核对套餐下的保护能力；已被他人克隆的公开副本无法收回。

[本次整理报告](docs/chat-import-report.md) · [接入指南](ai-integration.md) · [安全边界](SECURITY.md) · [初次搭建历史报告](docs/setup-report.md)
