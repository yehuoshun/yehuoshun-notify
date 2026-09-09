"""集成测试：模拟各事件的消息组装流程。"""
import os, sys, json, unittest
from unittest.mock import patch

os.environ["DINGTALK_WEBHOOK"] = "https://mock"
os.environ["GITHUB_REPOSITORY"] = "test/repo"
os.environ["GITHUB_REF_NAME"] = "main"
os.environ["GITHUB_ACTOR"] = "testuser"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import importlib.util
spec = importlib.util.spec_from_file_location("dn",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dingtalk-notify.py"))
dn = importlib.util.module_from_spec(spec)

# 各事件测试用的 mock 数据
EVENT_FIXTURES = {
    "push": {
        "compare": "https://github.com/test/repo/compare/abc..def",
        "commits": [
            {"message": "feat: add new feature\n\n- change 1\n- change 2", "author": {"name": "dev1"}},
            {"message": "fix: resolve bug", "author": {"name": "dev2"}},
        ]
    },
    "pull_request": {
        "action": "opened",
        "pull_request": {
            "number": 42,
            "title": "Add awesome feature",
            "user": {"login": "dev1"},
            "head": {"ref": "feature/awesome"},
            "base": {"ref": "main"},
            "html_url": "https://github.com/test/repo/pull/42",
            "body": "This PR adds an awesome feature.\n\n## Changes\n- thing 1\n- thing 2",
            "labels": [{"name": "enhancement"}, {"name": "frontend"}],
        }
    },
    "pull_request_review": {
        "action": "submitted",
        "pull_request": {
            "number": 42,
            "title": "Add awesome feature",
            "html_url": "https://github.com/test/repo/pull/42",
        },
        "review": {
            "state": "approved",
            "user": {"login": "reviewer1"},
            "body": "LGTM! Great work.",
        }
    },
    "issues": {
        "action": "opened",
        "issue": {
            "number": 101,
            "title": "Bug: login broken",
            "user": {"login": "bugreporter"},
            "html_url": "https://github.com/test/repo/issues/101",
            "body": "When I click login, nothing happens.",
            "labels": [{"name": "bug"}, {"name": "urgent"}],
        }
    },
    "release": {
        "action": "published",
        "release": {
            "tag_name": "v2.0.0",
            "name": "v2.0.0",
            "body": "## Changelog\n\n### Features\n- feature 1\n- feature 2\n\n### Fixes\n- fix 1\n",
            "html_url": "https://github.com/test/repo/releases/v2.0.0",
            "author": {"login": "maintainer"},
            "prerelease": False,
            "draft": False,
        }
    },
    "workflow_run": {
        "action": "completed",
        "workflow_run": {
            "name": "CI",
            "conclusion": "success",
            "html_url": "https://github.com/test/repo/actions/runs/123",
            "head_branch": "main",
            "actor": {"login": "devops-bot"},
        }
    },
}


def setUpModule():
    # 导入模块（会执行顶层代码，需要 mock 事件文件）
    pass


class TestPushEvent(unittest.TestCase):
    """Push 事件消息组装。"""

    def setUp(self):
        os.environ["GITHUB_EVENT_NAME"] = "push"
        os.environ["GITHUB_REF_NAME"] = "main"
        os.environ["GITHUB_ACTOR"] = "testuser"

    def _run_push(self, mention_all="false"):
        with open("/tmp/test-event-push.json", "w") as f:
            json.dump(EVENT_FIXTURES["push"], f)
        os.environ["GITHUB_EVENT_PATH"] = "/tmp/test-event-push.json"
        os.environ["DINGTALK_MENTION_ALL"] = mention_all

        # Re-import to refresh event data
        newspec = importlib.util.spec_from_file_location("dn_push",
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dingtalk-notify.py"))
        dn = importlib.util.module_from_spec(newspec)
        newspec.loader.exec_module(dn)
        return dn

    def test_push_contains_repo_and_branch(self):
        dn = self._run_push()
        title, text = dn.push()
        self.assertIn("test/repo", text)
        self.assertIn("main", text)
        self.assertIn("testuser", text)

    def test_push_contains_commits(self):
        dn = self._run_push()
        title, text = dn.push()
        self.assertIn("feat: add new feature", text)
        self.assertIn("fix: resolve bug", text)
        self.assertIn("dev1", text)
        self.assertIn("dev2", text)

    def test_push_contains_diff_link(self):
        dn = self._run_push()
        title, text = dn.push()
        self.assertIn("View diff", text)
        self.assertIn("compare/abc..def", text)

    def test_push_total_count(self):
        dn = self._run_push()
        title, text = dn.push()
        self.assertIn("**2**", text)  # total commits

    def test_push_emoji(self):
        dn = self._run_push()
        title, text = dn.push()
        self.assertIn("✨", text)  # feat
        self.assertIn("🐛", text)  # fix

    def test_push_commit_body(self):
        dn = self._run_push()
        title, text = dn.push()
        self.assertIn("change 1", text)
        self.assertIn("change 2", text)

    def test_push_mention_all(self):
        """@all 由 main() 追加，push() 本身不处理。验证 MENTION_ALL 解析正确即可。"""
        dn = self._run_push(mention_all="True")
        self.assertTrue(dn.MENTION_ALL)


class TestPREvent(unittest.TestCase):
    def setUp(self):
        os.environ["GITHUB_EVENT_NAME"] = "pull_request"

    def _make_dn(self):
        with open("/tmp/test-event-pr.json", "w") as f:
            json.dump(EVENT_FIXTURES["pull_request"], f)
        os.environ["GITHUB_EVENT_PATH"] = "/tmp/test-event-pr.json"
        newspec = importlib.util.spec_from_file_location("dn_pr",
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dingtalk-notify.py"))
        dn = importlib.util.module_from_spec(newspec)
        newspec.loader.exec_module(dn)
        return dn

    def test_pr_opened(self):
        dn = self._make_dn()
        title, text = dn.pull_request()
        self.assertIn("Opened", text)
        self.assertIn("Add awesome feature", text)
        self.assertIn("dev1", text)
        self.assertIn("feature/awesome → main", text)

    def test_pr_labels(self):
        dn = self._make_dn()
        title, text = dn.pull_request()
        self.assertIn("enhancement", text)
        self.assertIn("frontend", text)

    def test_pr_body(self):
        dn = self._make_dn()
        title, text = dn.pull_request()
        self.assertIn("This PR adds", text)


class TestReviewEvent(unittest.TestCase):
    def setUp(self):
        os.environ["GITHUB_EVENT_NAME"] = "pull_request_review"

    def _make_dn(self):
        with open("/tmp/test-event-review.json", "w") as f:
            json.dump(EVENT_FIXTURES["pull_request_review"], f)
        os.environ["GITHUB_EVENT_PATH"] = "/tmp/test-event-review.json"
        newspec = importlib.util.spec_from_file_location("dn_review",
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dingtalk-notify.py"))
        dn = importlib.util.module_from_spec(newspec)
        newspec.loader.exec_module(dn)
        return dn

    def test_review_approved(self):
        dn = self._make_dn()
        title, text = dn.pull_request_review()
        self.assertIn("✅", text)
        self.assertIn("Approved", text)
        self.assertIn("LGTM", text)
        self.assertIn("reviewer1", text)


class TestIssueEvent(unittest.TestCase):
    def setUp(self):
        os.environ["GITHUB_EVENT_NAME"] = "issues"

    def _make_dn(self):
        with open("/tmp/test-event-issue.json", "w") as f:
            json.dump(EVENT_FIXTURES["issues"], f)
        os.environ["GITHUB_EVENT_PATH"] = "/tmp/test-event-issue.json"
        newspec = importlib.util.spec_from_file_location("dn_issue",
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dingtalk-notify.py"))
        dn = importlib.util.module_from_spec(newspec)
        newspec.loader.exec_module(dn)
        return dn

    def test_issue_opened(self):
        dn = self._make_dn()
        title, text = dn.issues()
        self.assertIn("Opened", text)
        self.assertIn("Bug: login broken", text)
        self.assertIn("bugreporter", text)
        self.assertIn("bug", text)
        self.assertIn("urgent", text)
        self.assertIn("nothing happens", text)


class TestReleaseEvent(unittest.TestCase):
    def setUp(self):
        os.environ["GITHUB_EVENT_NAME"] = "release"

    def _make_dn(self):
        with open("/tmp/test-event-release.json", "w") as f:
            json.dump(EVENT_FIXTURES["release"], f)
        os.environ["GITHUB_EVENT_PATH"] = "/tmp/test-event-release.json"
        newspec = importlib.util.spec_from_file_location("dn_release",
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dingtalk-notify.py"))
        dn = importlib.util.module_from_spec(newspec)
        newspec.loader.exec_module(dn)
        return dn

    def test_release_published(self):
        dn = self._make_dn()
        title, text = dn.release()
        self.assertIn("v2.0.0", text)
        self.assertIn("Published", text)
        self.assertIn("maintainer", text)
        self.assertIn("Changelog", text)
        self.assertIn("feature 1", text)

    def test_release_no_prerelease(self):
        dn = self._make_dn()
        title, text = dn.release()
        self.assertIn("🏷️", title)


class TestWorkflowRunEvent(unittest.TestCase):
    def setUp(self):
        os.environ["GITHUB_EVENT_NAME"] = "workflow_run"

    def _make_dn(self):
        with open("/tmp/test-event-workflow.json", "w") as f:
            json.dump(EVENT_FIXTURES["workflow_run"], f)
        os.environ["GITHUB_EVENT_PATH"] = "/tmp/test-event-workflow.json"
        newspec = importlib.util.spec_from_file_location("dn_workflow",
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dingtalk-notify.py"))
        dn = importlib.util.module_from_spec(newspec)
        newspec.loader.exec_module(dn)
        return dn

    def test_workflow_success(self):
        dn = self._make_dn()
        title, text = dn.workflow_run()
        self.assertIn("✅", text)
        self.assertIn("CI", text)
        self.assertIn("success", text)
        self.assertIn("main", text)
        self.assertIn("devops-bot", text)


if __name__ == "__main__":
    unittest.main()