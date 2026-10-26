# AI-READONLY: 安全与权限边界

仓库为 private。GitHub 身份认证使用运行环境中的 ARCHIVE_GITHUB_TOKEN / GH_TOKEN / GITHUB_TOKEN，或已有 Git Credential Manager；凭据不写入文件、不放在 URL、不输出到日志。

- 只读客户端：仅授予此仓库 Contents: read。
- 写入客户端：仅授予此仓库 Contents: write、Pull requests: write、Checks: read。平台无法读取 Checks 时，工具保留 PR 并停止自动合并。
- 首次安装工作流需要额外的 Workflows: write（classic token 对应 workflow scope）；日常记录不需要此权限。
- 日常 Agent 不需要 Administration 权限。不要把账户的完整管理员凭据复制到其他 AI 平台。
- `AI-READONLY` 是行为约定，不是加密或权限。令牌拥有 Contents: write 时，恶意客户端仍可能写入其它文件。

当前私有仓库分支保护被账户套餐限制（GitHub API 403：Upgrade to GitHub Pro or make this repository public to enable this feature）。我们保持私有，未购买任何套餐。升级后可由仓库所有者运行 `python scripts/archive_sync.py protect` 开启 main 禁止删除/强推、强制 PR 与 archive-validate 检查。脚本只在 API 返回成功并复查后报告启用。

PR 校验、自动写入白名单、只新增记录和 Git 历史提供恢复能力，但不等同于服务器强制保护。拥有管理权限的人也可以更改保护设置。仓库被彻底删除、历史被重写后的恢复仍依赖独立备份；交付包包含初始化 Git bundle。

来源：GitHub [受保护分支](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)。
