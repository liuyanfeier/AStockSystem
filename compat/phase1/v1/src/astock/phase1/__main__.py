"""Public, import-safe integrated Phase1 entry; live always requires exact licenses."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from pydantic import SecretStr

from astock.phase1 import acquisition, application, contracts, domains, evidence, fixtures, legacy, pipeline
from astock.phase1.core import PRODUCTION, category, encoded, publish, strict_json


def load(path):
    return strict_json(Path(path).read_bytes())


def main(argv=None):
    p = argparse.ArgumentParser(prog='python -m astock.phase1')
    p.add_argument('--root', type=Path, default=Path.cwd())
    p.add_argument('--output', type=Path)
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('specs')
    sub.add_parser('legacy')
    sub.add_parser('identity-compatibility')
    s = sub.add_parser('legacy-resolve')
    s.add_argument('--dataset', required=True)
    s.add_argument('--native', required=True)
    s.add_argument('--event-date', required=True)
    s.add_argument('--as-of', required=True)
    s.add_argument('--source-object', required=True)
    s.add_argument('--source-row', type=int, required=True)
    s.add_argument('--exchange')
    s.add_argument('--asset-type')
    for command in ('demo', 'audit', 'coverage', 'build', 'increment'):
        s = sub.add_parser(command)
        s.add_argument('--destination', type=Path, required=True)
    s = sub.add_parser('import-evidence')
    s.add_argument('--destination', type=Path, required=True)
    s.add_argument('--packages', required=True)
    s.add_argument('--live', action='store_true', help='Explicit approved production fact adoption; sends no API')
    s.add_argument('--approval')
    s.add_argument('--human')
    s = sub.add_parser('rebuild')
    s.add_argument('--source', type=Path, required=True)
    s.add_argument('--destination', type=Path, required=True)
    s = sub.add_parser('as-of')
    s.add_argument('--destination', type=Path, required=True)
    s.add_argument('--security', required=True)
    s.add_argument('--event-date', required=True)
    s.add_argument('--as-of', required=True)
    s.add_argument('--taxonomy')
    for command in ('adjust', 'rule', 'reference'):
        s = sub.add_parser(command)
        s.add_argument('--destination', type=Path, required=True)
        s.add_argument('--as-of', required=True)
        s.add_argument('--event-date', required=True)
        if command == 'adjust':
            s.add_argument('--native', required=True)
            s.add_argument('--anchor', required=True)
        elif command == 'rule':
            s.add_argument('--exchange', required=True)
            s.add_argument('--board', required=True)
            s.add_argument('--state', required=True)
        else:
            s.add_argument('--native', required=True)
    s = sub.add_parser('plan')
    s.add_argument('--destination', type=Path, required=True)
    s.add_argument('--members', required=True)
    s.add_argument('--baseline', required=True)
    s.add_argument('--fixture', action='store_true')
    s.add_argument('--protected-history')
    s.add_argument('--resume-from')
    for command in ('execute',):
        s = sub.add_parser(command)
        s.add_argument('--destination', type=Path, required=True)
        s.add_argument('--plan', required=True)
        s.add_argument('--baseline', required=True)
        s.add_argument('--approval', required=True)
        s.add_argument('--human', required=True)
        s.add_argument('--live', action='store_true')
    s = sub.add_parser('failed-body-candidate')
    s.add_argument('--destination', type=Path, required=True)
    s.add_argument('--directory', type=Path, required=True)
    s.add_argument('--baseline', required=True)
    s = sub.add_parser('stopped27')
    s.add_argument('--destination', type=Path, required=True)
    s.add_argument('--selection', type=Path, required=True)
    s.add_argument('--baseline', required=True)
    s = sub.add_parser('protection-benchmark')
    s.add_argument('--destination', type=Path, required=True)
    s = sub.add_parser('application')
    s.add_argument('--selection', type=Path, required=True)
    s.add_argument('--market6', type=Path, required=True)
    s.add_argument('--baseline', required=True)
    s.add_argument('--protected-history', required=True)
    s = sub.add_parser('expand-market')
    s.add_argument('--destination', type=Path, required=True)
    s.add_argument('--baseline', required=True)
    s.add_argument('--start', required=True)
    s.add_argument('--end', required=True)
    s.add_argument('--budget', type=int, required=True)
    args = p.parse_args(argv)
    root = args.root.resolve()
    try:
        if args.command == 'specs':
            cs = contracts.catalog(root)
            result = dict(protocol='PHASE1_INTEGRATED_V1', datasets={k: dict(domain=v['domain'], fields=list(v['fields']), cap=v['cap'], date_axis=v['date_axis']) for k, v in cs.items()}, live_default=False)
        elif args.command == 'legacy': result = legacy.snapshot(root)
        elif args.command == 'identity-compatibility': result = evidence.compatible_identity(root)[1]
        elif args.command == 'legacy-resolve':
            from uuid import UUID
            from astock.phase1.core import day, instant
            resolver, _ = evidence.compatible_identity(root)
            result = resolver.resolve(provider='tushare', dataset=args.dataset, native_identifier=args.native,
                event_date=day(args.event_date), raw_object_id=UUID(args.source_object), raw_row_number=args.source_row,
                knowledge_as_of=instant(args.as_of), provider_exchange=args.exchange, provider_asset_type=args.asset_type).model_dump(mode='json')
        elif args.command == 'demo': result = fixtures.demo(root, args.destination)
        elif args.command == 'import-evidence': result = pipeline.import_evidence(root, args.destination, load(args.packages),
                     fixture=not args.live, approval=load(args.approval) if args.approval else None,
                     human=load(args.human) if args.human else None)
        elif args.command in ('build', 'increment', 'rebuild'):
            result = pipeline.build(root, args.destination, source_destination=args.source if args.command == 'rebuild' else None)
        elif args.command == 'audit':
            with acquisition.store(root, args.destination, fixture=args.destination.resolve() != (root / PRODUCTION).resolve(), read_only=True) as db:
                pipeline.verify_generation_inputs(root, args.destination, db)
                result = dict(capture=acquisition.audit(root, args.destination, db), lineage=pipeline.validate_lineage(db))
        elif args.command == 'coverage': result = pipeline.coverage(root, args.destination)
        elif args.command == 'as-of': result = pipeline.query(root, args.destination, args.security, args.event_date, args.as_of, taxonomy=args.taxonomy)
        elif args.command in ('adjust', 'rule', 'reference'):
            with acquisition.store(root, args.destination, fixture=args.destination.resolve() != (root / PRODUCTION).resolve(), read_only=True) as db:
                pipeline.inputs(root, args.destination, db)
                pipeline.verify_generation_inputs(root, args.destination, db)
                pipeline.validate_lineage(db)
                rows = pipeline.fact_rows(db)
            if args.command == 'adjust': result = domains.adjusted_price(rows, args.native, args.event_date, args.anchor, args.as_of)
            elif args.command == 'rule': result = domains.rule_at(rows, args.exchange, args.board, args.state, args.event_date, args.as_of)
            else:
                known, conflicts = domains.known_versions([r for r in rows if r['domain'] == 'index' and r['entity'] == args.native], args.as_of)
                result = dict(rows=[r for r in known if r['event_date'] in (None, args.event_date)], conflicts=conflicts, research_admitted=False)
        elif args.command == 'plan':
            prior = []
            if (args.destination / 'catalog.duckdb').exists():
                with acquisition.store(root, args.destination, fixture=args.fixture, read_only=True) as db:
                    acquisition.audit(root, args.destination, db)
                    prior = acquisition.local_consumption(db)
            result = acquisition.make_plan(root, args.destination, load(args.members), load(args.baseline), fixture=args.fixture,
                       prior_consumption=prior, resume_from=args.resume_from, protected_history=load(args.protected_history) if args.protected_history else None)
        elif args.command == 'execute':
            result = acquisition.run_batch(root, args.destination, load(args.plan), load(args.baseline),
                     approval=load(args.approval), human=load(args.human), live=args.live,
                     token=SecretStr(os.environ.get('TUSHARE_TOKEN', '')))
        elif args.command == 'failed-body-candidate': result = evidence.failed_calendar_candidate(root, args.destination, args.directory, load(args.baseline))
        elif args.command == 'stopped27': result = evidence.stopped27(root, args.destination, args.selection, load(args.baseline))
        elif args.command == 'application': result = application.propose(root, args.selection, args.market6, load(args.baseline), load(args.protected_history))
        elif args.command == 'expand-market': result = application.expand_market(root, args.destination, load(args.baseline), start=args.start, end=args.end, budget=args.budget)
        else: result = evidence.protection_benchmark(args.destination)
        body = encoded(result)
        if args.output: publish(args.output, body)
        else: print(body.decode())
        return 1 if result.get('primary_error') or result.get('secondary_errors') or result.get('status') == 'STOPPED' else 0
    except Exception as error:
        print(encoded(dict(status='STOPPED', reason=category(error), real_market_API_not_assumed_zero=True)).decode())
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
