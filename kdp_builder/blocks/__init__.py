"""Block library system for AI-powered layout generation"""

from kdp_builder.blocks.block_schema import (
    BlockCategory,
    BlockComplexity,
    BLOCK_SCHEMA,
    PAGE_COMPOSITION_SCHEMA,
    create_block
)

__all__ = [
    "BlockCategory",
    "BlockComplexity",
    "BLOCK_SCHEMA",
    "PAGE_COMPOSITION_SCHEMA",
    "create_block"
]
