# ruff: noqa: E501
from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.config import get_settings
from app.db.models import NotificationType, Submission, SubmissionStatus, TestCase, TestVisibility
from app.db.session import SessionLocal
from app.execution.celery_app import celery_app
from app.gamification.service import reward_submission
from app.leaderboards.service import invalidate_leaderboard_cache
from app.notifications.service import create_notification

RUNNERS = {
    "python": ("python:3.12-alpine", "python", "runner.py"),
    "javascript": ("node:22-alpine", "node", "runner.js"),
}
PYTHON_RUNNER = """import json,sys
payload=json.load(sys.stdin); scope={}; exec(compile(payload['source'],'source.py','exec'),scope); solve=scope.get('solve')
out=[]
for test in payload['tests']:
 try: out.append({'passed': solve(*test['input']) == test['expected']})
 except Exception as e: out.append({'passed':False,'error':type(e).__name__+': '+str(e)})
print(json.dumps(out))
"""
JS_RUNNER = """const fs=require('fs'),vm=require('vm');const payload=JSON.parse(fs.readFileSync(0,'utf8'));let s={};vm.createContext(s);vm.runInContext(payload.source,s,{timeout:1000});let solve=s.solve;let out=[];for(const t of payload.tests){try{out.push({passed:JSON.stringify(solve(...t.input))===JSON.stringify(t.expected)})}catch(e){out.push({passed:false,error:e.name+': '+e.message})}}console.log(JSON.stringify(out));"""


def execute(language: str, source: str, tests: list[dict]) -> list[dict]:
    image, command, _ = RUNNERS[language]
    runner = PYTHON_RUNNER if language == "python" else JS_RUNNER
    process = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--memory",
            f"{get_settings().execution_memory_mb}m",
            "--cpus",
            "0.5",
            "--pids-limit",
            "64",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=16m",
            "--user",
            "65534:65534",
            "-i",
            image,
            command,
            "-c" if language == "python" else "-e",
            runner,
        ],
        input=json.dumps({"source": source, "tests": tests}),
        text=True,
        capture_output=True,
        timeout=get_settings().execution_timeout_seconds + 2,
        check=False,
    )
    if process.returncode != 0:
        return [
            {"passed": False, "error": (process.stderr or "Runtime error")[-2000:]} for _ in tests
        ]
    return json.loads(process.stdout)


@celery_app.task(name="codele.evaluate_submission")
def evaluate_submission(submission_id: str) -> None:
    with SessionLocal() as db:
        notification_ids: list[UUID] = []
        submission = db.scalar(
            select(Submission).where(Submission.id == UUID(submission_id)).with_for_update()
        )
        if submission is None or submission.status != SubmissionStatus.QUEUED:
            return
        submission.status = SubmissionStatus.RUNNING
        db.commit()
        tests = list(
            db.scalars(
                select(TestCase)
                .where(TestCase.question_version_id == submission.question_version_id)
                .order_by(TestCase.position)
            )
        )
        payload = [
            {
                "input": test.input_data
                if isinstance(test.input_data, list)
                else [test.input_data],
                "expected": test.expected_output,
            }
            for test in tests
        ]
        try:
            results = execute(submission.language.value, submission.source_code, payload)
            passed = sum(result.get("passed", False) for result in results)
            submission.status = (
                SubmissionStatus.PASSED if passed == len(tests) else SubmissionStatus.FAILED
            )
            submission.passed_test_count = passed
            submission.total_test_count = len(tests)
            submission.test_results = {
                "public": [
                    {"position": test.position, **result}
                    for test, result in zip(tests, results)
                    if test.visibility == TestVisibility.PUBLIC
                ],
                "hidden": {
                    "passed": sum(
                        result.get("passed", False)
                        for test, result in zip(tests, results)
                        if test.visibility == TestVisibility.HIDDEN
                    ),
                    "total": sum(1 for test in tests if test.visibility == TestVisibility.HIDDEN),
                },
            }
            if submission.status == SubmissionStatus.PASSED:
                notification_ids.extend(reward_submission(db, submission))
        except subprocess.TimeoutExpired:
            submission.status = SubmissionStatus.ERROR
            submission.test_results = {"error": "Execution timed out"}
        except Exception:
            submission.status = SubmissionStatus.ERROR
            submission.test_results = {"error": "Execution worker failed"}
        submission.evaluated_at = datetime.now(UTC)
        if submission.status == SubmissionStatus.PASSED:
            title = "Submission passed"
            body = f"Your solution passed all {submission.total_test_count or 0} tests."
        elif submission.status == SubmissionStatus.FAILED:
            title = "Submission needs another try"
            body = (
                f"Your solution passed {submission.passed_test_count or 0} of "
                f"{submission.total_test_count or 0} tests."
            )
        else:
            title = "Submission could not be evaluated"
            body = "Your code did not finish safely. Review the execution details and try again."
        notification_id = create_notification(
            db,
            user_id=submission.user_id,
            notification_type=NotificationType.SUBMISSION,
            title=title,
            body=body,
            link="/submissions",
            event_key=f"submission-result:{submission.id}",
        )
        if notification_id is not None:
            notification_ids.append(notification_id)
        db.commit()
        from app.notifications.tasks import deliver_notification

        for notification_id in notification_ids:
            deliver_notification.delay(str(notification_id))
        if submission.status == SubmissionStatus.PASSED:
            invalidate_leaderboard_cache()
