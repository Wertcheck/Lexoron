"""CostControlService – Budget-Verfolgung und Vorab-Prüfung vor jedem
Claude-API-Aufruf (Prompt 33).

Baut auf `ApiCallLog` (Prompt 21) und der Kostenschätzung (siehe
pricing.py) auf. Zwei Aufgaben:

1. **Verfolgung**: `get_current_month_spend_usd` summiert die geschätzten
   Kosten aller `ApiCallLog`-Einträge (nur `result_status="success"` -
   blockierte/fehlgeschlagene Aufrufe verursachten nie tatsächliche
   Kosten) im laufenden Kalendermonat.
2. **Kontrolle**: `check_before_call` wird von `DraftingService`/
   `ReviewEngine` VOR jedem tatsächlichen Claude-Aufruf aufgerufen - wenn
   ein Budget konfiguriert ist (`settings.monthly_budget_usd`) UND
   bereits erreicht/überschritten wurde, wird der Aufruf gar nicht erst
   ausgeführt (spart die Kosten, die ihn erst überschreiten würden).
   Ohne konfiguriertes Budget (`None`, Standardeinstellung) wird NIE
   blockiert - nur verfolgt/angezeigt.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import ApiCallLog


@dataclass(frozen=True)
class BudgetCheckResult:
    allowed: bool
    current_spend_usd: float
    budget_usd: float | None
    is_warning: bool  # True, wenn ueber der Warnschwelle, aber noch nicht blockiert
    reason: str | None = None


class CostControlService:
    def get_current_month_spend_usd(self, db: Session) -> float:
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        total = (
            db.query(func.sum(ApiCallLog.estimated_cost_usd))
            .filter(ApiCallLog.result_status == "success")
            .filter(ApiCallLog.created_at >= month_start)
            .scalar()
        )
        return total or 0.0

    def get_total_spend_usd(self, db: Session) -> float:
        total = (
            db.query(func.sum(ApiCallLog.estimated_cost_usd))
            .filter(ApiCallLog.result_status == "success")
            .scalar()
        )
        return total or 0.0

    def check_before_call(self, db: Session) -> BudgetCheckResult:
        settings = get_settings()
        current_spend = self.get_current_month_spend_usd(db)
        budget = settings.monthly_budget_usd

        if budget is None:
            return BudgetCheckResult(
                allowed=True, current_spend_usd=current_spend, budget_usd=None, is_warning=False
            )

        if current_spend >= budget:
            return BudgetCheckResult(
                allowed=False,
                current_spend_usd=current_spend,
                budget_usd=budget,
                is_warning=True,
                reason=(
                    f"Kostenlimit erreicht: {current_spend:.2f} USD von {budget:.2f} USD "
                    "im laufenden Monat bereits verbraucht."
                ),
            )

        warning_threshold = budget * (settings.budget_warning_threshold_percent / 100)
        is_warning = current_spend >= warning_threshold
        return BudgetCheckResult(
            allowed=True,
            current_spend_usd=current_spend,
            budget_usd=budget,
            is_warning=is_warning,
        )
