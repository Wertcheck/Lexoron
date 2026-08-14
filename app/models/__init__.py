"""Datenmodelle (Prompt 04).

Alle Modelle werden hier importiert, damit `Base.metadata` vollstaendig ist
(wichtig fuer Alembics Autogenerate und fuer `Base.metadata.create_all()`
in Tests). Reihenfolge der Importe spielt dank SQLAlchemys
String-Foreign-Key-Aufloesung keine Rolle.
"""

from app.models.audit_event import AuditEvent
from app.models.base import Base
from app.models.client import Client
from app.models.deadline import Deadline
from app.models.document import Document
from app.models.draft import Draft
from app.models.draft_feedback import DraftFeedback
from app.models.embedding import Embedding
from app.models.knowledge_item import KnowledgeItem
from app.models.matter import Matter
from app.models.message import Message
from app.models.party import Party
from app.models.policy import Policy
from app.models.role import Role
from app.models.source import Source
from app.models.task import Task
from app.models.user import User
from app.models.workflow_run import VALID_WORKFLOW_STATUSES, WorkflowRun

__all__ = [
    "Base",
    "Client",
    "Matter",
    "Party",
    "Policy",
    "Message",
    "Document",
    "Task",
    "Deadline",
    "Draft",
    "DraftFeedback",
    "Embedding",
    "Source",
    "KnowledgeItem",
    "WorkflowRun",
    "VALID_WORKFLOW_STATUSES",
    "AuditEvent",
    "User",
    "Role",
]
