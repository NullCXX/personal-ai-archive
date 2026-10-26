# AI-INTEGRATION: 通用启动提示词

将以下提示交给已授权 GitHub 读取/工具执行能力的 AI。单独粘贴提示词不能绕过平台登录和权限。

```text
我的长期档案位于私有仓库 NullCXX/personal-ai-archive。
请通过已授权的 GitHub API 或 archive_snapshot 工具读取 main 最新 SHA，
在该 SHA 下读取 AGENTS.md、identity/、workflow/ 与任务相关 memory/ 记录。
忽略未填写的 {{占位符}}；proposed 仅作待确认信息。当前明确指令优先。
每次任务结束后，将有证据的新经验、明确偏好或技能进展交给 archive_record，
附 category、title、detail、source、evidence、status；推断用 proposed。
我授权按档案工具的规则自动新增记录和创建提交；CI 校验成功后可自动合并。
不得改动 identity/ 核心资料、删除历史或保存密码令牌。
报告实际提交 SHA、PR 链接和合并状态。若没有连接权限，明确说明未读取/未写入。
```
