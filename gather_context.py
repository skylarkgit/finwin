#!/usr/bin/env python3
"""
Collect unstructured context (text + numbers) for ANY stock.

Outputs:
  out/<slug>/
    context.json
    raw_text/
      *.txt
    downloads/
      *.pdf, *.html
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, quote_plus
import base64

import logging
import requests
import feedparser
import trafilatura
import yfinance as yf
from bs4 import BeautifulSoup
from pdfminer.high_level import extract_text as pdf_extract_text

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 25
DEFAULT_SLEEP = 1.0

HEADERS = {
    # Some sites reject default python UA
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) StockContextCollector/1.0",
    "Accept-Language": "en-IN,en;q=0.9",
}

@dataclass
class FetchResult:
    url: str
    status: int
    content_type: str
    saved_path: Optional[str]
    extracted_text_path: Optional[str]
    error: Optional[str]

def safe_slug(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")[:80] or "output"

def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def guess_ext(content_type: str, url: str) -> str:
    ct = (content_type or "").lower()
    if "pdf" in ct or url.lower().endswith(".pdf"):
        return ".pdf"
    if "html" in ct or "text/" in ct:
        return ".html"
    return ".bin"

def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", errors="ignore")

def fetch_url(
    sess: requests.Session,
    url: str,
    out_downloads: Path,
    out_raw_text: Path,
    sleep_s: float = DEFAULT_SLEEP,
) -> FetchResult:
    try:
        r = sess.get(url, headers=HEADERS, timeout=DEFAULT_TIMEOUT, allow_redirects=True)
        ct = r.headers.get("Content-Type", "")
        status = r.status_code

        ext = guess_ext(ct, url)
        fname = f"{safe_slug(Path(urlparse(url).path).stem or 'page')}-{sha1(url)}{ext}"
        saved = out_downloads / fname
        saved.write_bytes(r.content)

        text_path = None
        extracted = None

        if status >= 200 and status < 300:
            if ext == ".pdf":
                try:
                    extracted = pdf_extract_text(str(saved)) or ""
                except Exception as e:
                    return FetchResult(url, status, ct, str(saved), None, f"PDF extract failed: {e}")
            else:
                # Use trafilatura for cleaner extraction
                try:
                    downloaded = trafilatura.fetch_url(url)
                    extracted = trafilatura.extract(downloaded, include_comments=False, include_tables=True) if downloaded else None
                except Exception:
                    extracted = None

                if not extracted:
                    # fallback: bs4 plain text
                    soup = BeautifulSoup(r.text, "html.parser")
                    extracted = soup.get_text("\n", strip=True)

            if extracted:
                text_fname = f"{safe_slug(Path(urlparse(url).path).stem or 'text')}-{sha1(url)}.txt"
                text_path = out_raw_text / text_fname
                write_text(text_path, extracted)

        time.sleep(sleep_s)
        return FetchResult(url, status, ct, str(saved), str(text_path) if text_path else None, None)

    except Exception as e:
        return FetchResult(url, -1, "", None, None, str(e))

def resolve_google_news_url(url: str, sess: requests.Session) -> str:
    """
    Google News RSS links require a special API call to resolve to the actual article URL.
    This fetches the page, extracts the data-p attribute, and calls Google's batchexecute API.
    """
    if "news.google.com/rss/articles/" not in url:
        return url
    
    try:
        browser_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        }
        
        # Step 1: Fetch the Google News article page
        r = sess.get(url, headers=browser_headers, timeout=DEFAULT_TIMEOUT)
        if r.status_code != 200:
            logger.warning(f"Failed to fetch Google News page: {r.status_code}")
            return url
        
        # Step 2: Parse and extract data-p attribute from c-wiz element
        soup = BeautifulSoup(r.text, "html.parser")
        cwiz = soup.find("c-wiz", attrs={"data-p": True})
        if not cwiz:
            logger.warning("Could not find c-wiz[data-p] element")
            return url
        
        data_p = cwiz.get("data-p")
        if not data_p:
            logger.warning("data-p attribute is empty")
            return url
        
        # Step 3: Parse the data-p JSON (it has a weird prefix)
        # Format: %.@.[...] needs to become ["garturlreq",[...]
        try:
            json_str = data_p.replace('%.@.', '["garturlreq",')
            obj = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse data-p JSON: {e}")
            return url
        
        # Step 4: Build the payload for batchexecute API
        # The payload uses a subset of the parsed object
        req_data = obj[:-6] + obj[-2:]  # Remove middle elements, keep first part and last 2
        
        payload = {
            'f.req': json.dumps([[["Fbv4je", json.dumps(req_data), "null", "generic"]]])
        }
        
        post_headers = {
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        }
        
        # Step 5: Call the batchexecute API
        post_r = sess.post(
            "https://news.google.com/_/DotsSplashUi/data/batchexecute",
            data=payload,
            headers=post_headers,
            timeout=DEFAULT_TIMEOUT
        )
        
        if post_r.status_code != 200:
            logger.warning(f"batchexecute API returned {post_r.status_code}")
            return url
        
        # Step 6: Parse the response
        # Response format: )]}'<newline><json>
        response_text = post_r.text
        if response_text.startswith(")]}'"):
            response_text = response_text[4:].strip()
        
        try:
            response_json = json.loads(response_text)
            # Navigate: [0][2] contains a JSON string, parse it, then [1] is the URL
            array_string = response_json[0][2]
            inner_array = json.loads(array_string)
            article_url = inner_array[1]
            
            if article_url and article_url.startswith("http"):
                logger.info(f"Resolved Google News URL: {article_url}")
                return article_url
        except (json.JSONDecodeError, IndexError, KeyError, TypeError) as e:
            logger.warning(f"Failed to parse batchexecute response: {e}")
            return url
            
    except Exception as e:
        logger.warning(f"Failed to resolve Google News URL: {e}")
    
    return url


def google_news_rss(query: str, country: str = "IN", lang: str = "en") -> str:
    # No key needed. Change country/lang if you want.
    # Example: https://news.google.com/rss/search?q=TCS&hl=en-IN&gl=IN&ceid=IN:en
    q = quote_plus(query)
    return f"https://news.google.com/rss/search?q={q}&hl={lang}-{country}&gl={country}&ceid={country}:{lang}"

def collect_news(sess: requests.Session, query: str, max_items: int) -> List[Dict[str, Any]]:
    rss = google_news_rss(query)
    feed = feedparser.parse(rss)
    items = []
    for entry in feed.entries[:max_items]:
        items.append({
            "title": getattr(entry, "title", ""),
            "link": getattr(entry, "link", ""),
            "published": getattr(entry, "published", ""),
            "source": getattr(entry, "source", {}).get("title") if hasattr(entry, "source") else None,
        })
    return items

def yf_numbers(symbol: str) -> Dict[str, Any]:
    """
    Best-effort: yfinance coverage varies by exchange.
    For India: try SYMBOL.NS or SYMBOL.BO
    """
    data: Dict[str, Any] = {"symbol": symbol, "ok": False}
    try:
        t = yf.Ticker(symbol)
        info = t.info or {}
        data["info"] = {
            k: info.get(k)
            for k in [
                "shortName", "longName", "sector", "industry", "website",
                "marketCap", "currency", "exchange", "quoteType",
                "trailingPE", "forwardPE", "priceToBook",
                "currentPrice", "previousClose", "fiftyTwoWeekHigh", "fiftyTwoWeekLow",
                "beta", "dividendYield",
            ]
        }

        # These can be empty for some tickers
        # Note: DataFrame columns are Timestamps, convert to str for JSON serialization
        try:
            fin = t.financials
            if fin is not None and not fin.empty:
                data["financials"] = fin.rename(columns=str).to_dict()
        except Exception:
            pass

        try:
            qfin = t.quarterly_financials
            if qfin is not None and not qfin.empty:
                data["quarterly_financials"] = qfin.rename(columns=str).to_dict()
        except Exception:
            pass

        try:
            bs = t.balance_sheet
            if bs is not None and not bs.empty:
                data["balance_sheet"] = bs.rename(columns=str).to_dict()
        except Exception:
            pass

        try:
            cf = t.cashflow
            if cf is not None and not cf.empty:
                data["cashflow"] = cf.rename(columns=str).to_dict()
        except Exception:
            pass

        data["ok"] = True
    except Exception as e:
        data["error"] = str(e)
    return data

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", help="Yahoo Finance symbol (e.g., TCS.NS, 543928.BO, AAPL)", default=None)
    ap.add_argument("--name", help="Company name (used for folder + news query). If omitted, uses symbol.", default=None)
    ap.add_argument("--query", help="News query. If omitted, uses name or symbol.", default=None)
    ap.add_argument("--urls", nargs="*", default=[], help="Extra URLs to fetch (company site, filings PDFs, etc.)")
    ap.add_argument("--news-items", type=int, default=10)
    ap.add_argument("--sleep", type=float, default=1.0)
    ap.add_argument("--out", default="out")
    args = ap.parse_args()

    label = args.name or args.symbol or "stock"
    slug = safe_slug(label)
    out_root = Path(args.out) / slug
    out_downloads = out_root / "downloads"
    out_raw_text = out_root / "raw_text"
    ensure_dir(out_downloads)
    ensure_dir(out_raw_text)

    sess = requests.Session()

    context: Dict[str, Any] = {
        "meta": {
            "label": label,
            "symbol": args.symbol,
            "query": args.query,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        },
        "numbers": {},
        "news": [],
        "fetches": [],
    }

    # 1) Numbers (best-effort)
    if args.symbol:
        context["numbers"]["yfinance"] = yf_numbers(args.symbol)

    # 2) News list from RSS
    q = args.query or args.name or args.symbol or label
    if q:
        news_items = collect_news(sess, q, args.news_items)
        context["news"] = news_items

        # Fetch top news pages too (raw text)
        for item in news_items:
            link = item.get("link")
            if link:
                # Resolve Google News redirect URLs to actual article URLs
                resolved_link = resolve_google_news_url(link, sess)
                item["resolved_link"] = resolved_link  # Store the resolved URL
                fr = fetch_url(sess, resolved_link, out_downloads, out_raw_text, sleep_s=args.sleep)
                context["fetches"].append(asdict(fr))

    # 3) Fetch user-provided URLs (filings, company site, PDFs, etc.)
    for url in args.urls:
        fr = fetch_url(sess, url, out_downloads, out_raw_text, sleep_s=args.sleep)
        context["fetches"].append(asdict(fr))

    # Save context.json
    def check_json_keys(obj, path=""):
        """Log any non-serializable keys in nested dicts."""
        if isinstance(obj, dict):
            for k, v in obj.items():
                key_path = f"{path}.{k}" if path else str(k)
                if not isinstance(k, (str, int, float, bool, type(None))):
                    logger.warning(f"Non-serializable key at '{key_path}': {type(k).__name__} = {k!r}")
                check_json_keys(v, key_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                check_json_keys(item, f"{path}[{i}]")

    check_json_keys(context)
    (out_root / "context.json").write_text(json.dumps(context, indent=2), encoding="utf-8")

    print(f"Saved to: {out_root}")

if __name__ == "__main__":
    main()
