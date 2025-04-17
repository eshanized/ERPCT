#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Hybrid Attack Module.
This module provides components for hybrid password attacks that combine
different attack strategies.
"""

from src.hybrid.combiner import PasswordCombiner
from src.hybrid.scheduler import AttackScheduler
from src.hybrid.strategy import HybridStrategy, DictionaryMaskStrategy, MaskDictionaryStrategy

__all__ = [
    'PasswordCombiner',
    'AttackScheduler',
    'HybridStrategy',
    'DictionaryMaskStrategy',
    'MaskDictionaryStrategy',
]
