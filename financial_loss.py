"""
FINANCIAL LOSS ALGORITHM — the core IP of Debtrix.

Converts raw code metrics (complexity + churn) into money and time,
using assumptions that are explicit and configurable per company
(via FinancialConfig), not hardcoded guesses.

-------------------------------------------------------------------
THE MODEL (documented so it's defensible to an engineering exec):

For each file:
  1. complexity_multiplier = cyclomatic_complexity / BASELINE_COMPLEXITY
     -> how many times "harder than clean code" this file is.
     A file at baseline complexity has multiplier = 1 (no extra tax).

  2. extra_hours_per_touch = BASELINE_HOURS_PER_TOUCH * max(0, complexity_multiplier - 1)
     -> the EXTRA time (beyond a normal safe edit) a developer needs
        because the file is complex. Clean files contribute ~0.

  3. monthly_touches = churn_last_90_days / 3
     -> how often this file gets edited, per month on average.

  4. monthly_hours_wasted_for_file = extra_hours_per_touch * monthly_touches

  5. monthly_loss_for_file = monthly_hours_wasted_for_file
                              * avg_developer_hourly_rate
                              * risk_multiplier

Sum across all files -> total monthly financial loss + total hours wasted.

Health Score (0-100):
  A churn-weighted average complexity multiplier across the repo,
  inverted onto a 0-100 scale. 100 = clean codebase, lower = more debt.

Time-to-Market Delay:
  monthly_hours_wasted / hours_per_working_day
  -> "equivalent full working days per month lost to fighting this
     debt", a proxy non-tech stakeholders can understand.
-------------------------------------------------------------------
"""
from dataclasses import dataclass, field

BASELINE_COMPLEXITY = 5.0       # cyclomatic complexity considered "clean"
BASELINE_HOURS_PER_TOUCH = 0.5  # hours to safely edit a clean file once
HOURS_PER_WORKING_DAY = 8.0


@dataclass
class FileFinancialResult:
    file_path: str
    complexity: float
    churn: int
    complexity_multiplier: float
    monthly_hours_wasted: float
    monthly_loss: float


@dataclass
class FinancialLossReport:
    overall_health_score: float
    monthly_financial_loss: float
    estimated_dev_hours_wasted_monthly: float
    time_to_market_delay_days: float
    per_file_results: list[FileFinancialResult] = field(default_factory=list)
    top_3_priority_fixes: list[dict] = field(default_factory=list)


def calculate_financial_loss(
    merged_metrics: dict[str, dict],
    avg_developer_hourly_rate: float,
    risk_multiplier: float = 1.0,
    working_hours_per_month: float = 160.0,
) -> FinancialLossReport:
    """
    merged_metrics: { file_path: {
        "cyclomatic_complexity": float,
        "churn": int,
        ...
    }}
    """
    per_file_results: list[FileFinancialResult] = []
    total_monthly_hours_wasted = 0.0
    total_monthly_loss = 0.0

    # For health score: churn-weighted average complexity multiplier
    weighted_multiplier_sum = 0.0
    total_churn_weight = 0.0

    for file_path, metrics in merged_metrics.items():
        complexity = metrics.get("cyclomatic_complexity") or BASELINE_COMPLEXITY
        churn = metrics.get("churn", 0)

        complexity_multiplier = complexity / BASELINE_COMPLEXITY
        extra_hours_per_touch = BASELINE_HOURS_PER_TOUCH * max(0.0, complexity_multiplier - 1)
        monthly_touches = churn / 3.0  # 90-day churn -> per-month average
        monthly_hours_wasted = extra_hours_per_touch * monthly_touches
        monthly_loss = monthly_hours_wasted * avg_developer_hourly_rate * risk_multiplier

        per_file_results.append(FileFinancialResult(
            file_path=file_path,
            complexity=complexity,
            churn=churn,
            complexity_multiplier=round(complexity_multiplier, 2),
            monthly_hours_wasted=round(monthly_hours_wasted, 2),
            monthly_loss=round(monthly_loss, 2),
        ))

        total_monthly_hours_wasted += monthly_hours_wasted
        total_monthly_loss += monthly_loss

        # weight by (churn + 1) so untouched files don't distort health score
        weight = churn + 1
        weighted_multiplier_sum += complexity_multiplier * weight
        total_churn_weight += weight

    avg_weighted_multiplier = (
        weighted_multiplier_sum / total_churn_weight if total_churn_weight else 1.0
    )
    # multiplier of 1.0 -> health 100; multiplier of 6.0+ -> health floors at 0
    overall_health_score = max(0.0, min(100.0, 100.0 - (avg_weighted_multiplier - 1.0) * 20.0))

    time_to_market_delay_days = total_monthly_hours_wasted / HOURS_PER_WORKING_DAY

    # Top 3 priority fixes: rank by monthly_loss descending
    top_3 = sorted(per_file_results, key=lambda r: r.monthly_loss, reverse=True)[:3]
    top_3_priority_fixes = [
        {
            "file_path": r.file_path,
            "rank": i + 1,
            "estimated_monthly_loss": r.monthly_loss,
            "reason_summary": (
                f"Complexity is {r.complexity_multiplier}x baseline and was "
                f"modified ~{round(r.churn / 3, 1)} times/month — "
                f"costing an estimated {r.monthly_hours_wasted} dev hours/month."
            ),
        }
        for i, r in enumerate(top_3)
    ]

    return FinancialLossReport(
        overall_health_score=round(overall_health_score, 2),
        monthly_financial_loss=round(total_monthly_loss, 2),
        estimated_dev_hours_wasted_monthly=round(total_monthly_hours_wasted, 2),
        time_to_market_delay_days=round(time_to_market_delay_days, 2),
        per_file_results=per_file_results,
        top_3_priority_fixes=top_3_priority_fixes,
    )
