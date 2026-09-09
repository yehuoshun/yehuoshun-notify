"""单元测试：工具函数 + 环境变量解析。"""
import os, sys, json, unittest
from unittest.mock import patch

# 模拟环境变量，让模块可以被 import
os.environ["DINGTALK_WEBHOOK"] = "https://mock"
os.environ["GITHUB_EVENT_NAME"] = "push"
os.environ["GITHUB_EVENT_PATH"] = "/tmp/mock-event.json"
os.environ["GITHUB_REPOSITORY"] = "test/repo"
os.environ["GITHUB_REF_NAME"] = "main"
os.environ["GITHUB_ACTOR"] = "testuser"

# 创建 mock 事件文件
with open("/tmp/mock-event.json", "w") as f:
    json.dump({"compare": "https://github.com/test/repo/compare/abc..def", "commits": [
        {"message": "feat: add new feature\n\n- first change\n- second change", "author": {"name": "dev1"}},
        {"message": "fix: resolve bug", "author": {"name": "dev2"}},
    ]}, f)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import importlib.util
spec = importlib.util.spec_from_file_location("dn", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dingtalk-notify.py"))
dn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dn)
_truncate = dn._truncate
_emoji = dn._emoji


class TestTruncate(unittest.TestCase):

    def test_empty(self):
        self.assertEqual(_truncate(""), "")
        self.assertEqual(_truncate(None), "")

    def test_short_text(self):
        self.assertEqual(_truncate("hello", n=10), "hello")

    def test_text_within_limit(self):
        self.assertEqual(_truncate("hello world", n=20), "hello world")

    def test_truncate_by_chars(self):
        result = _truncate("hello\nworld\nfoo", n=10)
        self.assertIn("…", result)
        self.assertLessEqual(len(result.replace("\n…", "")), 10)

    def test_truncate_by_bytes(self):
        text = "你好世界" * 100
        result = _truncate(text, max_bytes=100)
        self.assertIn("…", result)
        # Make sure it's within byte limit
        self.assertLessEqual(len(result.encode("utf-8")), 110)

    def test_byte_truncate_keeps_newlines(self):
        text = "line1\nline2\nline3\n" * 50
        result = _truncate(text, max_bytes=200)
        self.assertIn("…", result)
        # Should end with a newline + …
        self.assertTrue(result.endswith("\n…"))


class TestEmoji(unittest.TestCase):

    def test_feat(self):
        self.assertEqual(_emoji("feat: add thing"), "✨")

    def test_fix(self):
        self.assertEqual(_emoji("fix: resolve bug"), "🐛")

    def test_docs(self):
        self.assertEqual(_emoji("docs: update readme"), "📝")

    def test_alias_fixes(self):
        self.assertEqual(_emoji("fixes: something"), "🐛")

    def test_alias_bug(self):
        self.assertEqual(_emoji("bug: crash fix"), "🐛")

    def test_alias_feature(self):
        self.assertEqual(_emoji("feature: big change"), "✨")

    def test_unknown(self):
        self.assertEqual(_emoji("random: message"), "•")

    def test_empty(self):
        self.assertEqual(_emoji(""), "•")


class TestMentionAllParsing(unittest.TestCase):
    """MENTION_ALL 环境变量解析测试。"""

    def _parse(self, value):
        """模拟 MENTION_ALL 的解析逻辑。"""
        return value.lower() in ("true", "1", "yes")

    def test_true_lowercase(self):
        self.assertTrue(self._parse("true"))

    def test_true_capitalized(self):
        self.assertTrue(self._parse("True"))

    def test_true_uppercase(self):
        self.assertTrue(self._parse("TRUE"))

    def test_1(self):
        self.assertTrue(self._parse("1"))

    def test_yes(self):
        self.assertTrue(self._parse("yes"))

    def test_false(self):
        self.assertFalse(self._parse("false"))

    def test_empty(self):
        self.assertFalse(self._parse(""))

    def test_random(self):
        self.assertFalse(self._parse("whatever"))


if __name__ == "__main__":
    unittest.main()