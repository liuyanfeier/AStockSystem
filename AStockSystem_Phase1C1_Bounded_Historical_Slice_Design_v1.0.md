# AStockSystem --- Phase 1C.1 Bounded Historical Slice Design v1.0

## Objective

Phase 1C.1 is a production rehearsal, not a full backfill.

It validates:

Raw provider data → immutable storage → identity resolution → curated
data → DQ validation.

No strategy, backtest, broker, or order system.

## Required slices

-   2013-01 baseline
-   2020-08 ChiNext boundary
-   2021-11 BSE opening boundary
-   2025-05 BSE pilot code switch
-   2025-10 BSE full code switch
-   2026-07 field availability validation
-   2026-09 latest sample

Additional cases:

-   BSE old/new identifier transition
-   ST stock
-   suspended stock
-   delisted stock
-   STAR Market stock

## Pipeline

Planner → Request Plan → Executor → Raw Writer → Identity Resolver →
Curated Parquet → DQ Report

## Raw requirements

Each capture must retain:

-   request parameters
-   contract version
-   retrieval time
-   row count
-   schema hash
-   content hash
-   lineage metadata

Raw data is immutable.

## Identity rules

Resolution must use security_identifier_history.

Forbidden:

-   name matching
-   suffix guessing
-   silent manual mapping

Unresolved identifiers go to quarantine.

## Curated outputs

Initial datasets:

-   daily_bar
-   daily_basic_snapshot
-   adjustment_factor_observed
-   suspension_daily
-   risk_warning_daily

## DQ checks

Required:

-   schema validation
-   duplicate detection
-   identity resolution
-   daily vs daily_basic consistency
-   daily vs stk_limit consistency
-   suspension explanation
-   BSE transition continuity
-   causal adjustment validation

## Recovery

Interrupt a run intentionally.

Verify:

-   restart
-   resume
-   no duplicate raw objects

## Rebuild

Delete curated output.

Rebuild from raw.

Logical hash must match.

## Acceptance

Phase 1C.1 passes when:

-   lineage is complete
-   identity is correct
-   quarantine is explained
-   schemas are stable
-   resume works
-   rebuild is deterministic
-   DQ errors are zero
