"""Send a plain-text workflow summary without exposing Telegram credentials."""

import argparse
from contextlib import closing
from http.client import HTTPException, HTTPSConnection
import json
import os
from pathlib import Path
import ssl
from urllib.parse import quote

from workflow_utils import configure_console


STATUS = {
    "success": "成功", "failure": "失败", "cancelled": "取消",
    "skipped": "未执行", "unknown": "未知",
}
JOBS = {
    "source": "源码核验", "resolve": "标签与源码核验",
    "quality": "质量检查", "test": "测试与打包",
    "deploy": "Pages 部署", "publish": "Release 发布",
}


def render_message(environment):
    needs = json.loads(environment.get("NOTIFY_RESULTS", "{}"))
    if not isinstance(needs, dict) or not needs:
        raise ValueError("Missing job results")
    results = {name: job.get("result", "unknown") for name, job in needs.items()}
    if any(result not in STATUS for result in results.values()):
        raise ValueError("Invalid job result")
    overall = next((status for status in ("failure", "cancelled", "unknown", "skipped")
                    if status in results.values()), "success")

    def value(name, default="未提供"):
        return " ".join(environment.get(name, default).split())[:256] or default

    lines = [
        "Wrt Selector · " + value("NOTIFY_TITLE"),
        "整体结果：" + STATUS[overall],
        "仓库：" + value("GITHUB_REPOSITORY"),
        "分支/标签：" + value("NOTIFY_REF"),
        "源码提交：" + value("NOTIFY_SHA"),
        "",
    ]
    lines.extend(f"{JOBS.get(name, name)[:80]}：{STATUS[result]}"
                 for name, result in results.items())
    lines.extend([
        "", "运行：" + value("NOTIFY_RUN_URL"),
        "触发：" + value("GITHUB_EVENT_NAME") + " / " + value("GITHUB_ACTOR"),
    ])
    if overall == "success" and environment.get("NOTIFY_RESULT_URL"):
        lines.append("查看结果：" + value("NOTIFY_RESULT_URL"))
    return "\n".join(lines)[:3900]


def report(environment, message):
    print(message)
    if environment.get("GITHUB_STEP_SUMMARY"):
        with Path(environment["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as summary:
            summary.write(message + "\n\n")


def notify(environment, dry_run=False):
    token = environment.get("TELEGRAM_TOKEN", "").strip()
    chat_id = environment.get("TELEGRAM_TO", "").strip()
    if not dry_run and (not token or not chat_id):
        report(environment, "Telegram 通知已跳过：未配置 TELEGRAM_TO 或 TELEGRAM_TOKEN。")
        return 0
    try:
        message = render_message(environment)
        if dry_run:
            print(message)
            return 0
        payload = json.dumps({
            "chat_id": chat_id, "text": message,
            "link_preview_options": {"is_disabled": True},
        }, ensure_ascii=False).encode("utf-8")
        tls = ssl.create_default_context()
        # Python 3.11+ with explicit certificate/hostname checks; the rule flags every HTTPSConnection.
        # nosemgrep: python.lang.security.audit.httpsconnection-detected.httpsconnection-detected
        with closing(HTTPSConnection("api.telegram.org", timeout=20, context=tls)) as connection:
            connection.request(
                "POST", "/bot" + quote(token, safe=":") + "/sendMessage",
                body=payload, headers={"Content-Type": "application/json"},
            )
            response = connection.getresponse()
            if not 200 <= response.status < 300:
                report(environment, f"Telegram 通知失败：HTTP {response.status}；请检查凭证、聊天权限或服务状态。")
                return 1
            result = json.load(response)
        if not isinstance(result, dict) or result.get("ok") is not True:
            raise ValueError("Telegram did not acknowledge delivery")
    except (HTTPException, OSError, ValueError, TypeError, AttributeError):
        report(environment, "Telegram 通知失败：网络、输入或 API 响应异常；未输出敏感错误详情。")
        return 1
    report(environment, "Telegram API 已确认通知发送成功。")
    return 0


if __name__ == "__main__":
    configure_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Render without making a network request")
    raise SystemExit(notify(os.environ, parser.parse_args().dry_run))
