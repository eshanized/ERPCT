#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Setup script for ERPCT - Enhanced Rapid Password Cracking Tool.
"""

import os
from setuptools import setup, find_packages

# Get version from package
about = {}
with open(os.path.join("src", "__init__.py")) as f:
    exec(f.read(), about)

# Get long description from README
with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

# Core requirements
requirements = [
    "paramiko>=2.7.0",        # For SSH protocol
    "requests>=2.25.0",       # For HTTP-based protocols
    "beautifulsoup4>=4.9.0",  # For HTML parsing
]

# Optional GUI requirements
gui_requirements = [
    "PyGObject>=3.36.0",
]

# Development requirements
dev_requirements = [
    "pytest>=6.0.0",
    "black>=21.5b2",
    "flake8>=3.9.0",
    "isort>=5.9.0",
    "mypy>=0.812",
]

setup(
    name="erpct",
    version=about["__version__"],
    description="Enhanced Rapid Password Cracking Tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author=about["__author__"],
    author_email="your.email@example.com",
    url="https://github.com/eshanized/ERPCT",
    packages=find_packages(),
    package_data={
        "erpct": ["resources/*"],
    },
    entry_points={
        "console_scripts": [
            "erpct=src.main:main",
        ],
        "gui_scripts": [
            "erpct-gui=src.gui.main:main",
        ],
    },
    install_requires=requirements,
    extras_require={
        "gui": gui_requirements,
        "dev": dev_requirements,
        "all": gui_requirements + dev_requirements,
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Security",
    ],
    python_requires=">=3.8",
)
