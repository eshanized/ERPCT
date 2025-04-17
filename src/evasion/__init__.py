#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT evasion techniques module.
This module provides detection avoidance mechanisms for password cracking.
"""

from src.evasion.base import EvasionBase
from src.evasion.delay import DelayManager
from src.evasion.protocol_specific import ProtocolSpecificEvasion
from src.evasion.retry_manager import RetryManager
from src.evasion.timing_pattern import TimingPattern
from src.evasion.detection_avoider import DetectionAvoider
from src.evasion.ip_rotator import IPRotator
from src.evasion.proxy import ProxyManager

__all__ = [
    'EvasionBase',
    'DelayManager',
    'ProtocolSpecificEvasion',
    'RetryManager',
    'TimingPattern',
    'DetectionAvoider',
    'IPRotator',
    'ProxyManager'
]
