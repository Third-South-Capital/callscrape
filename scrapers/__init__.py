"""
Art opportunity scrapers package.
"""

from .base import BaseScraper
from .cafe import CafeScraper
from .artcall import ArtCallScraper
from .showsubmit import ShowSubmitScraper
from .artwork_archive import ArtworkArchiveScraper
from .zapplication import ZapplicationScraper

__all__ = [
    'BaseScraper',
    'CafeScraper',
    'ArtCallScraper',
    'ShowSubmitScraper',
    'ArtworkArchiveScraper',
    'ZapplicationScraper'
]

# Registry of all available scrapers
SCRAPERS = {
    'cafe': CafeScraper,
    'artcall': ArtCallScraper,
    'showsubmit': ShowSubmitScraper,
    'artwork_archive': ArtworkArchiveScraper,
    'zapplication': ZapplicationScraper
}