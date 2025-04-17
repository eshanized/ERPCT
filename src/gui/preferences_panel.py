#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Preferences Panel (compatibility module).
This module re-exports the Preferences class as PreferencesPanel for backward compatibility.
"""

from src.gui.preferences import Preferences

# Re-export Preferences as PreferencesPanel for backward compatibility
PreferencesPanel = Preferences 