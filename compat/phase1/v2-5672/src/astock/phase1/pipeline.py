"""Immutable evidenced facts, atomic generations, rebuild, coverage and queries."""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from astock.phase1 import PROTOCOL, acquisition, contracts, domains, interpretation
from astock.phase1.core import (PRODUCTION, day, digest, encoded, file_hash, instant, publish,
                               require, safe_path, stamp, strict_json)


def import_evidence(root: Path, destination: Path, packages: list[dict], *, fixture=True, approval=None, human=None) -> dict:
    """Offline fixture fact batches use the real contract path, never SQL injection.

    Production needs matched independent fact policy and actual human license.
    """
    imported = []
    policy = {}
    if not fixture:
        from astock.phase1.fact_admission import authorize
        policy = authorize(root, destination, packages, approval, human)
    require(bool(packages) and len({digest(p) for p in packages}) == len(packages), 'NONEMPTY_DISTINCT_FACT_BATCH_REQUIRED')
    for package in packages:
        if contracts.catalog(root)[package['request']['dataset']]['source'] == 'TUSHARE':
            interpretation.validate(root, package)
        decoded = contracts.decode(root, package['request'], encoded(package['response']))
        source = dict(object_id=digest(package), retrieved_at=package['retrieved_at'], fixture_only=fixture, **policy)
        domains.facts(root, package['request'], decoded['rows'], source)
    with acquisition.store(root, destination, fixture=fixture) as db:
        for package in packages:
            member, body, observed = package['request'], encoded(package['response']), package['retrieved_at']
            require(not fixture or package['namespace'] == 'FIXTURE' and package.get('evidence') == 'SYNTHETIC_NOT_LEGAL_EVIDENCE', 'FIXTURE_EVIDENCE_ONLY')
            contracts.decode(root, member, body)
            oid = digest(package)
            source = dict(protocol=PROTOCOL, object_id=oid, request=member, retrieved_at=stamp(instant(observed)),
                          body_hash=digest(package['response']), fixture_only=fixture, transform_pins=acquisition.pins(root),
                          evidence=package['evidence'], evidence_hash=digest(package), **policy)
            if package.get('raw_reference'):
                source.update(interpretation.validate(root, package, destination=destination, db=db))
            directory = safe_path(destination, destination / 'evidence' / oid)
            directory.mkdir(parents=True, exist_ok=True)
            publish(directory / 'response.body', body)
            publish(directory / 'source.json', encoded(source))
            publish(directory / 'package.json', encoded(package))
            imported.append(oid)
        # Registration commits only after all packages decode; partial files
        # are not admitted and are caught as unregistered evidence by audit.
        def register():
            prior = db.execute("SELECT payload FROM p1_meta WHERE key='evidence'").fetchone()
            ids = strict_json(prior[0].encode()) if prior else []
            next_ids = sorted(set(ids + imported))
            if prior is None or ids != next_ids:
                db.execute("INSERT OR REPLACE INTO p1_meta VALUES ('evidence',?)", [encoded(next_ids).decode()])
        acquisition.transaction(db, register)
    return dict(status='FIXTURE_EVIDENCE_REGISTERED' if fixture else 'REVIEWED_EVIDENCE_REGISTERED', objects=len(imported), production_adopted=not fixture)


def inputs(root: Path, destination: Path, db) -> list[dict]:
    acquisition.audit(root, destination, db)
    result = []
    for mid, oid in db.execute('SELECT logical_id,object_id FROM p1_receipt ORDER BY logical_id').fetchall():
        directory = destination / 'objects' / oid
        source = strict_json(safe_path(destination, directory / 'http-source.json', exists=True).read_bytes())
        result.append(dict(object_id=oid, kind='CAPTURE', request=source['request'], source=source,
                           body_path=str(directory / 'response.body'), source_path=str(directory / 'http-source.json'),
                           body_hash=file_hash(directory / 'response.body'), source_hash=digest(source),
                           transform_pins=strict_json(db.execute('SELECT payload FROM p1_plan WHERE plan_hash=?',[source['batch_hash']]).fetchone()[0].encode())['pins']))
    owner=strict_json(db.execute("SELECT payload FROM p1_meta WHERE key='owner'").fetchone()[0].encode())
    from astock.phase1 import versions
    default_pins=versions.v1_registry(root)['pins'] if owner['protocol']=='PHASE1_INTEGRATED_V1' else acquisition.pins(root)
    prior = db.execute("SELECT payload FROM p1_meta WHERE key='evidence'").fetchone()
    registered = strict_json(prior[0].encode()) if prior else []
    directory = destination / 'evidence'
    require(not directory.exists() or {p.name for p in directory.iterdir()} == set(registered), 'EVIDENCE_ORPHAN_OR_MISSING')
    for oid in registered:
        base = directory / oid
        package = strict_json(safe_path(destination, base / 'package.json', exists=True).read_bytes())
        source = strict_json(safe_path(destination, base / 'source.json', exists=True).read_bytes())
        require(set(p.name for p in base.iterdir()) == {'package.json', 'source.json', 'response.body'}, 'EVIDENCE_MEMBERSHIP')
        require(digest(package) == oid and source['evidence_hash'] == oid and source['object_id'] == oid
                and source['request'] == package['request'] and source['retrieved_at'] == stamp(instant(package['retrieved_at']))
                and source['body_hash'] == digest(package['response'])
                and source['fixture_only'] == (package['namespace'] == 'FIXTURE')
                and (base / 'response.body').read_bytes() == encoded(package['response']), 'EVIDENCE_BINDING_CHANGED')
        if package.get('raw_reference'):
            interpreted = interpretation.validate(root, package, destination=destination, db=db)
            require(all(source[k] == v for k, v in interpreted.items()), 'INTERPRETATION_SOURCE_CHANGED')
        result.append(dict(object_id=oid, kind='DOCUMENT_FACT', request=source['request'], source=source,
                           body_path=str(base / 'response.body'), source_path=str(base / 'source.json'),
                           body_hash=file_hash(base / 'response.body'), source_hash=digest(source), transform_pins=source.get('transform_pins',default_pins)))
    if registered and any(not r['source']['fixture_only'] for r in result if r['kind'] == 'DOCUMENT_FACT'):
        # Recheck actual approval/source bytes at reopen; no admission is inferred
        # from an author-provided policy_hash alone.
        from astock.phase1.fact_admission import authorize
        for r in result:
            if r['kind'] == 'DOCUMENT_FACT' and not r['source']['fixture_only']:
                s = r['source']
                signed = s['approval']
                # Approval binds the entire batch, reconstructed from its registered packages.
                require(set(s['batch_object_ids']) <= set(registered), 'APPROVED_FACT_BATCH_MEMBERSHIP')
                batch = [strict_json((directory / i / 'package.json').read_bytes()) for i in s['batch_object_ids']]
                checked = authorize(root, destination, batch, signed, s['human'], runtime=False)
                require(all(s[k] == v for k, v in checked.items()), 'FACT_POLICY_BINDING_CHANGED')
    return sorted(result, key=lambda r: r['object_id'])


def verify_generation_inputs(root, destination, db):
    """Compare every generation to raw-derived truth, including all immutable columns."""
    from astock.phase1 import versions
    refs = db.execute("SELECT payload FROM p1_meta WHERE key='generation_inputs'").fetchone()
    generations = db.execute('SELECT * FROM p1_generation ORDER BY generation_hash').fetchall()
    if not generations:
        require(not fact_rows(db) and not db.execute('SELECT 1 FROM p1_quality').fetchone(), 'UNPUBLISHED_FACTS')
        return
    require(refs is not None, 'GENERATION_INPUT_MEMBERSHIP')
    descriptors = strict_json(refs[0].encode())
    require(len({r['object_id'] for r in descriptors}) == len(descriptors), 'GENERATION_INPUT_MEMBERSHIP')
    owner = strict_json(db.execute("SELECT payload FROM p1_meta WHERE key='owner'").fetchone()[0].encode())
    expected_namespace = owner.get('source',{}).get('namespace',owner['namespace'])
    by_id = {r['object_id']: r for r in descriptors}
    persisted = {r['fact_hash']: r for r in fact_rows(db)}
    expected_all, quality_all, seen_objects = {}, {}, set()
    omit = ('body_path', 'source_path', 'transform_pins')
    for gh, payload, content, namespace, completed in generations:
        manifest = strict_json(payload.encode())
        require(digest(manifest) == gh and namespace == manifest['namespace'], 'GENERATION_BINDING_CHANGED')
        require(namespace==expected_namespace and all(r['source']['fixture_only']==(namespace=='FIXTURE') for r in manifest['objects']), 'GENERATION_NAMESPACE_CHANGED')
        versions.validate(root, manifest['pins'])
        require(len({r['object_id'] for r in manifest['objects']}) == len(manifest['objects']), 'GENERATION_INPUT_MEMBERSHIP')
        expected = {}
        for bound in manifest['objects']:
            oid = bound['object_id']; seen_objects.add(oid)
            require(oid in by_id, 'GENERATION_INPUT_MEMBERSHIP')
            descriptor = by_id[oid]
            require({k:v for k,v in descriptor.items() if k not in omit} ==
                    {k:v for k,v in bound.items() if k not in omit}, 'GENERATION_INPUT_BINDING_CHANGED')
            pinned = bound.get('transform_pins', manifest['pins'])
            if descriptor.get('transform_pins'):
                require(descriptor['transform_pins'] == pinned, 'TRANSFORM_BINDING_CHANGED')
            fs, qs = source_decode(root, descriptor, destination=destination, db=db, pinned=pinned)
            expected.update({f['fact_hash']:f for f in fs})
            for q in qs:
                q = dict(q, event_date=day(q['event_date']).isoformat() if q['event_date'] else None, source_object=oid)
                quality_all[digest(q)] = q
        hashes = [r[0] for r in db.execute('SELECT fact_hash FROM p1_lineage WHERE generation_hash=? ORDER BY fact_hash', [gh]).fetchall()]
        require(hashes == sorted(expected) and all(persisted.get(h) == expected[h] for h in hashes), 'SOURCE_DERIVED_FACT_SET_CHANGED')
        require(content == digest([expected[h] for h in sorted(expected)]), 'SOURCE_DERIVED_CONTENT_CHANGED')
        expected_all.update(expected)
    require(seen_objects == set(by_id), 'GENERATION_INPUT_MEMBERSHIP')
    require(persisted == expected_all, 'SOURCE_DERIVED_FACT_SET_CHANGED')
    actual_quality = {}
    for h, ds, entity, date, reason, oid, payload in db.execute('SELECT * FROM p1_quality').fetchall():
        q = strict_json(payload.encode())
        require(digest(q) == h and (ds,entity,date.isoformat() if date else None,reason,oid) ==
                tuple(q[k] for k in ('dataset','entity','event_date','reason','source_object')), 'QUALITY_BINDING_CHANGED')
        actual_quality[h] = q
    require(actual_quality == quality_all, 'SOURCE_DERIVED_QUALITY_SET_CHANGED')


def fact_rows(db) -> list[dict]:
    q = db.execute('SELECT * FROM p1_fact ORDER BY fact_hash')
    keys = [c[0] for c in q.description]
    output = []
    for row in q.fetchall():
        f = dict(zip(keys, row, strict=True))
        f['payload'] = strict_json(f['payload'].encode())
        for k in ('event_date', 'valid_from', 'valid_to'):
            f[k] = f[k].isoformat() if f[k] else None
        for k in ('published_at', 'available_at', 'retrieved_at'):
            f[k] = stamp(f[k]) if f[k] else None
        h = f.pop('fact_hash')
        require(digest(f) == h, 'PERSISTED_FACT_CHANGED')
        f['fact_hash'] = h
        output.append(f)
    return output


def source_decode(root: Path, descriptor: dict, *, destination=None, db=None, pinned=None) -> tuple[list, list]:
    require(file_hash(Path(descriptor['body_path'])) == descriptor['body_hash'] and
            file_hash(Path(descriptor['source_path'])) == descriptor['source_hash'], 'INPUT_CHANGED_DURING_BUILD')
    require(Path(descriptor['source_path']).read_bytes() == encoded(descriptor['source']) and
            descriptor['request'] == descriptor['source']['request'] and descriptor['object_id'] == descriptor['source']['object_id'], 'INPUT_SOURCE_DESCRIPTOR_CHANGED')
    if descriptor['kind'] == 'CAPTURE':
        origin = Path(descriptor['body_path']).parents[2]
        if destination is not None and origin.resolve() == destination.resolve() and db is not None:
            acquisition.physical_validate(root, origin, db, descriptor['source']['logical_id'])
        else:
            with acquisition.store(root, origin, read_only=True) as original:
                acquisition.physical_validate(root, origin, original, descriptor['source']['logical_id'])
    if descriptor['kind'] == 'DOCUMENT_FACT':
        directory = Path(descriptor['body_path']).parent
        package = strict_json(safe_path(directory, directory / 'package.json', exists=True).read_bytes())
        require(digest(package) == descriptor['object_id'] and descriptor['request'] == package['request']
                and encoded(package['response']) == Path(descriptor['body_path']).read_bytes(), 'GENERATION_PACKAGE_CHANGED')
        if package.get('raw_reference'):
            interpretation.validate(root, package, destination=destination, db=db)
        source = descriptor['source']
        if not source['fixture_only']:
            from astock.phase1.fact_admission import authorize
            store = directory.parents[1]
            batch = [strict_json(safe_path(store, store / 'evidence' / i / 'package.json', exists=True).read_bytes()) for i in source['batch_object_ids']]
            checked = authorize(root, store, batch, source['approval'], source['human'], runtime=False)
            require(all(source[k] == v for k, v in checked.items()), 'GENERATION_POLICY_CHANGED')
    from astock.phase1 import versions
    cs, ds = versions.adapters(root, pinned or descriptor.get('transform_pins') or acquisition.pins(root))
    decoded = cs.decode(root, descriptor['request'], Path(descriptor['body_path']).read_bytes())
    return ds.facts(root, descriptor['request'], decoded['rows'], descriptor['source'])


def build(root: Path, destination: Path, *, source_destination: Path | None = None,
          fault=lambda stage: None) -> dict:
    """A rebuild imports fixed validated inputs; increment merges immutable facts."""
    source_destination = source_destination or destination
    derived = None
    if source_destination.resolve() != destination.resolve():
        with acquisition.store(root, source_destination, read_only=True) as src:
            verify_generation_inputs(root,source_destination,src)
            descriptors=inputs(root,source_destination,src)
            source_owner=strict_json(src.execute("SELECT payload FROM p1_meta WHERE key='owner'").fetchone()[0].encode())
            if source_owner['namespace']=='DERIVED_ONLY':
                descriptors += strict_json(src.execute("SELECT payload FROM p1_meta WHERE key='generation_inputs'").fetchone()[0].encode())
            source_namespace=source_owner.get('source',{}).get('namespace',source_owner['namespace'])
            derived=dict(path=str(source_destination.resolve()),namespace=source_namespace)
    else:
        descriptors = None
    with acquisition.store(root, destination, derived=derived) as db:
        target_owner=strict_json(db.execute("SELECT payload FROM p1_meta WHERE key='owner'").fetchone()[0].encode())
        fixture=target_owner.get('source',{}).get('namespace',target_owner['namespace'])=='FIXTURE'
        descriptors = descriptors if descriptors is not None else inputs(root, destination, db)
        if target_owner['namespace']=='DERIVED_ONLY' and not descriptors:
            refs=db.execute("SELECT payload FROM p1_meta WHERE key='generation_inputs'").fetchone()
            descriptors=strict_json(refs[0].encode()) if refs else []
        require(bool(descriptors), 'NONEMPTY_BUILD_INPUTS_REQUIRED')
        require(all(r['source']['fixture_only'] == fixture for r in descriptors), 'REBUILD_NAMESPACE_CHANGED')
        refs = db.execute("SELECT payload FROM p1_meta WHERE key='generation_inputs'").fetchone()
        previous_inputs = strict_json(refs[0].encode()) if refs else []
        all_inputs = {r['object_id']: r for r in previous_inputs + descriptors}
        descriptors = [all_inputs[k] for k in sorted(all_inputs)]
        manifest = dict(protocol=PROTOCOL, namespace='FIXTURE' if fixture else 'PRODUCTION', pins=acquisition.pins(root), objects=[
            {k: v for k, v in r.items() if k not in ('body_path', 'source_path')} for r in descriptors])
        generation = digest(manifest)
        verify_generation_inputs(root, destination, db)
        old = fact_rows(db)
        prepared, findings = [], []
        for r in descriptors:
            fs, qs = source_decode(root, r, destination=destination, db=db)
            prepared.extend(fs)
            findings.extend(dict(q, event_date=day(q['event_date']).isoformat() if q['event_date'] else None,
                                 source_object=r['object_id']) for q in qs)
        expected = {f['fact_hash']: f for f in prepared}
        require(all(expected.get(f['fact_hash']) == f for f in old), 'OLD_FACT_NOT_SOURCE_DERIVED')
        content_hash = digest([expected[h] for h in sorted(expected)])
        previous = db.execute('SELECT input_manifest,logical_content_hash FROM p1_generation WHERE generation_hash=?', [generation]).fetchone()
        if previous:
            require(previous == (encoded(manifest).decode(), content_hash), 'GENERATION_CHANGED')
            verify_generation_inputs(root, destination, db)
            validate_lineage(db)
            return dict(status='ALREADY_VALID', generation_hash=generation, logical_content_hash=content_hash, facts=len(expected))
        def append():
            for f in prepared:
                values = [f[k] for k in ('fact_hash', 'dataset', 'domain', 'series_key', 'entity', 'event_date', 'valid_from', 'valid_to', 'published_at', 'available_at', 'retrieved_at', 'precision', 'knowledge_basis', 'source_object', 'source_row')]
                values += [encoded(f['payload']).decode(), f['eligibility']]
                db.execute('INSERT INTO p1_fact VALUES (' + ','.join('?' for _ in values) + ') ON CONFLICT DO NOTHING', values)
            db.execute('INSERT INTO p1_generation VALUES (?,?,?,?,?)', [generation, encoded(manifest).decode(), content_hash, manifest['namespace'], stamp()])
            db.execute("INSERT OR REPLACE INTO p1_meta VALUES ('generation_inputs',?)", [encoded(descriptors).decode()])
            for h in expected:
                db.execute('INSERT INTO p1_lineage VALUES (?,?)', [generation, h])
            for q in findings:
                db.execute('INSERT INTO p1_quality VALUES (?,?,?,?,?,?,?) ON CONFLICT DO NOTHING', [digest(q), q['dataset'], q['entity'], q['event_date'], q['reason'], q['source_object'], encoded(q).decode()])
            fault('before_readback')
            # Read source bytes again INSIDE the fact transaction, not only before it.
            for r in descriptors:
                source_decode(root, r, destination=destination, db=db)
            require(fact_rows(db) == [expected[h] for h in sorted(expected)], 'GENERATION_READBACK_CHANGED')
            verify_generation_inputs(root, destination, db)
            validate_lineage(db)
        acquisition.transaction(db, append)
        return dict(status='COMPLETE', generation_hash=generation, logical_content_hash=content_hash, facts=len(expected), research_admitted=False)


def validate_lineage(db) -> dict:
    rows = fact_rows(db)
    by_hash = {f['fact_hash']: f for f in rows}
    checked = 0
    referenced = set()
    for generation, payload, content, namespace, completed in db.execute('SELECT * FROM p1_generation ORDER BY generation_hash').fetchall():
        manifest = strict_json(payload.encode())
        require(digest(manifest) == generation and namespace == manifest['namespace'], 'GENERATION_BINDING_CHANGED')
        hashes = [r[0] for r in db.execute('SELECT fact_hash FROM p1_lineage WHERE generation_hash=? ORDER BY fact_hash', [generation]).fetchall()]
        referenced.update(hashes)
        require(bool(hashes) and digest([by_hash[h] for h in hashes]) == content, 'LINEAGE_CONTENT_CHANGED')
        objects = {r['object_id'] for r in manifest['objects']}
        # An increment includes earlier facts; every member must be evidenced in
        # this manifest or an earlier immutable generation.
        require(all(by_hash[h]['source_object'] in objects for h in hashes), 'LINEAGE_SOURCE_MISSING')
        checked += 1
    require(set(by_hash) == referenced, 'UNPUBLISHED_FACTS')
    owner = strict_json(db.execute("SELECT payload FROM p1_meta WHERE key='owner'").fetchone()[0].encode())
    verify_generation_inputs(Path(owner['root']), Path(owner['destination']), db)
    return dict(status='VALID', generations=checked, facts=len(rows))


def coverage(root: Path, destination: Path, *, expectations: list | None = None, target_manifest=None) -> dict:
    with acquisition.store(root, destination, read_only=True) as db:
        acquisition.audit(root, destination, db)
        verify_generation_inputs(root, destination, db)
        validate_lineage(db)
        rows = fact_rows(db)
        findings = [strict_json(p.encode()) for p, in db.execute('SELECT payload FROM p1_quality ORDER BY finding_hash').fetchall()]
        calls = acquisition.local_consumption(db)
    for r in calls:
        if r['states'][-1] not in ('COMPLETE', 'RAW_RETAINED'):
            findings.append(dict(dataset=r['request']['dataset'], reason='ACQUISITION_' + r['states'][-1], source_object=r['object_id'], entity=None, event_date=None))
    identities = [r for r in rows if r['dataset'] == 'security_identifiers']
    for r in rows:
        if r['dataset'] in contracts.MARKET and r['event_date']:
            identity = domains.resolve(rows, r['entity'], r['event_date'], r['available_at'])
            if identity['status'] != 'RESOLVED':
                findings.append(dict(dataset=r['dataset'], reason='IDENTITY_' + identity['status'], entity=r['entity'], event_date=r['event_date'], source_object=r['source_object']))
            exchange = identity.get('exchange')
            sessions = [c for c in rows if c['dataset'] == 'trade_cal' and c['payload']['exchange'] == exchange and c['event_date'] == r['event_date'] and instant(c['available_at']) <= instant(r['available_at'])]
            if not sessions or any(c['payload']['is_open'] != 1 for c in sessions):
                findings.append(dict(dataset=r['dataset'], reason='SESSION_EVIDENCE_REQUIRED_OR_CLOSED', entity=r['entity'], event_date=r['event_date'], source_object=r['source_object']))
    for e in expectations or []:
        matches = [r for r in rows if r['dataset'] == e['dataset'] and r['entity'] == e.get('entity') and r['event_date'] == e.get('event_date')]
        if not matches:
            findings.append(dict(**e, reason='EXPECTED_OBSERVATION_MISSING_NOT_INFERRED_SUSPENDED', source_object=None))
    # Independent source values are retained; disagreements are never averaged.
    groups = defaultdict(list)
    for r in rows:
        groups[(r['dataset'], r['entity'], r['event_date'], r['available_at'])].append(r)
    for group in groups.values():
        if len({digest(r['payload']) for r in group}) > 1:
            r = group[0]
            findings.append(dict(dataset=r['dataset'], entity=r['entity'], event_date=r['event_date'], source_object=None, reason='SOURCE_VERSION_CONFLICT'))
    for reference in [r for r in rows if r['dataset'] == 'market_crosscheck']:
        primaries = [r for r in rows if r['dataset'] == 'daily' and r['entity'] == reference['entity'] and r['event_date'] == reference['event_date']]
        known, conflict = domains.known_versions(primaries, reference['available_at'])
        if len(known) != 1 or conflict:
            findings.append(dict(dataset='market_crosscheck', entity=reference['entity'], event_date=reference['event_date'], source_object=reference['source_object'], reason='CROSS_SOURCE_PRIMARY_UNKNOWN_OR_CONFLICT'))
            continue
        primary = known[0]['payload']
        converted = {k: primary.get(k) for k in ('open', 'high', 'low', 'close')}
        converted.update(volume_shares=primary['vol'] * 100 if primary.get('vol') is not None else None,
                         amount_cny=primary['amount'] * 1000 if primary.get('amount') is not None else None)
        changed = [k for k, v in converted.items() if v is not None and reference['payload'][k] is not None and v != reference['payload'][k]]
        if changed:
            findings.append(dict(dataset='market_crosscheck', entity=reference['entity'], event_date=reference['event_date'], source_object=reference['source_object'], reason='CROSS_SOURCE_VALUE_DISAGREEMENT', fields=changed, selection='NEITHER_SOURCE_OVERWRITTEN'))
    from astock.phase1 import coverage_targets
    target_report=coverage_targets.evaluate(rows,target_manifest or coverage_targets.target(rows))
    for goal in target_report['obligations']:
        if goal['state']=='missing':
            findings.append(dict(dataset=goal['dataset'],entity=goal.get('entity'),event_date=goal['event_date'],source_object=None,reason='EXPECTED_OBSERVATION_MISSING_NOT_INFERRED_SUSPENDED'))
    for q in findings:
        candidates = [r for r in rows if r['entity'] == q.get('entity') and r['event_date'] == q.get('event_date')]
        identity = domains.resolve(rows, q.get('entity'), q['event_date'], max((r['available_at'] for r in candidates), default=stamp())) if q.get('entity') and q.get('event_date') else {}
        q['exchange'] = identity.get('exchange') or next((r['payload'].get('exchange') for r in candidates if r['payload'].get('exchange')), 'UNKNOWN')
        q['episode_id'] = identity.get('episode_id') or 'UNKNOWN'
    dimensions = Counter((q['dataset'], q['reason'], (q.get('event_date') or 'UNKNOWN')[:4], q.get('entity') or 'UNKNOWN', q['exchange'], q['episode_id']) for q in findings)
    return dict(status='SOFTWARE_AUDIT_VALID_REAL_ADMISSION_BLOCKED', target_coverage=target_report, datasets=dict(Counter(r['dataset'] for r in rows)),
                domains=dict(Counter(r['domain'] for r in rows)), reasons=dict(Counter(q['reason'] for q in findings)),
                dimensions=[dict(dataset=d, reason=q, year=y, entity=e, exchange=x, episode_id=ep, count=n) for (d, q, y, e, x, ep), n in sorted(dimensions.items())],
                findings=findings, old_findings_preserved=402060, research_admitted=False,
                missing_status_does_not_mean_normal=True, historical_coverage_certified=False)


def query(root: Path, destination: Path, security_id: str, event: str, as_of: str, *, taxonomy=None) -> dict:
    with acquisition.store(root, destination, read_only=True) as db:
        inputs(root, destination, db)
        verify_generation_inputs(root, destination, db)
        validate_lineage(db)
        return domains.historical_snapshot(fact_rows(db), security_id, event, as_of, taxonomy=taxonomy)
