"""Benchmark Service orchestrating competitor comparisons, rankings, and scoring (Phase 8)."""

from __future__ import annotations

import uuid
from typing import Any

from app.benchmarking.comparison_builder import ComparisonBuilder
from app.benchmarking.exceptions import (
    BenchmarkEngineError,
    CompanyNotFoundError,
    MissingReportError,
)
from app.benchmarking.ranking_engine import RankingEngine
from app.benchmarking.score_calculator import ScoreCalculator
from app.benchmarking.validators import BenchmarkValidator
from app.core.logging import get_logger
from app.models.benchmark import BenchmarkResult, BenchmarkRun, BenchmarkSummary
from app.models.company import Company
from app.models.enums import BenchmarkDimension, BenchmarkStatus
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

log = get_logger(__name__)

# Direction mapping for metric normalization: True = higher is better, False = lower is better
METRIC_DIRECTIONS = {
    "FINANCIAL": {
        "REVENUE_GROWTH": True,
        "EBITDA_GROWTH": True,
        "NET_INCOME_GROWTH": True,
        "FCF_GROWTH": True,
        "OPERATING_MARGIN": True,
        "NET_MARGIN": True,
        "DEBT_TO_REVENUE": False,
        "CASH_FLOW_MARGIN": True,
    },
    "RISK": {
        "TOTAL_RISKS": False,
        "HIGH_SEVERITY_RISKS": False,
        "CRITICAL_RISKS": False,
        "NEW_RISKS": False,
        "ESCALATED_RISKS": False,
        "RISK_DENSITY": False,
    },
    "TONE": {
        "SENTIMENT_SCORE": True,
        "CONFIDENCE_SCORE": True,
        "HEDGING_SCORE": False,
        "TONE_STABILITY": True,
        "CONFIDENCE_EVOLUTION": True,
    },
    "CAPITAL_ALLOCATION": {
        "CAPEX": True,
        "CAPEX_GROWTH": True,
        "DEBT_REDUCTION": True,
        "CASH_DEPLOYMENT": True,
        "DIVIDEND_METRICS": True,
        "BUYBACK_METRICS": True,
    },
}


class BenchmarkService:
    """Orchestrates loading cohort data, computing scores/ranks, and saving results."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.builder = ComparisonBuilder(db)

    async def _verify_companies_exist(self, company_ids: list[uuid.UUID]) -> dict[uuid.UUID, Company]:
        """Verify all company IDs exist, returning a map of ID -> Company."""
        company_map: dict[uuid.UUID, Company] = {}
        for cid in company_ids:
            stmt = select(Company).where(Company.id == cid)
            res = await self.db.execute(stmt)
            company = res.scalars().first()
            if not company:
                # Unknown company id is a client error (404), not a server fault.
                raise CompanyNotFoundError(f"Company ID {cid} not found in database")
            company_map[cid] = company
        return company_map

    async def run_benchmark(self, run_id: uuid.UUID) -> BenchmarkRun:
        """Execute a benchmark run asynchronously (invoked by Celery task)."""
        # Load run
        stmt = select(BenchmarkRun).where(BenchmarkRun.id == run_id)
        run_res = await self.db.execute(stmt)
        run = run_res.scalars().first()
        if not run:
            raise BenchmarkEngineError(f"Benchmark run {run_id} not found")

        run.status = BenchmarkStatus.PROCESSING
        await self.db.commit()

        try:
            # 1. Validation
            BenchmarkValidator.validate_cohort(run.company_ids)
            weights = BenchmarkValidator.validate_weights(run.configuration.get("weights"))
            year_override = run.configuration.get("year")

            # 2. Verify companies exist
            company_map = await self._verify_companies_exist(run.company_ids)

            # 3. Extract data
            cohort_data: dict[uuid.UUID, dict[str, Any]] = {}
            for cid in run.company_ids:
                data = await self.builder.extract_company_data(cid, year_override)
                if not data:
                    c = company_map[cid]
                    raise MissingReportError(
                        f"Company '{c.name}' ({c.ticker}) is missing reports for the benchmarking period"
                    )
                cohort_data[cid] = data

            # 4. Compute ranks and scores for each metric
            # Shape: company_id -> dimension -> metric_name -> (val, rank, percentile, score)
            computed_metrics: dict[uuid.UUID, dict[str, dict[str, Any]]] = {
                cid: {dim: {} for dim in METRIC_DIRECTIONS} for cid in run.company_ids
            }

            for dim, metrics_dict in METRIC_DIRECTIONS.items():
                for metric_name, direction in metrics_dict.items():
                    # Collect raw values
                    metric_values = []
                    for cid in run.company_ids:
                        val = cohort_data[cid][dim.lower()][metric_name]
                        metric_values.append((cid, val))

                    # Compute ranks/percentiles & scores
                    ranks = RankingEngine.rank_items(metric_values, higher_is_better=direction)
                    scores = ScoreCalculator.normalize_metrics(metric_values, higher_is_better=direction)

                    # Store in map
                    rank_map = {cid: (rank, pct) for cid, rank, pct in ranks}
                    score_map = {cid: score for cid, score in scores}
                    val_map = {cid: val for cid, val in metric_values}

                    for cid in run.company_ids:
                        rank, pct = rank_map[cid]
                        score = score_map[cid]
                        val = val_map[cid]

                        computed_metrics[cid][dim][metric_name] = {
                            "value": val,
                            "rank": rank,
                            "percentile": pct,
                            "score": score,
                        }

            # 5. Compute dimension scores & overall score for each company
            company_summaries: dict[uuid.UUID, dict[str, Any]] = {}
            for cid in run.company_ids:
                dim_scores: dict[str, float | None] = {}
                for dim in METRIC_DIRECTIONS:
                    metric_scores = [computed_metrics[cid][dim][m]["score"] for m in METRIC_DIRECTIONS[dim]]
                    dim_scores[dim] = ScoreCalculator.calculate_dimension_score(metric_scores)

                overall_score = ScoreCalculator.calculate_overall_score(dim_scores, weights)
                company_summaries[cid] = {
                    "scores": dim_scores,
                    "overall_score": overall_score,
                }

            # 6. Rank companies by overall score descending
            overall_scores = [(cid, company_summaries[cid]["overall_score"]) for cid in run.company_ids]
            overall_ranks = RankingEngine.rank_items(overall_scores, higher_is_better=True)
            for cid, rank, _ in overall_ranks:
                company_summaries[cid]["rank"] = rank

            # 7. Persist results
            for cid in run.company_ids:
                # Save granular results
                for dim in METRIC_DIRECTIONS:
                    for mname in METRIC_DIRECTIONS[dim]:
                        m_data = computed_metrics[cid][dim][mname]
                        res_rec = BenchmarkResult(
                            benchmark_run_id=run.id,
                            company_id=cid,
                            benchmark_dimension=BenchmarkDimension[dim],
                            metric_name=mname,
                            metric_value=m_data["value"],
                            rank=m_data["rank"],
                            percentile=m_data["percentile"],
                            score=m_data["score"],
                        )
                        self.db.add(res_rec)

                # Save summary record
                sum_rec = BenchmarkSummary(
                    benchmark_run_id=run.id,
                    company_id=cid,
                    financial_score=company_summaries[cid]["scores"]["FINANCIAL"],
                    risk_score=company_summaries[cid]["scores"]["RISK"],
                    tone_score=company_summaries[cid]["scores"]["TONE"],
                    capital_allocation_score=company_summaries[cid]["scores"]["CAPITAL_ALLOCATION"],
                    overall_score=company_summaries[cid]["overall_score"],
                    rank=company_summaries[cid]["rank"],
                )
                self.db.add(sum_rec)

            run.status = BenchmarkStatus.COMPLETED
            run.error_message = None
            await self.db.commit()

        except Exception as e:
            await self.db.rollback()
            run.status = BenchmarkStatus.FAILED
            run.error_message = str(e)
            await self.db.commit()
            log.error("benchmark_service.execution_failed", run_id=run.id, error=str(e))
            raise

        return run

    async def compare_cohort(self, company_ids: list[uuid.UUID], configuration: dict[str, Any]) -> dict[str, Any]:
        """Compute rankings and scores synchronously in-memory (no database storage)."""
        # 1. Validation
        BenchmarkValidator.validate_cohort(company_ids)
        weights = BenchmarkValidator.validate_weights(configuration.get("weights"))
        year_override = configuration.get("year")

        # 2. Verify companies exist
        company_map = await self._verify_companies_exist(company_ids)

        # 3. Extract data
        cohort_data: dict[uuid.UUID, dict[str, Any]] = {}
        for cid in company_ids:
            data = await self.builder.extract_company_data(cid, year_override)
            if not data:
                c = company_map[cid]
                raise MissingReportError(
                    f"Company '{c.name}' ({c.ticker}) is missing reports for the benchmarking period"
                )
            cohort_data[cid] = data

        # 4. Compute metrics
        computed_metrics: dict[uuid.UUID, dict[str, dict[str, Any]]] = {
            cid: {dim: {} for dim in METRIC_DIRECTIONS} for cid in company_ids
        }

        # List of CohortComparisonPoint shapes
        cohort_results_list: list[dict[str, Any]] = []

        for dim, metrics_dict in METRIC_DIRECTIONS.items():
            for metric_name, direction in metrics_dict.items():
                metric_values = []
                for cid in company_ids:
                    val = cohort_data[cid][dim.lower()][metric_name]
                    metric_values.append((cid, val))

                ranks = RankingEngine.rank_items(metric_values, higher_is_better=direction)
                scores = ScoreCalculator.normalize_metrics(metric_values, higher_is_better=direction)

                rank_map = {cid: (rank, pct) for cid, rank, pct in ranks}
                score_map = {cid: score for cid, score in scores}
                val_map = {cid: val for cid, val in metric_values}

                # Construct comparison point
                results_entry = {
                    "metric_name": metric_name,
                    "dimension": dim,
                    "values": {str(cid): val_map[cid] for cid in company_ids},
                    "ranks": {str(cid): rank_map[cid][0] for cid in company_ids},
                    "percentiles": {str(cid): rank_map[cid][1] for cid in company_ids},
                    "scores": {str(cid): score_map[cid] for cid in company_ids},
                }
                cohort_results_list.append(results_entry)

                for cid in company_ids:
                    computed_metrics[cid][dim][metric_name] = {
                        "score": score_map[cid],
                    }

        # 5. Compute summary scores
        cohort_summaries_list: list[dict[str, Any]] = []
        company_overall_scores = []

        for cid in company_ids:
            dim_scores: dict[str, float | None] = {}
            for dim in METRIC_DIRECTIONS:
                metric_scores = [computed_metrics[cid][dim][m]["score"] for m in METRIC_DIRECTIONS[dim]]
                dim_scores[dim] = ScoreCalculator.calculate_dimension_score(metric_scores)

            overall_score = ScoreCalculator.calculate_overall_score(dim_scores, weights)
            company_overall_scores.append((cid, overall_score))

            c = company_map[cid]
            cohort_summaries_list.append({
                "company_id": cid,
                "company_name": c.name,
                "ticker": c.ticker,
                "scores": dim_scores,
                "rank": None,  # Computed below
            })

        # Rank cohort overall
        overall_ranks = RankingEngine.rank_items(company_overall_scores, higher_is_better=True)
        rank_map = {cid: rank for cid, rank, _ in overall_ranks}

        for summary in cohort_summaries_list:
            cid = summary["company_id"]
            summary["rank"] = rank_map[cid]

        return {
            "cohort_summaries": cohort_summaries_list,
            "cohort_results": cohort_results_list,
            "configuration": configuration,
        }
