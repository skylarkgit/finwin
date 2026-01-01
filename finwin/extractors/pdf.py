"""PDF text extractor for finwin."""

from __future__ import annotations

import asyncio
import io
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Tuple

from pdfminer.high_level import extract_text as pdf_extract_text

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4)


def _extract_sync(pdf_bytes: bytes) -> Tuple[Optional[str], Optional[str]]:
    """Synchronous PDF text extraction."""
    try:
        # pdfminer can read from file-like object
        pdf_file = io.BytesIO(pdf_bytes)
        text = pdf_extract_text(pdf_file)
        
        if text and text.strip():
            return text.strip(), None
        
        return None, "No text extracted from PDF"
        
    except Exception as e:
        logger.warning(f"PDF extraction failed: {e}")
        return None, str(e)


class PDFExtractor:
    """Extracts text from PDF documents."""
    
    async def extract(
        self,
        pdf_bytes: bytes,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract text from PDF.
        
        Args:
            pdf_bytes: PDF file content as bytes
            
        Returns:
            Tuple of (extracted_text, error)
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            _extract_sync,
            pdf_bytes,
        )
