"""Read-only 007 acceptance using the locked DuckDB engine's catalog structure."""

from functools import lru_cache

import duckdb

from astock.data.raw_validation import require
from astock.paths import get_project_root

TABLES = ('slice_receipt_completion_binding', 'slice_receipt_validation_audit')


def _structure(db) -> tuple:
    # Reject views, temporary shadows and identically named tables in other schemas
    # or attached databases: admission queries must resolve to persistent main tables.
    identities = db.execute('''SELECT database_name=current_database(), schema_name,
        table_name, temporary FROM duckdb_tables() WHERE table_name IN (?,?)
        ORDER BY table_name''', TABLES).fetchall()
    require(identities == [(True, 'main', name, False) for name in TABLES]
            and db.execute('SELECT current_schema()').fetchone() == ('main',)
            and not db.execute('SELECT 1 FROM duckdb_views() WHERE view_name IN (?,?)', TABLES).fetchall(),
            'BINDING_SCHEMA_REQUIRED')
    columns = db.execute('''SELECT table_name, column_name, data_type, is_nullable, column_default
        FROM duckdb_columns() WHERE database_name=current_database() AND schema_name='main'
        AND table_name IN (?,?) ORDER BY table_name,column_index''', TABLES).fetchall()
    constraints = db.execute('''SELECT table_name, constraint_type, constraint_column_names,
        expression, referenced_table, referenced_column_names FROM duckdb_constraints()
        WHERE database_name=current_database() AND schema_name='main' AND table_name IN (?,?)''', TABLES).fetchall()
    # Names/OIDs and declaration order are immaterial. CHECK expressions here are
    # parser-normalized catalog values, compared with the same engine's reference
    # catalog, never with SQL source text. Column arrays preserve composite-key order.
    constraints = sorted((t, kind, tuple(cols), expression or '', target or '', tuple(refs))
                         for t, kind, cols, expression, target, refs in constraints)
    references = db.execute('''SELECT t.table_name, r.unique_constraint_catalog=current_database(),
        r.unique_constraint_schema, p.table_name, r.match_option, r.update_rule, r.delete_rule
        FROM information_schema.referential_constraints r
        JOIN information_schema.table_constraints t USING(constraint_catalog,constraint_schema,constraint_name)
        JOIN information_schema.table_constraints p
          ON p.constraint_catalog=r.unique_constraint_catalog
         AND p.constraint_schema=r.unique_constraint_schema AND p.constraint_name=r.unique_constraint_name
        WHERE t.table_catalog=current_database() AND t.table_schema='main'
        AND t.table_name IN (?,?) ORDER BY ALL''', TABLES).fetchall()
    return tuple(columns), tuple(constraints), tuple(references)


@lru_cache(maxsize=1)
def _reference_structure() -> tuple:
    # Only this versioned checkout is the reference, never a caller's deployment
    # directory. No files/warehouse are created or upgraded by this memory database.
    from astock.data.raw_writer import migrate

    root = get_project_root()
    with duckdb.connect(':memory:') as reference:
        migrate(reference, root)
        reference.execute((root / 'sql/007_slice_receipt_integrity.sql').read_text())
        return _structure(reference)


def require_integrity_schema(db, *, published: bool = True) -> None:
    """Draft mode is internal to explicit007's transaction, before version publication."""
    if published:
        require(db.execute('SELECT migration_id FROM schema_version WHERE version=7').fetchall()
                == [('007_slice_receipt_integrity',)], 'BINDING_SCHEMA_REQUIRED')
    require(_structure(db) == _reference_structure(), 'BINDING_SCHEMA_REQUIRED')
