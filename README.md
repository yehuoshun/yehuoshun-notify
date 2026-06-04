# DingTalk Notify Action

中英双语 GitHub 事件通知 → 钉钉机器人。  
Bilingual (CN/EN) GitHub event → DingTalk bot.

## 使用 / Usage

### 常规通知（push / PR / issue）

```yaml
on:
  push:
    branches: [main]
  pull_request:
    types: [opened, closed, reopened]
  issues:
    types: [opened, closed, reopened]

jobs:
  notify:
    runs-on: ubuntu-latest
    steps:
      - uses: yehuoshun/yehuoshun-notify@main
        with:
          webhook: ${{ secrets.DINGTALK_WEBHOOK }}
```

### PR Review 通知

```yaml
on:
  pull_request_review:
    types: [submitted, edited, dismissed]

jobs:
  notify:
    runs-on: ubuntu-latest
    steps:
      - uses: yehuoshun/yehuoshun-notify@main
        with:
          webhook: ${{ secrets.DINGTALK_WEBHOOK }}
```

### Workflow Run 通知（CI/CD 结果）

```yaml
on:
  workflow_run:
    workflows: ["CI", "Build"]
    types: [completed]

jobs:
  notify:
    runs-on: ubuntu-latest
    steps:
      - uses: yehuoshun/yehuoshun-notify@main
        with:
          webhook: ${{ secrets.DINGTALK_WEBHOOK }}
```

### 外部 Release 通知

```yaml
on:
  push:
    branches: [main]
    paths:
      - 'SKILL.md'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: softprops/action-gh-release@v2
        with:
          tag_name: latest
          files: SKILL.md
      - uses: yehuoshun/yehuoshun-notify@main
        with:
          webhook: ${{ secrets.DINGTALK_WEBHOOK }}
          event: release
```

## 参数 / Inputs

| 参数 / Input | 必填 / Required | 默认 / Default | 说明 / Description |
|---|---|---|---|
| `webhook` | ✅ | — | 钉钉机器人 webhook 地址 |
| `event` | ❌ | `''` | 手动覆盖事件类型（如 `release`），默认自动检测 |
| `max_commits` | ❌ | `'0'` | push 通知最多展示的 commit 条数（0=全部） |
| `mention_users` | ❌ | `''` | 要 @ 的钉钉 userId（逗号分隔），需在钉钉管理后台查看 |
| `mention_mobiles` | ❌ | `''` | 要 @ 的手机号（逗号分隔），仅群内成员有效 |
| `mention_all` | ❌ | `'false'` | 是否 @ 所有人（`'true'` / `'false'`） |

## 消息格式 / Message Format

- **Push**: 仓库/分支/提交者/提交数 + 全部 commit 列表（默认全部显示，自动匹配 emoji + 别名）
- **PR**: 状态图标/标题/作者/分支/labels/内容预览（含 review_requested / ready_for_review / synchronize）
- **PR Review**: 审查结果通知（✅批准 / 🔄请求修改 / 💬评论 / ↩️驳回）
- **Release**: 版本号/发布者 + 完整 changelog + 文件变更列表
- **Issue**: 状态图标/标题/作者/labels/内容预览
- **Workflow Run**: 工作流名/状态/分支/触发者（✅成功 ❌失败 ⏹️取消 ⏭️跳过）
- 所有消息中英双语，中文在前
- 自动附加 `> GitHub` 关键词

## 前置条件 / Prerequisites

钉钉群需添加自定义机器人，安全设置选「自定义关键词」，填入 `GitHub`。
