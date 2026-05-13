#!/usr/bin/env python3
"""DingTalk notification for GitHub repo events — 中英双语 Markdown 模板."""
import json, os, re, sys, time, urllib.request, urllib.error

# ── preflight checks ─────────────────────────────────────

WEBHOOK = os.environ.get("DINGTALK_WEBHOOK", "")
if not WEBHOOK:
    print("[DingTalk] ❌ 未配置 DINGTALK_WEBHOOK，请在仓库 Settings > Secrets 中添加", file=sys.stderr)
    sys.exit(1)

CUSTOM_EVENT = os.environ.get("DINGTALK_EVENT", "")
EVENT_NAME = CUSTOM_EVENT or os.environ["GITHUB_EVENT_NAME"]
EVENT_PATH = os.environ["GITHUB_EVENT_PATH"]
REPO = os.environ.get("GITHUB_REPOSITORY", "?")

# @ 提醒
MENTION_USERS = os.environ.get("DINGTALK_MENTION_USERS", "")
MENTION_MOBILES = os.environ.get("DINGTALK_MENTION_MOBILES", "")
MENTION_ALL = os.environ.get("DINGTALK_MENTION_ALL", "false") == "true"
MAX_COMMITS = int(os.environ.get("DINGTALK_MAX_COMMITS", "0") or "0")

try:
    with open(EVENT_PATH) as f:
        ev = json.load(f)
except FileNotFoundError:
    print(f"[DingTalk] ❌ 事件文件不存在: {EVENT_PATH}", file=sys.stderr)
    sys.exit(1)
except json.JSONDecodeError as e:
    print(f"[DingTalk] ❌ 事件 JSON 解析失败: {e}", file=sys.stderr)
    sys.exit(1)

# ── helpers ──────────────────────────────────────────────

COMMIT_EMOJI = {
    "feat": "✨", "fix": "🐛", "docs": "📝", "style": "💄",
    "refactor": "♻️", "test": "✅", "chore": "🔧", "perf": "⚡",
    "ci": "👷", "build": "📦", "revert": "⏪", "merge": "🔀",
    "wip": "🚧",
}

COMMIT_ALIASES = {
    "fixes": "fix", "fixed": "fix", "bugfix": "fix", "bug": "fix",
    "feature": "feat", "features": "feat",
    "documentation": "docs", "doc": "docs",
    "refactoring": "refactor", "refactored": "refactor",
    "testing": "test", "tests": "test",
    "performance": "perf",
    "builds": "build",
    "reverts": "revert",
    "merging": "merge",
}

def _emoji(msg):
    m = re.match(r"(\w+)[(:]", msg)
    key = (m.group(1) if m else "").lower()
    return COMMIT_EMOJI.get(key) or COMMIT_EMOJI.get(COMMIT_ALIASES.get(key, ""), "•")

def _truncate(text, n=300):
    if not text: return ""
    text = text.strip()
    return text if len(text) <= n else text[:n].rsplit("\n", 1)[0] + "\n…"


# ── builders ─────────────────────────────────────────────

def push():
    ref = os.environ["GITHUB_REF_NAME"]
    actor = os.environ["GITHUB_ACTOR"]
    compare = ev.get("compare", "")
    commits = ev.get("commits", [])
    total = len(commits)

    lines = []
    seen = set()
    for c in commits[:MAX_COMMITS] if MAX_COMMITS > 0 else commits:
        raw = c.get("message", "")
        msgParts = raw.split("\n")
        title = msgParts[0][:80]
        author = c.get("author", {}).get("name", "?")
        key = f"{title}|{author}"
        if key in seen: continue
        seen.add(key)

        # Show all body lines for full context
        body = [b.strip() for b in msgParts[1:] if b.strip() and b.strip().startswith("-")]
        if body:
            subItems = "\n".join(f"  {b}" for b in body)
            lines.append(f"- {_emoji(title)} {title}  — **{author}**\n{subItems}")
        else:
            lines.append(f"- {_emoji(title)} {title}  — **{author}**")

    commit_text = "\n".join(lines)
    if total > (MAX_COMMITS if MAX_COMMITS > 0 else total):
        shown = MAX_COMMITS if MAX_COMMITS > 0 else total
        commit_text += f"\n- ⋯ 共 **{total}** 条 / **{total}** total"

    title = f"Push · {REPO}"
    text = f"""## 🚀 代码推送 · Code Push  

**仓库** / *Repo*: {REPO}  
**分支** / *Branch*: {ref}  
**提交者** / *Author*: **{actor}**  
**提交数** / *Commits*: **{total}**  

{commit_text}  

[📎 查看变更 / View diff]({compare})  

—— **GitHub**"""
    return title, text


def pull_request():
    pr = ev.get("pull_request", {})
    action = ev.get("action", "?")
    number = pr.get("number", "?")

    action_label = {
        "opened":   "🟢 新建 / Opened",
        "closed":   "🔴 关闭 / Closed",
        "reopened": "🔄 重新打开 / Reopened",
        "synchronize": "🔄 代码更新 / Code Updated",
        "review_requested": "👀 请求审查 / Review Requested",
        "ready_for_review": "📋 准备审查 / Ready for Review",
    }.get(action, f"📌 {action}")
    if action == "closed" and pr.get("merged"):
        action_label = "🟣 已合并 / Merged"

    user = pr.get("user", {}).get("login", "?")
    head = pr.get("head", {}).get("ref", "?")
    base = pr.get("base", {}).get("ref", "?")
    url = pr.get("html_url", "")
    body = _truncate(pr.get("body", ""))
    labels_list = [l["name"] for l in (pr.get("labels") or [])]
    label_str = " · ".join(f"`{l}`" for l in labels_list) if labels_list else "—"

    title = f"PR {action} · {REPO}"
    text = f"""## {action_label}  

**{pr.get('title', '?')}**  

- **作者** / *Author*: **{user}**  
- **分支** / *Branch*: {head} → {base}  
- **标签** / *Labels*: {label_str}"""

    if body:
        text += f"\n\n{body}"

    text += f"\n\n[📎 查看详情 / View PR]({url})  \n\n—— **GitHub**"
    return title, text


def issues():
    issue = ev.get("issue", {})
    action = ev.get("action", "?")
    number = issue.get("number", "?")

    action_label = {
        "opened":   "📝 新建 / Opened",
        "closed":   "✅ 关闭 / Closed",
        "reopened": "🔄 重新打开 / Reopened",
    }.get(action, f"📌 {action}")

    user = issue.get("user", {}).get("login", "?")
    url = issue.get("html_url", "")
    body = _truncate(issue.get("body", ""))
    labels_list = [l["name"] for l in (issue.get("labels") or [])]
    label_str = " · ".join(f"`{l}`" for l in labels_list) if labels_list else "—"

    title = f"Issue {action} · {REPO}"
    text = f"""## {action_label}  

**{issue.get('title', '?')}**  

- **作者** / *Author*: **{user}**  
- **标签** / *Labels*: {label_str}"""

    if body:
        text += f"\n\n{body}"

    text += f"\n\n[📎 查看详情 / View Issue]({url})  \n\n—— **GitHub**"
    return title, text


def release():
    """GitHub Release 事件通用模板。
    展示 release body（含完整 changelog）+ 元信息。
    """
    rel = ev.get("release", {})
    action = ev.get("action", "published")
    tag = rel.get("tag_name", "?")
    name = rel.get("name") or tag
    body = rel.get("body", "")
    url = rel.get("html_url", "")
    author = rel.get("author", {}).get("login", "?")
    prerelease = rel.get("prerelease", False)
    draft = rel.get("draft", False)

    badge = "🏷️"
    if prerelease: badge = "🧪"
    if draft: badge = "📝"

    action_label = {
        "published": "发布 / Published",
        "created": "创建 / Created",
        "edited": "编辑 / Edited",
        "deleted": "删除 / Deleted",
        "prereleased": "预发布 / Prereleased",
        "released": "正式发布 / Released",
    }.get(action, action)

    title = f"{badge} Release {tag} · {REPO}"

    text = f"""## {badge} {action_label}

**{name}**

- **仓库** / *Repo*: {REPO}
- **版本** / *Version*: `{tag}`
- **发布者** / *Author*: **{author}**
"""

    if body:
        # release body 通常包含完整 changelog，直接展示
        text += f"\n{body}\n"

    if url:
        text += f"\n[📎 查看 Release / View Release]({url})"

    text += "\n\n—— **GitHub**"
    return title, text


def pull_request_review():
    """pull_request_review 事件 — PR 审查结果通知。"""
    review = ev.get("review", {})
    pr = ev.get("pull_request", {})
    state = review.get("state", "?")

    icon = {
        "approved": "✅",
        "changes_requested": "🔄",
        "commented": "💬",
        "dismissed": "↩️",
    }.get(state, "📌")

    label = {
        "approved": "已批准 / Approved",
        "changes_requested": "请求修改 / Changes Requested",
        "commented": "已评论 / Commented",
        "dismissed": "已驳回 / Dismissed",
    }.get(state, state)

    reviewer = review.get("user", {}).get("login", "?")
    pr_title = pr.get("title", "?")
    pr_url = pr.get("html_url", "")
    body = _truncate(review.get("body", ""))

    title = f"Review {state} · {REPO}"
    text = f"""## {icon} PR 审查 {label}

**{pr_title}**

- **审查人** / *Reviewer*: **{reviewer}**
- **PR** / *PR*: [#{pr.get('number', '?')}]({pr_url})"""

    if body:
        text += f"\n\n{body}"

    text += f"\n\n[📎 查看 PR / View PR]({pr_url})  \n\n—— **GitHub**"
    return title, text


def workflow_run():
    """workflow_run 事件 — CI/CD 完成通知。"""
    wf = ev.get("workflow_run", {})
    name = wf.get("name", "?")
    conclusion = wf.get("conclusion", "?")
    url = wf.get("html_url", "")
    branch = wf.get("head_branch", "?")
    actor = (wf.get("actor") or {}).get("login", "?")

    icon = {"success": "✅", "failure": "❌", "cancelled": "⏹️", "skipped": "⏭️"}.get(conclusion, "📌")
    label = {
        "success": "成功 / Success",
        "failure": "失败 / Failed",
        "cancelled": "已取消 / Cancelled",
        "skipped": "已跳过 / Skipped",
    }.get(conclusion, conclusion)

    title = f"Workflow {conclusion} · {REPO}"
    text = f"""## {icon} 工作流 {label}

**{name}**

- **仓库** / *Repo*: {REPO}
- **状态** / *Status*: `{conclusion}`
- **分支** / *Branch*: {branch}
- **触发者** / *Triggered by*: **{actor}**

[📎 查看详情 / View Run]({url})

—— **GitHub**"""
    return title, text


# ── dispatch ─────────────────────────────────────────────

handlers = {
    "push": push,
    "pull_request": pull_request,
    "pull_request_review": pull_request_review,
    "issues": issues,
    "release": release,
    "workflow_run": workflow_run,
}
handler = handlers.get(EVENT_NAME)
if handler:
    title, text = handler()
else:
    title = f"{EVENT_NAME} · {REPO}"
    text = f"## 📢 事件 / Event: `{EVENT_NAME}`\n\n_{REPO}_\n\n—— **GitHub**"

# @ 提醒：text 末尾追加 @ 标记（钉钉要求 text 中必须出现 @对象）
mention_parts = []
if MENTION_USERS:
    for uid in [u.strip() for u in MENTION_USERS.split(",") if u.strip()]:
        mention_parts.append(f"@{uid}")
if MENTION_MOBILES:
    for m in [m.strip() for m in MENTION_MOBILES.split(",") if m.strip()]:
        mention_parts.append(f"@{m}")
if MENTION_ALL:
    mention_parts.append("@all")

if mention_parts:
    text += "\n\n" + " ".join(mention_parts)

payload_obj = {
    "msgtype": "markdown",
    "markdown": {"title": title, "text": text},
}

# 有 @ 内容时才注入 at 对象
at_payload = {}
if MENTION_USERS:
    at_payload["atUserIds"] = [u.strip() for u in MENTION_USERS.split(",") if u.strip()]
if MENTION_MOBILES:
    at_payload["atMobiles"] = [m.strip() for m in MENTION_MOBILES.split(",") if m.strip()]
if MENTION_ALL:
    at_payload["isAtAll"] = True
if at_payload:
    payload_obj["at"] = at_payload

payload = json.dumps(payload_obj).encode()

# ── send with retry ──────────────────────────────────────

MAX_RETRIES = 3
for attempt in range(MAX_RETRIES):
    try:
        req = urllib.request.Request(WEBHOOK, data=payload, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=10)
        resp_body = resp.read().decode()
        # 钉钉返回 200 但 errcode 非 0 → 业务错误（限流等）
        try:
            body = json.loads(resp_body)
            errcode = body.get("errcode", 0)
            if errcode == 0:
                print(f"[DingTalk] ✅ 发送成功 / Sent")
                break
            elif errcode == 90030:
                print(f"[DingTalk] ⚠️ 钉钉频率超限 / rate limited, 1 分钟后重试")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(60)
                    continue
                else:
                    print("[DingTalk] ❌ 通知发送失败，已重试3次 / Notification failed after 3 retries")
            else:
                errmsg = body.get("errmsg", "unknown")
                print(f"[DingTalk] ⚠️ errcode={errcode}: {errmsg}")
                if attempt < MAX_RETRIES - 1:
                    wait = 2 ** attempt
                    print(f"[DingTalk] ⏳ {wait}s 后重试 / retrying in {wait}s")
                    time.sleep(wait)
                    continue
                else:
                    print("[DingTalk] ❌ 通知发送失败，已重试3次 / Notification failed after 3 retries")
        except json.JSONDecodeError:
            print(f"[DingTalk] ✅ {resp.status} (非 JSON 响应)")
            break
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        print(f"[DingTalk] ⚠️ 尝试 {attempt+1}/{MAX_RETRIES} 失败 / Attempt {attempt+1}/{MAX_RETRIES} failed: {e}")
        if attempt < MAX_RETRIES - 1:
            wait = 2 ** attempt
            print(f"[DingTalk] ⏳ {wait}s 后重试 / retrying in {wait}s")
            time.sleep(wait)
        else:
            print("[DingTalk] ❌ 通知发送失败，已重试3次 / Notification failed after 3 retries")
            # 不抛异常：通知失败不应阻断 CI
