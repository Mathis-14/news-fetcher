"""Zero-cost news fetcher for RSS and Google News."""

from .api import fetch_news
from .fetcher import Article

__all__ = ["Article", "fetch_news"]
__version__ = "0.1.0"
