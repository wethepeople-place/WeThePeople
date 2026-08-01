"""Dialect-safe Alembic default comparison helpers."""

from sqlalchemy import JSON


def compare_server_default(
    migration_context,
    inspected_column,
    metadata_column,
    inspected_default,
    metadata_default,
    rendered_metadata_default,
):
    """Compare PostgreSQL JSON defaults without unsupported JSON equality."""
    if migration_context.dialect.name != "postgresql" or not isinstance(metadata_column.type, JSON):
        return None

    def normalize(value):
        if value is None:
            return None
        text = str(value).strip()
        for suffix in ("::jsonb", "::json"):
            if text.lower().endswith(suffix):
                text = text[:-len(suffix)].strip()
        if len(text) >= 2 and text[0] == text[-1] == "'":
            text = text[1:-1]
        return text

    return normalize(inspected_default) != normalize(rendered_metadata_default)
