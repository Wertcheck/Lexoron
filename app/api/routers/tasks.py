"""Aufgaben-Endpunkte (Prompt 21).

Umfasst sowohl `Task` (manuelle/generierte Aufgaben) als auch `Deadline`
(erkannte Fristen, Prompt 10) - beide bilden fachlich denselben
Dashboard-Bereich "Aufgaben/Fristen" (Konzept §3).

WICHTIG: `Deadline.review_status` wird unveraendert durchgereicht - nie
implizit als "confirmed" dargestellt. Siehe Grundregel in
app/models/deadline.py.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import LimitParam, OffsetParam, get_or_404
from app.api.schemas import DeadlineOut, TaskOut
from app.db.session import get_db
from app.models import Deadline, Task

router = APIRouter(prefix="/api", tags=["tasks"])


@router.get("/tasks", response_model=list[TaskOut])
def list_tasks(
    db: Session = Depends(get_db),
    matter_id: str | None = Query(default=None),
    status: str | None = Query(default=None, description="'open' oder 'done'."),
    limit: LimitParam = 50,
    offset: OffsetParam = 0,
) -> list[Task]:
    query = db.query(Task)
    if matter_id is not None:
        query = query.filter(Task.matter_id == matter_id)
    if status is not None:
        query = query.filter(Task.status == status)
    return (
        query.order_by(Task.due_date.asc().nulls_last())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: str, db: Session = Depends(get_db)) -> Task:
    return get_or_404(db, Task, task_id, "Aufgabe")


@router.get("/deadlines", response_model=list[DeadlineOut])
def list_deadlines(
    db: Session = Depends(get_db),
    matter_id: str | None = Query(default=None),
    review_status: str | None = Query(
        default=None, description="'unreviewed', 'confirmed' oder 'rejected'."
    ),
    limit: LimitParam = 50,
    offset: OffsetParam = 0,
) -> list[Deadline]:
    query = db.query(Deadline)
    if matter_id is not None:
        query = query.filter(Deadline.matter_id == matter_id)
    if review_status is not None:
        query = query.filter(Deadline.review_status == review_status)
    return (
        query.order_by(Deadline.due_date.asc().nulls_last())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/deadlines/{deadline_id}", response_model=DeadlineOut)
def get_deadline(deadline_id: str, db: Session = Depends(get_db)) -> Deadline:
    return get_or_404(db, Deadline, deadline_id, "Frist")
