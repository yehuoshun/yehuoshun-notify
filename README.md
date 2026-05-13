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

### 带自动 Release 的 Push

```yaml
on:
  push:
    branches: [main]

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: yehuoshun/yehuoshun-notify@main
        id: notify
        with:
          webhook: ${{ secrets.DINGTALK_WEBHOOK }}
      - name: 下游使用版本号
        run: echo "新版本: ${{ steps.notify.outputs.version }}"
```

Push 时自动打 tag、生成 Release、发送钉钉通知。仅 README 变更时跳过 Release。

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
| `create_release` | ❌ | `'true'` | 是否自动创建 GitHub Release |
| `changelog_format` | ❌ | `- **%h** %s (%an, %ad)%n%b` | git log 格式化模板，用于 Release body 中的 changelog |

## 输出 / Outputs

| 输出 / Output | 说明 / Description |
|---|---|
| `version` | 生成的版本号（仅 push 且触发 release 时有效） |
| `should_release` | 是否触发了 release（仅 push 时有效，`'true'` / `'false'`） |

### changelog_format 自定义示例

```yaml
- uses: yehuoshun/yehuoshun-notify@main
  with:
    webhook: ${{ secrets.DINGTALK_WEBHOOK }}
    # 简洁模式：仅主题
    changelog_format: '- %s'
    # 完整模式（默认）：hash + 主题 + 作者 + 日期 + body
    # changelog_format: '- **%h** %s (%an, %ad)%n%b'
```

格式占位符参考 `git log --pretty=format`：
- `%h` — 缩写 commit hash
- `%s` — 提交主题
- `%an` — 作者名
- `%ad` — 日期
- `%b` — body 全文

## 消息格式 / Message Format

- **Push**: 仓库/分支/提交者/提交数 + commit 列表（自动匹配 emoji）
- **PR**: 状态图标/标题/作者/分支/labels/内容预览（含 review_requested / ready_for_review / synchronize）
- **PR Review**: 审查结果通知（✅批准 / 🔄请求修改 / 💬评论 / ↩️驳回）
- **Issue**: 状态图标/标题/作者/labels/内容预览
- **Release**: 版本号/发布者 + 完整 changelog
- **Workflow Run**: 工作流名/状态/分支/触发者（✅成功 ❌失败 ⏹️取消 ⏭️跳过）
- 所有消息中英双语，中文在前
- 自动附加 `> GitHub` 关键词

## 前置条件 / Prerequisites

钉钉群需添加自定义机器人，安全设置选「自定义关键词」，填入 `GitHub`。
