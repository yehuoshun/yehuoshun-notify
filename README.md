# DingTalk Notify Action

中英双语 GitHub 事件通知 → 钉钉机器人。

## 使用

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
      - uses: yehuoshun/dingtalk-notify@main
        with:
          webhook: ${{ secrets.DINGTALK_WEBHOOK }}
```

### Release 通知

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
      - uses: yehuoshun/dingtalk-notify@main
        with:
          webhook: ${{ secrets.DINGTALK_WEBHOOK }}
          event: release
```

## 消息格式

- **Push**: 仓库/分支/提交者/提交数 + commit 列表（自动匹配 emoji）
- **PR**: 状态图标/标题/作者/分支/labels/内容预览
- **Issue**: 状态图标/标题/作者/labels/内容预览
- **Release**: 仓库/分支/提交者/提交信息
- 所有消息中英双语，中文在前
- 自动附加 `> GitHub` 关键词

## 前置条件

钉钉群需添加自定义机器人，安全设置选「自定义关键词」，填入 `GitHub`。
