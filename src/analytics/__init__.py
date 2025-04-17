#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT Analytics Module.
This package provides analytics, statistics, and visualization functionality for password cracking operations.
"""

from src.analytics.statistics import (
    AttackStatistics,
    calculate_success_rate,
    calculate_attempt_rate,
    calculate_protocol_stats,
    calculate_time_distribution,
    extract_common_patterns
)

from src.analytics.performance_metrics import (
    PerformanceTracker,
    calculate_throughput,
    calculate_resource_usage,
    analyze_bottlenecks,
    get_protocol_performance
)

from src.analytics.visualization import (
    create_attack_timeline,
    create_success_rate_chart,
    create_attempt_distribution,
    create_performance_graph,
    export_visualization
)

from src.analytics.optimization_advisor import (
    OptimizationAdvisor,
    analyze_attack_efficiency,
    get_optimization_recommendations,
    calculate_optimal_thread_count
)

from src.analytics.reporting import (
    generate_report,
    Report,
    ReportFormat,
    ReportSection,
    export_to_pdf,
    export_to_html,
    export_to_json
)

__version__ = '1.0.0'
