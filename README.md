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
        with:
          webhook: ${{ secrets.DINGTALK_WEBHOOK }}
```

Push 时自动打 tag、生成 Release、发送钉钉通知。仅 README 变更时跳过 Release。

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
- **PR**: 状态图标/标题/作者/分支/labels/内容预览
- **Issue**: 状态图标/标题/作者/labels/内容预览
- **Release**: 版本号/发布者 + 完整 changelog
- 所有消息中英双语，中文在前
- 自动附加 `> GitHub` 关键词

## 前置条件 / Prerequisites

钉钉群需添加自定义机器人，安全设置选「自定义关键词」，填入 `GitHub`。
