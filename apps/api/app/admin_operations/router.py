"""Server-enforced operational controls for the Codele admin console."""

import csv
import json
from datetime import UTC, datetime, timedelta
from io import StringIO
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import String, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.admin_operations.schemas import (
    AdminActionResponse,
    AdminAuditLogListResponse,
    AdminAuditLogResponse,
    AdminUserActivity,
    AdminUserListResponse,
    AdminUserSummary,
    AnalyticsDay,
    AnalyticsOverviewResponse,
    CreateModerationReportRequest,
    ModerationReportListResponse,
    ModerationReportResponse,
    RoleChangeRequest,
    UpdateModerationReportRequest,
)
from app.auth.dependencies import (
    get_current_user,
    require_admin,
    require_moderator,
    require_super_admin,
)
from app.db.models import (
    AdminAuditLog,
    ModerationReport,
    NotificationType,
    Streak,
    StreakDay,
    Submission,
    SubmissionStatus,
    User,
    UserBadge,
    UserRole,
    XPTransaction,
)
from app.db.session import get_db
from app.notifications.service import create_notification

router = APIRouter(prefix="/admin", tags=["admin operations"])
public_router = APIRouter(tags=["moderation"])

ROLE_RANK = {
    UserRole.USER: 1,
    UserRole.MODERATOR: 2,
    UserRole.ADMIN: 3,
    UserRole.SUPER_ADMIN: 4,
}
TERMINAL_SUBMISSION_STATUSES = (
    SubmissionStatus.PASSED,
    SubmissionStatus.FAILED,
    SubmissionStatus.ERROR,
)


def record_audit(
    db: Session,
    *,
    actor: User,
    action: str,
    target_type: str,
    target_id: UUID | str,
    before: dict | None = None,
    after: dict | None = None,
) -> None:
    """Append a transaction-bound audit fact without storing credentials or source code."""
    db.add(
        AdminAuditLog(
            actor_user_id=actor.id,
            action=action,
            target_type=target_type,
            target_id=str(target_id),
            metadata_json={"before": before or {}, "after": after or {}},
        )
    )


def activity_totals(db: Session, user_id: UUID) -> tuple[int, int, int, int]:
    submission_count = db.scalar(
        select(func.count(Submission.id)).where(Submission.user_id == user_id)
    ) or 0
    xp_total = db.scalar(
        select(func.coalesce(func.sum(XPTransaction.amount), 0)).where(
            XPTransaction.user_id == user_id
        )
    ) or 0
    current_streak = db.scalar(select(Streak.current_streak).where(Streak.user_id == user_id)) or 0
    badge_count = db.scalar(
        select(func.count(UserBadge.id)).where(UserBadge.user_id == user_id)
    ) or 0
    return int(submission_count), int(xp_total), int(current_streak), int(badge_count)


def user_summary(db: Session, user: User) -> AdminUserSummary:
    submission_count, xp_total, current_streak, badge_count = activity_totals(db, user.id)
    return AdminUserSummary(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        level=user.level,
        is_active=user.is_active,
        created_at=user.created_at,
        session_version=user.session_version,
        submission_count=submission_count,
        xp_total=xp_total,
        current_streak=current_streak,
        badge_count=badge_count,
    )


def get_user_or_404(db: Session, user_id: UUID) -> User:
    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def assert_manageable(actor: User, target: User) -> None:
    if actor.id == target.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="You cannot perform this account action on yourself",
        )
    if actor.role != UserRole.SUPER_ADMIN and ROLE_RANK[target.role] >= ROLE_RANK[actor.role]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot manage an account with an equal or higher role",
        )
    if target.role == UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin accounts cannot be changed through routine account controls",
        )


def audit_response(log: AdminAuditLog) -> AdminAuditLogResponse:
    return AdminAuditLogResponse(
        id=log.id,
        action=log.action,
        target_type=log.target_type,
        target_id=log.target_id,
        metadata_json=log.metadata_json,
        created_at=log.created_at,
        actor_user_id=log.actor_user_id,
        actor_display_name=log.actor.display_name,
        actor_email=log.actor.email,
    )


def report_response(report: ModerationReport) -> ModerationReportResponse:
    return ModerationReportResponse(
        id=report.id,
        status=report.status,
        reason=report.reason,
        details=report.details,
        resolution_note=report.resolution_note,
        created_at=report.created_at,
        handled_at=report.handled_at,
        reporter_id=report.reporter_id,
        reporter_display_name=report.reporter.display_name,
        target_user_id=report.target_user_id,
        target_display_name=report.target_user.display_name,
        handled_by_id=report.handled_by_id,
        handled_by_display_name=(report.handled_by.display_name if report.handled_by else None),
    )


@public_router.post(
    "/moderation-reports",
    response_model=ModerationReportResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_moderation_report(
    payload: CreateModerationReportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ModerationReportResponse:
    if current_user.id == payload.target_user_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="You cannot report your own account",
        )
    target = get_user_or_404(db, payload.target_user_id)
    report = ModerationReport(
        reporter_id=current_user.id,
        target_user_id=target.id,
        reason=payload.reason.strip(),
        details=payload.details.strip() if payload.details else None,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    report = db.scalar(
        select(ModerationReport)
        .where(ModerationReport.id == report.id)
        .options(
            joinedload(ModerationReport.reporter),
            joinedload(ModerationReport.target_user),
            joinedload(ModerationReport.handled_by),
        )
    )
    assert report is not None
    return report_response(report)


@router.get("/operations/users", response_model=AdminUserListResponse)
def list_operational_users(
    q: str | None = Query(default=None, max_length=160),
    role: UserRole | None = None,
    is_active: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminUserListResponse:
    statement = select(User)
    if q and q.strip():
        needle = f"%{q.strip()}%"
        statement = statement.where(
            or_(
                User.email.ilike(needle),
                User.display_name.ilike(needle),
                User.id.cast(String).ilike(needle),
            )
        )
    if role is not None:
        statement = statement.where(User.role == role)
    if is_active is not None:
        statement = statement.where(User.is_active == is_active)
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    users = list(
        db.scalars(
            statement.order_by(User.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return AdminUserListResponse(
        items=[user_summary(db, user) for user in users],
        page=page,
        page_size=page_size,
        total=int(total),
    )


@router.get("/operations/users/{user_id}/activity", response_model=AdminUserActivity)
def get_operational_user_activity(
    user_id: UUID,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminUserActivity:
    user = get_user_or_404(db, user_id)
    submissions = list(
        db.scalars(
            select(Submission)
            .where(Submission.user_id == user.id)
            .order_by(Submission.created_at.desc())
            .limit(20)
        )
    )
    transactions = list(
        db.scalars(
            select(XPTransaction)
            .where(XPTransaction.user_id == user.id)
            .order_by(XPTransaction.created_at.desc())
            .limit(20)
        )
    )
    streak_days = list(
        db.scalars(
            select(StreakDay)
            .where(StreakDay.user_id == user.id)
            .order_by(StreakDay.solved_date.desc())
            .limit(90)
        )
    )
    awards = list(
        db.scalars(
            select(UserBadge)
            .where(UserBadge.user_id == user.id)
            .options(joinedload(UserBadge.badge))
            .order_by(UserBadge.awarded_at.desc())
        )
    )
    return AdminUserActivity(
        user=user_summary(db, user),
        recent_submissions=[
            {
                "id": str(item.id),
                "status": item.status.value,
                "language": item.language.value,
                "attempt_number": item.attempt_number,
                "passed_test_count": item.passed_test_count,
                "total_test_count": item.total_test_count,
                "created_at": item.created_at.isoformat(),
            }
            for item in submissions
        ],
        recent_xp_transactions=[
            {
                "id": str(item.id),
                "amount": item.amount,
                "reason": item.reason.value,
                "created_at": item.created_at.isoformat(),
            }
            for item in transactions
        ],
        streak_calendar=[
            {
                "date": item.solved_date.isoformat(),
                "shielded": item.is_shielded,
                "submission_id": str(item.submission_id) if item.submission_id else None,
            }
            for item in streak_days
        ],
        badges=[
            {
                "code": item.badge.code,
                "name": item.badge.name,
                "icon": item.badge.icon,
                "awarded_at": item.awarded_at.isoformat(),
            }
            for item in awards
        ],
    )


@router.post("/operations/users/{user_id}/suspend", response_model=AdminActionResponse)
def suspend_user(
    user_id: UUID,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminActionResponse:
    target = get_user_or_404(db, user_id)
    assert_manageable(actor, target)
    before = {"is_active": target.is_active, "session_version": target.session_version}
    target.is_active = False
    target.session_version += 1
    record_audit(
        db,
        actor=actor,
        action="user.suspended",
        target_type="user",
        target_id=target.id,
        before=before,
        after={"is_active": target.is_active, "session_version": target.session_version},
    )
    notification_id = create_notification(
        db,
        user_id=target.id,
        notification_type=NotificationType.ACCOUNT,
        title="Your account was suspended",
        body="An administrator suspended your account and revoked active sessions.",
        link="/login",
        event_key=f"account-suspended:{target.id}:{target.session_version}",
    )
    db.commit()
    if notification_id is not None:
        from app.notifications.tasks import deliver_notification

        deliver_notification.delay(str(notification_id))
    return AdminActionResponse(
        id=target.id,
        is_active=target.is_active,
        role=target.role,
        session_version=target.session_version,
        message="Account suspended and active sessions revoked.",
    )


@router.post("/operations/users/{user_id}/restore", response_model=AdminActionResponse)
def restore_user(
    user_id: UUID,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminActionResponse:
    target = get_user_or_404(db, user_id)
    assert_manageable(actor, target)
    before = {"is_active": target.is_active, "session_version": target.session_version}
    target.is_active = True
    target.session_version += 1
    record_audit(
        db,
        actor=actor,
        action="user.restored",
        target_type="user",
        target_id=target.id,
        before=before,
        after={"is_active": target.is_active, "session_version": target.session_version},
    )
    notification_id = create_notification(
        db,
        user_id=target.id,
        notification_type=NotificationType.ACCOUNT,
        title="Your account was restored",
        body="An administrator restored your account. Please sign in again to continue.",
        link="/login",
        event_key=f"account-restored:{target.id}:{target.session_version}",
    )
    db.commit()
    if notification_id is not None:
        from app.notifications.tasks import deliver_notification

        deliver_notification.delay(str(notification_id))
    return AdminActionResponse(
        id=target.id,
        is_active=target.is_active,
        role=target.role,
        session_version=target.session_version,
        message="Account restored. The user must sign in again.",
    )


@router.post("/operations/users/{user_id}/revoke-sessions", response_model=AdminActionResponse)
def revoke_user_sessions(
    user_id: UUID,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminActionResponse:
    target = get_user_or_404(db, user_id)
    assert_manageable(actor, target)
    before = {"session_version": target.session_version}
    target.session_version += 1
    record_audit(
        db,
        actor=actor,
        action="user.sessions_revoked",
        target_type="user",
        target_id=target.id,
        before=before,
        after={"session_version": target.session_version},
    )
    notification_id = create_notification(
        db,
        user_id=target.id,
        notification_type=NotificationType.ACCOUNT,
        title="Your sessions were revoked",
        body="An administrator signed you out of active sessions. Please sign in again.",
        link="/login",
        event_key=f"account-sessions-revoked:{target.id}:{target.session_version}",
    )
    db.commit()
    if notification_id is not None:
        from app.notifications.tasks import deliver_notification

        deliver_notification.delay(str(notification_id))
    return AdminActionResponse(
        id=target.id,
        is_active=target.is_active,
        role=target.role,
        session_version=target.session_version,
        message="All active sessions were revoked.",
    )


@router.patch("/operations/users/{user_id}/role", response_model=AdminActionResponse)
def change_user_role(
    user_id: UUID,
    payload: RoleChangeRequest,
    actor: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> AdminActionResponse:
    target = get_user_or_404(db, user_id)
    assert_manageable(actor, target)
    before = {"role": target.role.value, "session_version": target.session_version}
    target.role = payload.role
    target.session_version += 1
    record_audit(
        db,
        actor=actor,
        action="user.role_changed",
        target_type="user",
        target_id=target.id,
        before=before,
        after={"role": target.role.value, "session_version": target.session_version},
    )
    notification_id = create_notification(
        db,
        user_id=target.id,
        notification_type=NotificationType.ACCOUNT,
        title="Your Codele role changed",
        body="An administrator changed your account role. Please sign in again to refresh access.",
        link="/login",
        event_key=f"account-role-changed:{target.id}:{target.session_version}",
    )
    db.commit()
    if notification_id is not None:
        from app.notifications.tasks import deliver_notification

        deliver_notification.delay(str(notification_id))
    return AdminActionResponse(
        id=target.id,
        is_active=target.is_active,
        role=target.role,
        session_version=target.session_version,
        message="Role updated. The user must sign in again.",
    )


@router.get("/moderation-reports", response_model=ModerationReportListResponse)
def list_moderation_reports(
    report_status: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    _: User = Depends(require_moderator),
    db: Session = Depends(get_db),
) -> ModerationReportListResponse:
    statement = select(ModerationReport)
    if report_status is not None:
        if report_status not in {"open", "reviewing", "resolved", "dismissed"}:
            raise HTTPException(status_code=422, detail="Unknown moderation report status")
        statement = statement.where(ModerationReport.status == report_status)
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    reports = list(
        db.scalars(
            statement.options(
                joinedload(ModerationReport.reporter),
                joinedload(ModerationReport.target_user),
                joinedload(ModerationReport.handled_by),
            )
            .order_by(ModerationReport.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return ModerationReportListResponse(
        items=[report_response(item) for item in reports],
        page=page,
        page_size=page_size,
        total=int(total),
    )


@router.patch("/moderation-reports/{report_id}", response_model=ModerationReportResponse)
def update_moderation_report(
    report_id: UUID,
    payload: UpdateModerationReportRequest,
    actor: User = Depends(require_moderator),
    db: Session = Depends(get_db),
) -> ModerationReportResponse:
    report = db.scalar(
        select(ModerationReport)
        .where(ModerationReport.id == report_id)
        .options(
            joinedload(ModerationReport.reporter),
            joinedload(ModerationReport.target_user),
            joinedload(ModerationReport.handled_by),
        )
    )
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    before = {"status": report.status, "resolution_note": report.resolution_note}
    report.status = payload.status
    report.resolution_note = payload.resolution_note.strip() if payload.resolution_note else None
    report.handled_by_id = actor.id
    report.handled_at = datetime.now(UTC)
    record_audit(
        db,
        actor=actor,
        action="moderation_report.updated",
        target_type="moderation_report",
        target_id=report.id,
        before=before,
        after={"status": report.status, "resolution_note": report.resolution_note},
    )
    db.commit()
    db.refresh(report)
    return report_response(report)


@router.get("/analytics/overview", response_model=AnalyticsOverviewResponse)
def analytics_overview(
    days: int = Query(default=30, ge=7, le=90),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AnalyticsOverviewResponse:
    now = datetime.now(UTC)

    def active_users_since(delta: timedelta) -> int:
        return int(
            db.scalar(
                select(func.count(func.distinct(Submission.user_id))).where(
                    Submission.created_at >= now - delta
                )
            )
            or 0
        )

    start = now - timedelta(days=days - 1)
    rows = list(
        db.execute(
            select(
                Submission.user_id,
                Submission.created_at,
                Submission.status,
                Submission.attempt_number,
            ).where(Submission.created_at >= start)
        )
    )
    terminal_rows = [row for row in rows if row.status in TERMINAL_SUBMISSION_STATUSES]
    passed_count = sum(row.status == SubmissionStatus.PASSED for row in terminal_rows)
    error_count = sum(row.status == SubmissionStatus.ERROR for row in terminal_rows)
    daily_values: dict[str, dict[str, object]] = {}
    for offset in range(days):
        key = (start.date() + timedelta(days=offset)).isoformat()
        daily_values[key] = {
            "active_users": set(),
            "submissions": 0,
            "passed_submissions": 0,
            "execution_failures": 0,
        }
    for row in rows:
        key = row.created_at.date().isoformat()
        if key not in daily_values:
            continue
        values = daily_values[key]
        values["active_users"].add(row.user_id)  # type: ignore[union-attr]
        values["submissions"] += 1  # type: ignore[operator]
        if row.status == SubmissionStatus.PASSED:
            values["passed_submissions"] += 1  # type: ignore[operator]
        if row.status == SubmissionStatus.ERROR:
            values["execution_failures"] += 1  # type: ignore[operator]
    queue_depth = int(
        db.scalar(
            select(func.count(Submission.id)).where(
                Submission.status.in_((SubmissionStatus.QUEUED, SubmissionStatus.RUNNING))
            )
        )
        or 0
    )
    return AnalyticsOverviewResponse(
        dau=active_users_since(timedelta(days=1)),
        wau=active_users_since(timedelta(days=7)),
        mau=active_users_since(timedelta(days=30)),
        completion_rate=round(passed_count / len(terminal_rows) * 100, 2) if terminal_rows else 0,
        execution_failure_rate=(
            round(error_count / len(terminal_rows) * 100, 2) if terminal_rows else 0
        ),
        evaluated_submissions=len(terminal_rows),
        average_attempt_number=(
            round(sum(row.attempt_number for row in rows) / len(rows), 2) if rows else 0
        ),
        queue_depth=queue_depth,
        daily=[
            AnalyticsDay(
                date=key,
                active_users=len(values["active_users"]),  # type: ignore[arg-type]
                submissions=int(values["submissions"]),
                passed_submissions=int(values["passed_submissions"]),
                execution_failures=int(values["execution_failures"]),
            )
            for key, values in daily_values.items()
        ],
    )


def filtered_audit_statement(
    *,
    action: str | None,
    q: str | None,
    from_at: datetime | None,
    to_at: datetime | None,
) -> object:
    statement = select(AdminAuditLog).options(joinedload(AdminAuditLog.actor))
    if action:
        statement = statement.where(AdminAuditLog.action == action)
    if q and q.strip():
        needle = f"%{q.strip()}%"
        statement = statement.join(AdminAuditLog.actor).where(
            or_(
                User.email.ilike(needle),
                User.display_name.ilike(needle),
                AdminAuditLog.target_id.ilike(needle),
                AdminAuditLog.target_type.ilike(needle),
            )
        )
    if from_at:
        statement = statement.where(AdminAuditLog.created_at >= from_at)
    if to_at:
        statement = statement.where(AdminAuditLog.created_at <= to_at)
    return statement.order_by(AdminAuditLog.created_at.desc())


@router.get("/audit-logs", response_model=AdminAuditLogListResponse)
def list_audit_logs(
    action: str | None = Query(default=None, max_length=100),
    q: str | None = Query(default=None, max_length=160),
    from_at: datetime | None = Query(default=None, alias="from"),
    to_at: datetime | None = Query(default=None, alias="to"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminAuditLogListResponse:
    statement = filtered_audit_statement(action=action, q=q, from_at=from_at, to_at=to_at)
    total = db.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0
    logs = list(db.scalars(statement.offset((page - 1) * page_size).limit(page_size)))
    return AdminAuditLogListResponse(
        items=[audit_response(log) for log in logs],
        page=page,
        page_size=page_size,
        total=int(total),
    )


@router.get("/audit-logs/export")
def export_audit_logs(
    action: str | None = Query(default=None, max_length=100),
    q: str | None = Query(default=None, max_length=160),
    from_at: datetime | None = Query(default=None, alias="from"),
    to_at: datetime | None = Query(default=None, alias="to"),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    logs = list(
        db.scalars(filtered_audit_statement(action=action, q=q, from_at=from_at, to_at=to_at))
    )
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        ["created_at", "actor", "actor_email", "action", "target_type", "target_id", "metadata"]
    )
    for log in logs:
        writer.writerow(
            [
                log.created_at.isoformat(),
                log.actor.display_name,
                log.actor.email,
                log.action,
                log.target_type,
                log.target_id,
                json.dumps(log.metadata_json, sort_keys=True),
            ]
        )
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=codele-admin-audit-logs.csv"},
    )
