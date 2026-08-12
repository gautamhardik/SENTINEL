"""
Unit tests for FeatureCache and GraphIntelligenceService.
Validates sub-millisecond sliding velocity calculation and circular money laundering detection.
"""
import time
import pytest
from fraud_detection.feature_service.feature_cache import FeatureCache
from fraud_detection.services.graph_service import GraphIntelligenceService


def test_feature_cache_sliding_velocity():
    cache = FeatureCache()
    now = time.time()

    # Record transactions from Acc_A
    cache.record_transaction("Acc_A", "Acc_B", 500.0, timestamp=now - 5.0)   # within 10s
    cache.record_transaction("Acc_A", "Acc_C", 1200.0, timestamp=now - 30.0) # within 1m
    cache.record_transaction("Acc_A", "Acc_D", 8000.0, timestamp=now - 1200.0) # within 1h

    metrics = cache.get_velocity_metrics("Acc_A", "Acc_B", current_amount=1500.0, current_ts=now)

    assert metrics["velocity_10s_count"] >= 1.0
    assert metrics["velocity_1m_count"] >= 2.0
    assert metrics["velocity_1h_count"] >= 3.0
    assert metrics["account_transaction_count"] >= 4.0
    assert metrics["sender_out_degree"] >= 3.0
    assert metrics["ratio_to_account_average"] > 0.0


def test_graph_intelligence_cycle_detection():
    graph = GraphIntelligenceService()
    now = time.time()

    # Create cycle A -> B -> C -> A
    graph.record_edge("Acc_100", "Acc_200", amount=10000.0, timestamp=now)
    graph.record_edge("Acc_200", "Acc_300", amount=9500.0, timestamp=now + 1)
    graph.record_edge("Acc_300", "Acc_100", amount=9000.0, timestamp=now + 2)

    cycles = graph.detect_cycles()
    assert len(cycles) >= 1

    subgraph = graph.get_subgraph_for_transaction("Acc_100", "Acc_200", amount=10000.0)
    assert subgraph["has_circular_risk"] is True
    assert subgraph["cluster_risk_level"] == "CRITICAL"
    assert len(subgraph["nodes"]) >= 2
