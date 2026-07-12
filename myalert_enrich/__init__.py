"""MyAlert research CSV outcome enrichment (Phase F post-processor)."""

from myalert_enrich.config import EnrichmentConfig, load_config
from myalert_enrich.enricher import enrich_research_file, enrich_research_rows

__all__ = [
    "EnrichmentConfig",
    "load_config",
    "enrich_research_file",
    "enrich_research_rows",
]

__version__ = "1.0.0"
