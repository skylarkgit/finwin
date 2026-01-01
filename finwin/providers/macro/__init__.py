"""Macroeconomic data providers."""

from finwin.providers.macro.base import BaseMacroProvider
from finwin.providers.macro.worldbank import WorldBankProvider

__all__ = [
    "BaseMacroProvider",
    "WorldBankProvider",
]
