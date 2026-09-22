from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.db.models import (
    DailyAssignment,
    Level,
    ProgrammingLanguage,
    QuestionHint,
    QuestionVersion,
    Submission,
    SubmissionStatus,
    User,
)
from app.db.models import (
    TestCase as DatabaseTestCase,
)
from app.db.models import (
    TestVisibility as DatabaseTestVisibility,
)
from app.learning.router import get_submission_review
from app.learning.schemas import HintInput, QuestionVersionInput
from app.learning.schemas import TestCaseInput as CaseInput
from app.learning.service import challenge_response


def question_version_input() -> dict:
    return {
        "title": "Sum two values",
        "statement_markdown": "Return the sum.",
        "level": Level.ROOKIE,
        "category_id": uuid4(),
        "difficulty": 1,
        "starter_code": {"python": "def solve(a, b):\n    pass"},
        "solution_code": {"python": "def solve(a, b):\n    return a + b"},
        "public_tests": [CaseInput(position=1, input_data=[1, 2], expected_output=3)],
        "hidden_tests": [CaseInput(position=2, input_data=[10, 4], expected_output=14)],
        "hints": [
            HintInput(position=1, content_markdown="Use +"),
            HintInput(position=2, content_markdown="Return the result"),
            HintInput(position=3, content_markdown="Both inputs are integers"),
        ],
    }


def test_question_input_rejects_test_position_collision() -> None:
    payload = question_version_input()
    payload["hidden_tests"] = [CaseInput(position=1, input_data=[10, 4], expected_output=14)]

    with pytest.raises(ValidationError, match="unique across public and hidden"):
        QuestionVersionInput(**payload)


def test_question_input_accepts_multiple_public_and_hidden_tests() -> None:
    payload = question_version_input()
    payload["public_tests"] = [
        CaseInput(position=1, input_data=[1, 2], expected_output=3),
        CaseInput(position=2, input_data=[4, 5], expected_output=9),
    ]
    payload["hidden_tests"] = [
        CaseInput(position=3, input_data=[10, 4], expected_output=14),
        CaseInput(position=4, input_data=[0, 0], expected_output=0),
    ]

    question = QuestionVersionInput(**payload)

    assert len(question.public_tests) == 2
    assert len(question.hidden_tests) == 2


def test_question_input_rejects_an_unrenderable_walkthrough_trace() -> None:
    payload = question_version_input()
    payload["solution_trace"] = [
        {
            "step": 1,
            "array": [1, 2],
            "cursor": 0,
            "note_en": "Start here.",
            "note_ml": "ഇവിടെ തുടങ്ങുക.",
        },
        {
            "array": [1, 2],
            "cursor": 1,
            "note_en": "Continue.",
            "note_ml": "തുടരുക.",
        },
    ]

    with pytest.raises(ValidationError, match="positive integer step"):
        QuestionVersionInput(**payload)


def test_question_input_accepts_bilingual_walkthrough_content() -> None:
    payload = question_version_input()
    payload.update(
        {
            "explanation_en": "Track each number and its complement.",
            "explanation_ml": "ഓരോ സംഖ്യയും അതിന്റെ കോംപ്ലിമെന്റും പരിശോധിക്കുക.",
            "solution_trace": [
                {
                    "step": 1,
                    "array": [2, 7],
                    "cursor": 0,
                    "note_en": "Start with an empty lookup map.",
                    "note_ml": "ശൂന്യമായ lookup map-ൽ തുടങ്ങുക.",
                },
                {
                    "step": 2,
                    "array": [2, 7],
                    "cursor": 1,
                    "note_en": "The complement of 7 is already known.",
                    "note_ml": "7-ന്റെ complement മുമ്പേ അറിയാം.",
                },
            ],
            "solution_notes_en": ["Start with an empty map.", "Store the current value."],
            "solution_notes_ml": ["ശൂന്യമായ മാപ്പിൽ തുടങ്ങുക.", "നിലവിലെ മൂല്യം സൂക്ഷിക്കുക."],
        }
    )

    question = QuestionVersionInput(**payload)

    assert question.solution_trace[1]["cursor"] == 1


def test_challenge_response_redacts_solution_and_hidden_tests() -> None:
    version = QuestionVersion(
        id=uuid4(),
        version_number=1,
        title="Sum two values",
        statement_markdown="Return the sum.",
        examples=[],
        constraints_markdown=None,
        category_id=uuid4(),
        level=Level.ROOKIE,
        topic="variables",
        difficulty=1,
        starter_code={"python": "def solve(a, b):\n    pass"},
        solution_code={"python": "def solve(a, b):\n    return a + b"},
    )
    version.test_cases = [
        DatabaseTestCase(
            position=1,
            visibility=DatabaseTestVisibility.PUBLIC,
            input_data=[1, 2],
            expected_output=3,
            explanation="small values",
        ),
        DatabaseTestCase(
            position=2,
            visibility=DatabaseTestVisibility.HIDDEN,
            input_data=[10, 4],
            expected_output=14,
        ),
    ]
    version.hints = [
        QuestionHint(position=1, content_markdown="Use +", xp_penalty=0),
        QuestionHint(position=2, content_markdown="Return the result", xp_penalty=0),
        QuestionHint(position=3, content_markdown="Both inputs are integers", xp_penalty=0),
    ]
    assignment = DailyAssignment(
        id=uuid4(),
        assignment_date=date(2026, 9, 16),
        level=Level.ROOKIE,
        question_version=version,
    )

    response = challenge_response(assignment)

    assert response.starter_code == {"python": "def solve(a, b):\n    pass"}
    assert [test.position for test in response.public_tests] == [1]
    assert "solution_code" not in response.model_dump()
    assert response.public_tests[0].expected_output == 3


class SubmissionReviewDb:
    """Minimal scalar-only session used to exercise the serialization boundary."""

    def __init__(self, submission: Submission) -> None:
        self.submission = submission

    def scalar(self, _statement: object) -> Submission:
        return self.submission


def test_submission_review_redacts_hidden_tests_and_reference_solution() -> None:
    user = User(id=uuid4(), email="learner@example.com", display_name="learner")
    version = QuestionVersion(
        id=uuid4(),
        version_number=1,
        title="Historical sum",
        statement_markdown="Add the values.",
        examples=[],
        constraints_markdown=None,
        category_id=uuid4(),
        level=Level.ROOKIE,
        topic="Arrays",
        difficulty=1,
        starter_code={"python": "def solve(a, b):\n    pass"},
        solution_code={"python": "return a + b  # secret reference"},
    )
    version.test_cases = [
        DatabaseTestCase(
            position=1,
            visibility=DatabaseTestVisibility.PUBLIC,
            input_data=[1, 2],
            expected_output=3,
        ),
        DatabaseTestCase(
            position=2,
            visibility=DatabaseTestVisibility.HIDDEN,
            input_data=[99, 1],
            expected_output=100,
        ),
    ]
    submission = Submission(
        id=uuid4(),
        user_id=user.id,
        question_version_id=version.id,
        idempotency_key="review-test",
        language=ProgrammingLanguage.PYTHON,
        source_code="def solve(a, b):\n    return a + b",
        status=SubmissionStatus.PASSED,
        attempt_number=1,
        created_at=datetime.now(UTC),
        question_version=version,
    )

    response = get_submission_review(submission.id, user, SubmissionReviewDb(submission))
    payload = response.model_dump_json()

    assert response.source_code == submission.source_code
    assert [test.position for test in response.question.public_tests] == [1]
    assert "secret reference" not in payload
    assert "[99,1]" not in payload.replace(" ", "")
