"""add brand_exclusion to keyword_filter_configs

Revision ID: 7ddc7d8854d7
Revises: 40538b513b6e
Create Date: 2026-03-09 16:18:45.511720

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '7ddc7d8854d7'
down_revision: Union[str, Sequence[str], None] = '40538b513b6e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_ENTRIES = '[{"type": "word_count", "operator": "gte", "value": 2}, {"type": "brand_exclusion"}]'
MANAGED_TYPES = ("word_count", "brand_exclusion")


def upgrade() -> None:
    """Append default filter predicates to all business domains' keyword_filter_config."""
    # Domains with existing config: append the entries
    op.execute(f"""
        UPDATE business_domains
        SET keyword_filter_config = keyword_filter_config || '{DEFAULT_ENTRIES}'::jsonb
        WHERE keyword_filter_config IS NOT NULL
    """)
    # Domains with null config: set to the default list
    op.execute(f"""
        UPDATE business_domains
        SET keyword_filter_config = '{DEFAULT_ENTRIES}'::jsonb
        WHERE keyword_filter_config IS NULL
    """)


def downgrade() -> None:
    """Remove all default filter entries from keyword_filter_config."""
    type_list = ", ".join(f"'{t}'" for t in MANAGED_TYPES)
    op.execute(f"""
        UPDATE business_domains
        SET keyword_filter_config = (
            SELECT COALESCE(jsonb_agg(elem), '[]'::jsonb)
            FROM jsonb_array_elements(keyword_filter_config) AS elem
            WHERE elem ->> 'type' NOT IN ({type_list})
        )
        WHERE keyword_filter_config IS NOT NULL
    """)
    # Set empty arrays back to null for consistency
    op.execute("""
        UPDATE business_domains
        SET keyword_filter_config = NULL
        WHERE keyword_filter_config = '[]'::jsonb
    """)
