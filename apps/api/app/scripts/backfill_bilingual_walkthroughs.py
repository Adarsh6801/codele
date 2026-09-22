"""Create immutable bilingual-learning versions for the starter question library.

Existing submissions and schedules keep their original question_version_id.
For every library question missing a learning path, this script creates a new
READY version with cloned tests/hints and the curated bilingual walkthrough.
"""

from __future__ import annotations

from copy import deepcopy

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.models import Question, QuestionHint, QuestionVersion, QuestionVersionStatus, TestCase
from app.db.session import SessionLocal
from app.scripts.question_learning_paths import LEARNING_PATHS


def clone_version(source: QuestionVersion, learning_path: dict[str, object]) -> QuestionVersion:
    version = QuestionVersion(
        question_id=source.question_id,
        version_number=source.version_number + 1,
        title=source.title,
        statement_markdown=source.statement_markdown,
        examples=deepcopy(source.examples),
        constraints_markdown=source.constraints_markdown,
        category_id=source.category_id,
        level=source.level,
        topic=source.topic,
        difficulty=source.difficulty,
        starter_code=deepcopy(source.starter_code),
        solution_code=deepcopy(source.solution_code),
        explanation_markdown=source.explanation_markdown,
        explanation_en=str(learning_path["en"]),
        explanation_ml=str(learning_path["ml"]),
        solution_trace=deepcopy(learning_path["trace"]),
        solution_notes_en=deepcopy(learning_path["notes_en"]),
        solution_notes_ml=deepcopy(learning_path["notes_ml"]),
        solution_video_url=source.solution_video_url,
        solution_image_urls=deepcopy(source.solution_image_urls),
        complexity_notes=source.complexity_notes,
        alternative_approaches=deepcopy(source.alternative_approaches),
        status=QuestionVersionStatus.READY,
        created_by_id=source.created_by_id,
    )
    for test in source.test_cases:
        version.test_cases.append(
            TestCase(
                position=test.position,
                visibility=test.visibility,
                input_data=deepcopy(test.input_data),
                expected_output=deepcopy(test.expected_output),
                explanation=test.explanation,
            )
        )
    for hint in source.hints:
        version.hints.append(
            QuestionHint(
                position=hint.position,
                content_markdown=hint.content_markdown,
                xp_penalty=hint.xp_penalty,
            )
        )
    return version


def main() -> None:
    upgraded = 0
    skipped = 0
    with SessionLocal() as session:
        questions = list(
            session.scalars(
                select(Question)
                .where(Question.slug.in_(LEARNING_PATHS))
                .options(
                    selectinload(Question.versions).selectinload(QuestionVersion.test_cases),
                    selectinload(Question.versions).selectinload(QuestionVersion.hints),
                )
            )
        )
        for question in questions:
            source = max(question.versions, key=lambda version: version.version_number)
            if source.explanation_en and source.explanation_ml and source.solution_trace:
                skipped += 1
                continue
            session.add(clone_version(source, LEARNING_PATHS[question.slug]))
            upgraded += 1
        session.commit()
    print(f"Created {upgraded} bilingual walkthrough version(s); {skipped} already complete.")


if __name__ == "__main__":
    main()
