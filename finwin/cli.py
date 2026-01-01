"""Command-line interface for finwin."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional

from finwin import ContextCollector
from finwin.cache import InMemoryCache
from finwin.sources import GoogleNewsSource, YFinanceSource, WebFetcher


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Gather financial context for stocks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --symbol TCS.NS --name "TCS"
  %(prog)s --symbol AAPL --news-items 5
  %(prog)s --symbol RELIANCE.NS --urls https://example.com/report.pdf
        """,
    )
    
    parser.add_argument(
        "--symbol",
        help="Yahoo Finance symbol (e.g., TCS.NS, AAPL)",
        default=None,
    )
    parser.add_argument(
        "--name",
        help="Company name (used for news query). Defaults to symbol.",
        default=None,
    )
    parser.add_argument(
        "--query",
        help="Custom news search query. Defaults to name or symbol.",
        default=None,
    )
    parser.add_argument(
        "--urls",
        nargs="*",
        default=[],
        help="Additional URLs to fetch (PDFs, company pages, etc.)",
    )
    parser.add_argument(
        "--news-items",
        type=int,
        default=10,
        help="Number of news items to fetch (default: 10)",
    )
    parser.add_argument(
        "--country",
        default="IN",
        help="News country code (default: IN)",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path (default: stdout as JSON)",
        default=None,
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching",
    )
    
    return parser.parse_args(argv)


async def async_main(args: argparse.Namespace) -> int:
    """Async main entry point."""
    # Build sources
    sources = []
    
    query = args.query or args.name or args.symbol
    
    if query:
        sources.append(GoogleNewsSource(
            max_items=args.news_items,
            country=args.country,
        ))
    
    if args.symbol:
        sources.append(YFinanceSource())
    
    if args.urls:
        sources.append(WebFetcher())
    
    if not sources:
        logging.error("No sources configured. Provide --symbol, --name, or --urls")
        return 1
    
    # Create collector
    cache = None if args.no_cache else InMemoryCache(default_ttl=300)
    
    async with ContextCollector(sources=sources, cache=cache) as collector:
        context = await collector.gather(
            symbol=args.symbol,
            query=query,
            extra_urls=args.urls if args.urls else None,
            max_items=args.news_items,
        )
    
    # Output
    indent = 2 if args.pretty else None
    json_output = context.model_dump_json(indent=indent)
    
    if args.output:
        Path(args.output).write_text(json_output, encoding="utf-8")
        logging.info(f"Saved to: {args.output}")
    else:
        print(json_output)
    
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point."""
    args = parse_args(argv)
    setup_logging(args.verbose)
    
    try:
        return asyncio.run(async_main(args))
    except KeyboardInterrupt:
        logging.info("Interrupted")
        return 130
    except Exception as e:
        logging.exception(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
