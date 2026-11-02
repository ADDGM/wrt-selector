import contextlib
from http.client import HTTPException
import io
import json
from pathlib import Path
import sys
import ssl
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from notify_telegram import notify, render_message


class TelegramNotificationTest(unittest.TestCase):
    def setUp(self):
        self.environment = {
            "TELEGRAM_TOKEN": "12345:test-token", "TELEGRAM_TO": "-1000001",
            "NOTIFY_TITLE": "Pages 检查与部署", "NOTIFY_REF": "develop",
            "NOTIFY_SHA": "a" * 40, "GITHUB_REPOSITORY": "owner/repo",
            "GITHUB_EVENT_NAME": "push", "GITHUB_ACTOR": "maintainer",
            "NOTIFY_RUN_URL": "https://github.com/owner/repo/actions/runs/1",
            "NOTIFY_RESULT_URL": "https://owner.github.io/repo/",
        }
        self.set_results(source="success", quality="success", test="success", deploy="success")

    def set_results(self, **results):
        self.environment["NOTIFY_RESULTS"] = json.dumps({
            name: {"result": result, "outputs": {}} for name, result in results.items()
        })

    def execute(self, response=b'{"ok":true}', error=None, dry_run=False, status=200):
        output = io.StringIO()
        with patch("notify_telegram.HTTPSConnection") as request, contextlib.redirect_stdout(output):
            request.return_value.request.side_effect = error
            reply = io.BytesIO(response)
            reply.status = status
            request.return_value.getresponse.return_value = reply
            result = notify(self.environment, dry_run=dry_run)
        return result, output.getvalue(), request

    def test_success_reports_all_jobs_and_actual_commit(self):
        message = render_message(self.environment)
        self.assertIn("整体结果：成功", message)
        self.assertIn("Pages 部署：成功", message)
        self.assertIn("源码提交：" + "a" * 40, message)
        self.assertIn("查看结果：https://owner.github.io/repo/", message)

    def test_failure_cancellation_skip_and_unknown_are_not_success(self):
        for status, label in [("failure", "失败"), ("cancelled", "取消"),
                              ("skipped", "未执行"), ("unknown", "未知")]:
            with self.subTest(status=status):
                self.set_results(source="success", quality=status, test="success", deploy="skipped")
                message = render_message(self.environment)
                self.assertIn("整体结果：" + label, message)
                self.assertNotIn("查看结果：", message)
                self.assertIn("/actions/runs/1", message)

    def test_release_uses_resolved_tag_and_source(self):
        self.environment.update(NOTIFY_TITLE="Release 发布", NOTIFY_REF="site-v1.0.0",
                                NOTIFY_RESULT_URL="https://github.com/owner/repo/releases/tag/site-v1.0.0")
        self.set_results(resolve="success", quality="success", test="success", publish="success")
        message = render_message(self.environment)
        self.assertIn("分支/标签：site-v1.0.0", message)
        self.assertIn("Release 发布：成功", message)
        self.assertIn("/releases/tag/site-v1.0.0", message)

    def test_empty_or_malformed_results_do_not_send(self):
        for results in ["{}", "[]", "invalid", '{"test":null}', '{"test":{"result":"wrong"}}']:
            with self.subTest(results=results):
                self.environment["NOTIFY_RESULTS"] = results
                result, output, request = self.execute()
                self.assertEqual(result, 1)
                request.assert_not_called()
                self.assertNotIn("发送成功", output)

    def test_missing_either_secret_skips_without_network(self):
        for name in ["TELEGRAM_TO", "TELEGRAM_TOKEN"]:
            with self.subTest(name=name), patch.dict(self.environment, {name: ""}):
                result, output, request = self.execute()
                self.assertEqual(result, 0)
                self.assertIn("已跳过", output)
                request.assert_not_called()

    def test_plain_json_payload_and_api_acknowledgment(self):
        self.environment["NOTIFY_REF"] = "feature/[literal]*中文"
        result, output, request = self.execute()
        self.assertEqual(result, 0)
        request.assert_called_once()
        self.assertEqual(request.call_args.args, ("api.telegram.org",))
        self.assertEqual(request.call_args.kwargs["timeout"], 20)
        tls = request.call_args.kwargs["context"]
        self.assertEqual(tls.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(tls.check_hostname)
        sent = request.return_value.request.call_args
        payload = json.loads(sent.kwargs["body"])
        self.assertEqual(sent.args, ("POST", "/bot12345:test-token/sendMessage"))
        self.assertEqual(sent.kwargs["headers"], {"Content-Type": "application/json"})
        request.return_value.close.assert_called_once()
        self.assertEqual(payload["chat_id"], "-1000001")
        self.assertNotIn("parse_mode", payload)
        self.assertIn("feature/[literal]*中文", payload["text"])
        self.assertEqual(payload["link_preview_options"], {"is_disabled": True})
        self.assertIn("API 已确认", output)
        self.assertNotIn(self.environment["TELEGRAM_TOKEN"], output)
        self.assertNotIn(self.environment["TELEGRAM_TO"], output)

    def test_errors_never_print_token_chat_id_or_server_body(self):
        sensitive = self.environment["TELEGRAM_TOKEN"] + " " + self.environment["TELEGRAM_TO"]
        for error in [HTTPException(sensitive), OSError(sensitive), TimeoutError(sensitive)]:
            with self.subTest(error=type(error).__name__):
                result, output, _ = self.execute(error=error)
                self.assertEqual(result, 1)
                self.assertNotIn(sensitive, output)
                self.assertNotIn(self.environment["TELEGRAM_TOKEN"], output)
                self.assertNotIn(self.environment["TELEGRAM_TO"], output)
        for response in [json.dumps({"ok": False, "description": sensitive}).encode(), b"not json", b"[]"]:
            result, output, _ = self.execute(response=response)
            self.assertEqual(result, 1)
            self.assertNotIn(sensitive, output)

    def test_http_errors_and_redirects_fail_without_following_or_printing_body(self):
        sensitive = self.environment["TELEGRAM_TOKEN"] + " " + self.environment["TELEGRAM_TO"]
        for status in [301, 302, 401, 403, 429, 500]:
            with self.subTest(status=status):
                result, output, request = self.execute(response=sensitive.encode(), status=status)
                self.assertEqual(result, 1)
                self.assertIn(f"HTTP {status}", output)
                self.assertNotIn(sensitive, output)
                request.return_value.request.assert_called_once()
                request.return_value.close.assert_called_once()

    def test_dry_run_does_not_send_and_message_is_bounded(self):
        self.environment["NOTIFY_TITLE"] = "标" * 10000
        result, output, request = self.execute(dry_run=True)
        self.assertEqual(result, 0)
        self.assertLessEqual(len(output), 4096)
        request.assert_not_called()
        self.assertNotIn(self.environment["TELEGRAM_TOKEN"], output)
        self.assertNotIn(self.environment["TELEGRAM_TO"], output)


if __name__ == "__main__":
    unittest.main()
