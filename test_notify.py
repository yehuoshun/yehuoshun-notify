#!/usr/bin/env python3
"""dingtalk-notify.py 本地集成测试：mock 钉钉服务器 + 真实子进程跑脚本。"""
import json, os, subprocess, sys, threading, http.server, tempfile, shutil

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(REPO_DIR, "dingtalk-notify.py")
received = []  # [(path, payload_dict)]

class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            payload = json.loads(body)
            received.append((self.path, payload))
        except Exception:
            received.append((self.path, {"RAW": body.decode(errors="ignore")}))
        resp = json.dumps({"errcode": 0, "errmsg": "ok"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(resp)
    def log_message(self, *a):
        pass

server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
port = server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()
WEBHOOK = f"http://127.0.0.1:{port}/robot/send"

def run_event(name, event_data, extra_env=None, expect_ok=True):
    """构造事件文件 + 环境变量，跑脚本，返回 (returncode, stdout, payload)。"""
    tmpdir = tempfile.mkdtemp(prefix="notify-test-")
    event_path = os.path.join(tmpdir, "event.json")
    with open(event_path, "w", encoding="utf-8") as f:
        json.dump(event_data, f, ensure_ascii=False)
    env = dict(os.environ)
    env.update({
        "DINGTALK_WEBHOOK": WEBHOOK,
        "DINGTALK_EVENT": "",
        "DINGTALK_MAX_COMMITS": "0",
        "DINGTALK_MENTION_USERS": "",
        "DINGTALK_MENTION_MOBILES": "",
        "DINGTALK_MENTION_ALL": "false",
        "GITHUB_EVENT_NAME": name,
        "GITHUB_EVENT_PATH": event_path,
        "GITHUB_REPOSITORY": "yehuoshun/test-repo",
        "GITHUB_REF_NAME": "main",
        "GITHUB_ACTOR": "test-user",
    })
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run([sys.executable, SCRIPT], capture_output=True, text=True, env=env, timeout=30)
    shutil.rmtree(tmpdir, ignore_errors=True)
    return proc.returncode, proc.stdout + proc.stderr, (received[-1][1] if received else None)

PASS, FAIL = 0, 0
def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {label}")
    else:
        FAIL += 1
        print(f"  ❌ {label} {detail}")

# ── 1. push（含 body 多行 + emoji 匹配 + 汇总行）──────────────
print("[1] push 事件")
rc, out, payload = run_event("push", {
    "compare": "https://github.com/yehuoshun/test-repo/compare/a..b",
    "commits": [
        {"message": "feat: 新增功能\n\n- 第一点\n- 第二点\n* 第三点", "author": {"name": "Alice"}},
        {"message": "fix: bug修复", "author": {"name": "Bob"}},
    ],
})
check("rc=0", rc == 0, f"rc={rc} out={out}")
text = (payload or {}).get("markdown", {}).get("text", "")
check("标题 Push", "代码推送" in text and "Code Push" in text)
check("emoji feat=✨", "✨ feat: 新增功能" in text, text)
check("emoji fix=🐛", "🐛 fix: bug修复" in text, text)
check("body 全行 bullet", "- 第一点" in text and "- 第二点" in text and "- 第三点" in text, text)
check("去重 bullet（无双重）", text.count("- 第一点") == 1)
check("汇总行 共2条", "共 **2** 条" in text and "**2** total" in text, text)
check("diff 链接", "View diff" in text)

# ── 2. push + max_commits 截断 ─────────────────────────────
print("[2] push + max_commits=1")
rc, out, payload = run_event("push", {
    "compare": "",
    "commits": [
        {"message": "feat: A", "author": {"name": "A"}},
        {"message": "fix: B", "author": {"name": "B"}},
        {"message": "docs: C", "author": {"name": "C"}},
    ],
}, extra_env={"DINGTALK_MAX_COMMITS": "1"})
text = (payload or {}).get("markdown", {}).get("text", "")
check("只显示1条", "feat: A" in text and "fix: B" not in text)
check("显示/共 标注", "显示 **1** 条 / 共 **3** 条" in text, text)
check("无空 diff 链接", "View diff" not in text)

# ── 3. PR opened ───────────────────────────────────────────
print("[3] PR opened")
rc, out, payload = run_event("pull_request", {
    "action": "opened",
    "pull_request": {
        "number": 42, "title": "Add feature X", "html_url": "https://github.com/x/pull/42",
        "user": {"login": "alice"}, "head": {"ref": "feat-x"}, "base": {"ref": "main"},
        "labels": [{"name": "bug"}, {"name": "enhancement"}],
        "body": "实现 X，\n多行描述",
    },
})
text = (payload or {}).get("markdown", {}).get("text", "")
check("rc=0", rc == 0)
check("opened 标签", "🟢 新建 / Opened" in text)
check("分支方向", "feat-x → main" in text)
check("labels", "`bug` · `enhancement`" in text)
check("body 预览", "实现 X" in text)
check("PR 链接", "View PR" in text)

# ── 4. PR merged ───────────────────────────────────────────
print("[4] PR merged")
rc, out, payload = run_event("pull_request", {
    "action": "closed",
    "pull_request": {"number": 43, "title": "Merged PR", "html_url": "https://github.com/x/pull/43",
                     "user": {"login": "bob"}, "head": {"ref": "a"}, "base": {"ref": "main"},
                     "labels": [], "body": "", "merged": True},
})
text = (payload or {}).get("markdown", {}).get("text", "")
check("已合并标签", "🟣 已合并 / Merged" in text, text)

# ── 5. issue closed ────────────────────────────────────────
print("[5] issue closed")
rc, out, payload = run_event("issues", {
    "action": "closed",
    "issue": {"number": 7, "title": "登录失败", "html_url": "https://github.com/x/issue/7",
              "user": {"login": "carol"}, "labels": [{"name": "bug"}], "body": "报错信息: xxx"},
})
text = (payload or {}).get("markdown", {}).get("text", "")
check("closed 标签", "✅ 关闭 / Closed" in text)
check("body 截断含内容", "报错信息: xxx" in text)

# ── 6. release published（含 changelog + max_bytes 截断）────
print("[6] release published")
long_body = "## Changelog\n\n" + "\n".join(f"- item {i}" for i in range(500))
rc, out, payload = run_event("release", {
    "action": "published",
    "release": {"tag_name": "v2.0.0", "name": "v2.0.0", "body": long_body,
                "html_url": "https://github.com/x/releases/v2.0.0",
                "author": {"login": "dave"}, "prerelease": False, "draft": False},
})
text = (payload or {}).get("markdown", {}).get("text", "")
check("release 标题", "Release v2.0.0" in (payload or {}).get("markdown", {}).get("title", ""))
check("版本号", "`v2.0.0`" in text)
check("changelog 截断(≤5KB)", len(text.encode("utf-8")) < 6000, f"len={len(text.encode('utf-8'))}")
check("截断标记", "…" in text or "content truncated" in text)

# ── 7. PR review ───────────────────────────────────────────
print("[7] PR review")
rc, out, payload = run_event("pull_request_review", {
    "action": "submitted",
    "review": {"state": "approved", "user": {"login": "eve"}, "body": "LGTM"},
    "pull_request": {"number": 50, "title": "Review me", "html_url": "https://github.com/x/pull/50"},
})
text = (payload or {}).get("markdown", {}).get("text", "")
check("approved 图标", "✅ PR 审查 已批准 / Approved" in text)
check("审查人", "**eve**" in text)

# ── 8. workflow_run success ────────────────────────────────
print("[8] workflow_run success")
rc, out, payload = run_event("workflow_run", {
    "workflow_run": {"name": "CI", "conclusion": "success", "html_url": "https://github.com/x/actions/1",
                     "head_branch": "main", "actor": {"login": "frank"}},
})
text = (payload or {}).get("markdown", {}).get("text", "")
check("成功图标", "✅ 工作流 成功 / Success" in text)
check("触发者", "**frank**" in text)

# ── 9. 未支持事件 fallback ─────────────────────────────────
print("[9] 未知事件 fallback")
rc, out, payload = run_event("star", {"action": "created", "repository": {"full_name": "x/y"}})
text = (payload or {}).get("markdown", {}).get("text", "")
check("fallback 显示事件名", "`star`" in text)

# ── 10. mention 参数 ───────────────────────────────────────
print("[10] mention 参数")
rc, out, payload = run_event("push", {
    "commits": [{"message": "feat: x", "author": {"name": "a"}}],
}, extra_env={
    "DINGTALK_MENTION_USERS": "uid1, uid2",
    "DINGTALK_MENTION_MOBILES": "13800000000",
    "DINGTALK_MENTION_ALL": "true",
})
text = (payload or {}).get("markdown", {}).get("text", "")
at = (payload or {}).get("at", {})
check("text 含 @uid", "@uid1" in text and "@uid2" in text)
check("text 含 @手机号", "@13800000000" in text)
check("text 含 @all", "@all" in text)
check("at.atUserIds", at.get("atUserIds") == ["uid1", "uid2"], str(at))
check("at.atMobiles", at.get("atMobiles") == ["13800000000"], str(at))
check("at.isAtAll", at.get("isAtAll") is True, str(at))

# ── 11. 边界：无 commits / 空 body / MENTION_ALL 大小写 ─────
print("[11] 边界：空 push + MENTION_ALL=true")
rc, out, payload = run_event("push", {"compare": "", "commits": []},
                             extra_env={"DINGTALK_MENTION_ALL": "True"})
text = (payload or {}).get("markdown", {}).get("text", "")
check("空 commits 不崩", rc == 0, f"rc={rc} {out}")
check("空 push 不输出汇总行", "⋯ 共" not in text, text)
check("提交数正常显示", "**0**" in text, text)
check("MENTION_ALL True 生效", "@all" in text, text)

# ── 12. 非法 max_commits fallback ──────────────────────────
print("[12] 非法 max_commits")
rc, out, payload = run_event("push", {"commits": [{"message": "feat: a", "author": {"name": "a"}}]},
                             extra_env={"DINGTALK_MAX_COMMITS": "abc"})
check("fallback 0 不崩", rc == 0, f"rc={rc} out={out}")
check("警告输出", "不是有效数字" in out, out)

# ── 13. 无 webhook 报错退出 ─────────────────────────────────
print("[13] 缺 webhook")
env = dict(os.environ)
env.update({"DINGTALK_WEBHOOK": "", "GITHUB_EVENT_NAME": "push",
            "GITHUB_EVENT_PATH": "/tmp/nonexistent.json"})
proc = subprocess.run([sys.executable, SCRIPT], capture_output=True, text=True, env=env, timeout=30)
check("rc=1", proc.returncode == 1, f"rc={proc.returncode}")
check("报错提示", "未配置 DINGTALK_WEBHOOK" in proc.stderr, proc.stderr)

# ── 14. 事件文件缺失 ────────────────────────────────────────
print("[14] 事件文件缺失")
env = dict(os.environ)
env.update({"DINGTALK_WEBHOOK": WEBHOOK, "GITHUB_EVENT_NAME": "push",
            "GITHUB_EVENT_PATH": "/tmp/definitely-not-exist.json"})
proc = subprocess.run([sys.executable, SCRIPT], capture_output=True, text=True, env=env, timeout=30)
check("rc=1", proc.returncode == 1, f"rc={proc.returncode}")
check("报错提示", "事件文件不存在" in proc.stderr, proc.stderr)

server.shutdown()
print(f"\n===== 结果: {PASS} 通过 / {FAIL} 失败 =====")
sys.exit(1 if FAIL else 0)
