from datetime import date, datetime
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.db.models import (
    DailyAttemptStatus,
    Level,
    ProgrammingLanguage,
    QuestionVersionStatus,
    SubmissionStatus,
)


class ExampleInput(BaseModel):
    input: Any
    output: Any
    explanation: str | None = Field(default=None, max_length=10_000)
    image_url: str | None = Field(default=None, max_length=500)


class TestCaseInput(BaseModel):
    position: int = Field(ge=1)
    input_data: Any
    expected_output: Any
    explanation: str | None = Field(default=None, max_length=10_000)


class HintInput(BaseModel):
    position: int = Field(ge=1)
    content_markdown: str = Field(min_length=1, max_length=20_000)
    xp_penalty: int = Field(default=0, ge=0)


class AlternativeApproachInput(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    summary_markdown: str = Field(min_length=1, max_length=20_000)
    time_complexity: str = Field(min_length=1, max_length=200)
    space_complexity: str = Field(min_length=1, max_length=200)


class QuestionVersionInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    statement_markdown: str = Field(min_length=1, max_length=100_000)
    examples: list[ExampleInput] = Field(default_factory=list)
    constraints_markdown: str | None = Field(default=None, max_length=20_000)
    level: Level
    category_id: UUID
    difficulty: int = Field(ge=1, le=5)
    starter_code: dict[str, str] = Field(default_factory=dict)
    solution_code: dict[str, str] = Field(default_factory=dict)
    explanation_markdown: str | None = Field(default=None, max_length=100_000)
    explanation_en: str | None = Field(default=None, max_length=100_000)
    explanation_ml: str | None = Field(default=None, max_length=100_000)
    solution_trace: list[dict[str, Any]] = Field(default_factory=list, max_length=500)
    solution_notes_en: list[str] = Field(default_factory=list, max_length=500)
    solution_notes_ml: list[str] = Field(default_factory=list, max_length=500)
    solution_video_url: str | None = Field(default=None, max_length=500)
    solution_image_urls: list[str] = Field(default_factory=list, max_length=12)
    complexity_notes: str | None = Field(default=None, max_length=10_000)
    alternative_approaches: list[AlternativeApproachInput] = Field(
        default_factory=list, max_length=5
    )
    public_tests: list[TestCaseInput] = Field(min_length=1)
    hidden_tests: list[TestCaseInput] = Field(min_length=1)
    hints: list[HintInput] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def validate_unique_positions(self) -> "QuestionVersionInput":
        for collection, label in ((self.hints, "hints"),):
            positions = [item.position for item in collection]
            if len(positions) != len(set(positions)):
                raise ValueError(f"{label} must have unique positions")
        test_positions = [test.position for test in self.public_tests + self.hidden_tests]
        if len(test_positions) != len(set(test_positions)):
            raise ValueError("test positions must be unique across public and hidden tests")
        trace_positions: list[int] = []
        for item in self.solution_trace:
            step = item.get("step")
            if not isinstance(step, int) or step < 1:
                raise ValueError("each solution trace item must have a positive integer step")
            if not isinstance(item.get("array"), list):
                raise ValueError("each solution trace item must have an array")
            cursor = item.get("cursor")
            if not isinstance(cursor, int) or cursor < 0:
                raise ValueError("each solution trace item must have a non-negative cursor")
            for note_key in ("note_en", "note_ml"):
                note = item.get(note_key)
                if not isinstance(note, str) or not note.strip():
                    raise ValueError(f"each solution trace item must have a {note_key} explanation")
            trace_positions.append(step)
        if len(trace_positions) != len(set(trace_positions)):
            raise ValueError("solution trace steps must be unique")
        return self

    @field_validator("solution_video_url")
    @classmethod
    def require_youtube_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        normalized = value.strip()
        host = (urlparse(normalized).hostname or "").lower()
        if host not in {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}:
            raise ValueError("solution video must be a YouTube URL")
        return normalized

    @field_validator("solution_image_urls")
    @classmethod
    def require_unique_media_urls(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values if value.strip()]
        if len(normalized) != len(set(normalized)):
            raise ValueError("solution images must be unique")
        return normalized


class CreateQuestionRequest(QuestionVersionInput):
    slug: str = Field(min_length=3, max_length=160, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class CategoryInput(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    slug: str = Field(min_length=2, max_length=120, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: str | None = Field(default=None, max_length=500)

    @field_validator("name", "slug")
    @classmethod
    def require_nonblank_value(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank")
        return normalized


class QuestionMediaUploadRequest(BaseModel):
    image_data_url: str = Field(min_length=32, max_length=7_000_000)


class QuestionMediaUploadResponse(BaseModel):
    image_url: str


class CategoryResponse(CategoryInput):
    id: UUID
    question_count: int = 0


class ScheduleAssignmentRequest(BaseModel):
    assignment_date: date
    level: Level
    question_version_id: UUID


class PublicTestCaseResponse(BaseModel):
    position: int
    input_data: Any
    expected_output: Any
    explanation: str | None


class HintResponse(BaseModel):
    position: int
    content_markdown: str
    xp_penalty: int


class RevealedHintResponse(HintResponse):
    """The hint content is returned only after the server records its reveal."""

    content_markdown: str


class LearnerHintResponse(BaseModel):
    position: int
    xp_penalty: int


class ChallengeResponse(BaseModel):
    assignment_id: UUID
    assignment_date: date
    question_version_id: UUID
    title: str
    statement_markdown: str
    examples: list[ExampleInput]
    constraints_markdown: str | None
    level: Level
    category_id: UUID
    topic: str
    difficulty: int
    starter_code: dict[str, str]
    public_tests: list[PublicTestCaseResponse]
    hints: list[LearnerHintResponse]
    attempt_status: DailyAttemptStatus = DailyAttemptStatus.IN_PROGRESS
    walkthrough_unlocked_at: datetime | None = None


class AdminQuestionResponse(BaseModel):
    question_id: UUID
    question_version_id: UUID
    version_number: int


class QuestionListItemResponse(BaseModel):
    question_id: UUID
    question_version_id: UUID
    slug: str
    title: str
    status: QuestionVersionStatus
    difficulty: int
    category_id: UUID
    topic: str
    level: Level
    version_number: int


class AdminQuestionDetailResponse(QuestionListItemResponse):
    statement_markdown: str
    examples: list[ExampleInput]
    constraints_markdown: str | None
    starter_code: dict[str, str]
    solution_code: dict[str, str]
    explanation_markdown: str | None
    explanation_en: str | None
    explanation_ml: str | None
    solution_trace: list[dict[str, Any]]
    solution_notes_en: list[str]
    solution_notes_ml: list[str]
    solution_video_url: str | None
    solution_image_urls: list[str]
    complexity_notes: str | None
    alternative_approaches: list[AlternativeApproachInput]
    public_tests: list[PublicTestCaseResponse]
    hidden_tests: list[PublicTestCaseResponse]
    hints: list[HintResponse]


class AssignmentResponse(BaseModel):
    id: UUID
    assignment_date: date
    level: Level
    question_version_id: UUID


class DailyAttemptResponse(BaseModel):
    assignment_id: UUID
    status: DailyAttemptStatus
    xp_awarded: int
    streak_counted: bool
    walkthrough_unlocked_at: datetime | None


class SchedulePreviewItemResponse(AssignmentResponse):
    title: str
    topic: str

    model_config = {"from_attributes": True}


class SubmitRequest(BaseModel):
    question_version_id: UUID
    daily_assignment_id: UUID | None = None
    language: ProgrammingLanguage
    source_code: str = Field(min_length=1, max_length=200_000)


class RunSampleRequest(BaseModel):
    """A short-lived, public-test-only execution request."""

    question_version_id: UUID
    language: ProgrammingLanguage
    source_code: str = Field(min_length=1, max_length=200_000)


class SampleTestResult(BaseModel):
    position: int
    passed: bool
    error: str | None = None


class SampleRunResponse(BaseModel):
    passed_test_count: int
    total_test_count: int
    results: list[SampleTestResult]


class SubmissionResponse(BaseModel):
    id: UUID
    question_version_id: UUID
    daily_assignment_id: UUID | None
    language: ProgrammingLanguage
    status: SubmissionStatus
    passed_test_count: int | None
    total_test_count: int | None
    created_at: datetime
    evaluated_at: datetime | None
    test_results: dict[str, Any] | None
    attempt_number: int = 1

    model_config = {"from_attributes": True}


class SubmissionHistoryResponse(SubmissionResponse):
    question_title: str


class SubmissionHistoryPageResponse(BaseModel):
    """A stable, offset-paginated page of a learner's own submissions."""

    items: list[SubmissionHistoryResponse]
    total: int
    page: int
    page_size: int


class SubmissionReviewQuestionResponse(BaseModel):
    """The historical question snapshot that belongs to a learner's submission.

    Deliberately contains public material only. Hidden test cases and reference
    solutions must never be returned from a learner submission review.
    """

    question_version_id: UUID
    title: str
    statement_markdown: str
    examples: list[ExampleInput]
    constraints_markdown: str | None
    level: Level
    category_id: UUID
    topic: str
    difficulty: int
    starter_code: dict[str, str]
    public_tests: list[PublicTestCaseResponse]


class SubmissionReviewResponse(SubmissionResponse):
    """A submission owner's code together with its immutable problem snapshot."""

    question_title: str
    source_code: str
    question: SubmissionReviewQuestionResponse


class PostSolveLearningResponse(BaseModel):
    submission_id: UUID | None = None
    assignment_id: UUID | None = None
    attempt_status: DailyAttemptStatus
    walkthrough_unlocked_at: datetime
    title: str
    topic: str
    explanation_en: str
    explanation_ml: str
    complexity_notes: str
    reference_solution: str | None
    solution_trace: list[dict[str, Any]]
    solution_notes_en: list[str]
    solution_notes_ml: list[str]
    solution_video_url: str | None
    solution_image_urls: list[str]
    alternative_approaches: list[AlternativeApproachInput]
    hints_revealed: int


class TopicMasteryResponse(BaseModel):
    topic: str
    attempts: int
    solved: int
    mastery_score: int


class RecommendationResponse(BaseModel):
    assignment_id: UUID
    assignment_date: date
    question_version_id: UUID
    title: str
    topic: str
    difficulty: int
    reason: str


class RecommendationsResponse(BaseModel):
    weak_topics: list[TopicMasteryResponse]
    topic_mastery: list[TopicMasteryResponse]
    recommendations: list[RecommendationResponse]


class AdminSubmissionResponse(SubmissionResponse):
    """Submission data visible to content administrators, including its author."""

    user_id: UUID
    user_email: str
    user_display_name: str


class ProgressResponse(BaseModel):
    xp: int
    xp_level: int
    xp_level_name: str
    xp_in_level: int
    xp_for_next_level: int
    current_streak: int
    longest_streak: int
    last_solved_date: date | None
    server_timezone: str
    shield_available: int
    shield_cap: int
    topic_progress: list[dict[str, Any]]
    streak_calendar: list[dict[str, Any]]
    badges: list[dict[str, Any]]
