# AI-POLICY: 提交、历史与恢复

GitHub 保存所有已提交版本；编辑器里尚未提交的内容不属于 Git 历史。自动记录脚本每次通过 GitHub API 创建提交，因此不需要另设“自动保存历史”开关。

## 恢复到任意仍存在的完整档案历史版本

```sh
python scripts/archive_sync.py history
python scripts/archive_sync.py restore --sha <完整40位提交SHA> --auto-merge
```

restore 将 identity/、workflow/、memory/、skills/、archive/ 五个目录的内容恢复到目标 SHA，创建一条新的恢复提交和 PR，保留原有历史；脚本、工作流和文档配置保持当前版本，避免恢复旧脚本绕过校验。此命令仅由用户明确要求恢复时执行，普通 archive_record 工具没有恢复权限。

GitHub 网页也有 Actions → Restore archive → Run workflow，输入历史 SHA，即可一次运行恢复。工作流使用当前 main 上的工具创建恢复 PR，显式触发新提交上的校验，成功后自动合并。这里显式触发 workflow_dispatch，是因为 GITHUB_TOKEN 创建的 PR 通常不会自动触发 pull_request 工作流。失败、冲突或超时时保留 PR 并标为未完成，绝不强制合并。

初始空仓库的自动 README 提交早于完整档案建立，不能作为档案恢复目标。分支保护与组织策略仍可能阻止恢复；本仓库已允许 Actions 创建 PR，默认工作流令牌保持只读，仅恢复工作流显式申请必要写权限。

恢复动作可能删除目标版本中尚未存在的新记录，故普通校验会为 restore/ 分支使用恢复模式，仍验证路径、大小、密钥特征和模板存在性。恢复分支只允许更改五个档案目录。

## 多设备

新设备可 `git clone https://github.com/NullCXX/personal-ai-archive.git`。每次读写前刷新 main SHA。CLI 使用固定 SHA 读取、独立分支写入、合并时核对 PR head SHA，失败不会覆盖 main。

## 独立备份

```sh
git fetch origin
git bundle create personal-ai-archive-backup.bundle --all
git clone personal-ai-archive-backup.bundle recovered-archive
```

bundle 不含凭据，也不包含尚未提交的内容。请将备份保存在自己的设备；私有仓库历史仍可能包含旧的个人信息。泄露密钥必须立即撤销，普通恢复不会从历史抹除泄露内容。
