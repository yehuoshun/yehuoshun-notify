# DingTalk Notify Action

中英双语 GitHub 事件通知 → 钉钉机器人。

## 使用

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

Secrets 里配 `DINGTALK_WEBHOOK` 即可。

## 消息格式

- **Push**: 仓库/分支/提交者/提交数 + commit 列表（自动匹配 emoji）
- **PR**: 状态图标/标题/作者/分支/labels/内容预览
- **Issue**: 状态图标/标题/作者/labels/内容预览
- 所有消息中英双语，中文在前
- 自动在消息末尾附加 `> GitHub` 关键词

## 前置条件

钉钉群需添加自定义机器人，安全设置选「自定义关键词」，填入 `GitHub`。
