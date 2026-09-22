from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import DailyAssignment, QuestionVersion, TestVisibility
from app.learning.schemas import ChallengeResponse, LearnerHintResponse, PublicTestCaseResponse


def load_assignment_for_challenge(session: Session, assignment_id) -> DailyAssignment | None:
    """Load only the version snapshot needed to serve a learner challenge."""
    statement = (
        select(DailyAssignment)
        .where(DailyAssignment.id == assignment_id)
        .options(
            selectinload(DailyAssignment.question_version).selectinload(QuestionVersion.test_cases),
            selectinload(DailyAssignment.question_version).selectinload(QuestionVersion.hints),
        )
    )
    return session.scalar(statement)


def challenge_response(assignment: DailyAssignment) -> ChallengeResponse:
    """Return a learner-safe snapshot: hidden tests and solutions never leave the API."""
    version = assignment.question_version
    public_tests = sorted(
        (test for test in version.test_cases if test.visibility == TestVisibility.PUBLIC),
        key=lambda test: test.position,
    )
    hints = sorted(version.hints, key=lambda hint: hint.position)
    return ChallengeResponse(
        assignment_id=assignment.id,
        assignment_date=assignment.assignment_date,
        question_version_id=version.id,
        title=version.title,
        statement_markdown=version.statement_markdown,
        examples=version.examples,
        constraints_markdown=version.constraints_markdown,
        level=version.level,
        category_id=version.category_id,
        topic=version.topic,
        difficulty=version.difficulty,
        starter_code=version.starter_code,
        public_tests=[
            PublicTestCaseResponse(
                position=test.position,
                input_data=test.input_data,
                expected_output=test.expected_output,
                explanation=test.explanation,
            )
            for test in public_tests
        ],
        hints=[
            LearnerHintResponse(
                position=hint.position,
                xp_penalty=hint.xp_penalty,
            )
            for hint in hints
        ],
    )
