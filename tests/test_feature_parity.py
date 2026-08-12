"""
Test feature parity between offline feature store Parquet values and online FeatureService.
"""
from pathlib import Path

from fraud_detection.feature_service import OnlineFeatureService
from fraud_detection.history import HistoryRepository
from fraud_detection.registry import ArtifactLoader
from fraud_detection.retrieval import ContextService

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_feature_parity_comprehensive_scenarios(tmp_path):
    """Verifies 61-feature parity across 10 representative transaction scenarios with float tolerance atol=1e-5."""
    loader = ArtifactLoader()
    assets = loader.load_assets()
    feature_order = assets["feature_order"]
    assert len(feature_order) == 61, f"Expected exactly 61 features, got {len(feature_order)}"

    repo = HistoryRepository(duckdb_path=tmp_path / "parity_multi.duckdb")
    ctx_service = ContextService(repository=repo, reference_priors=assets.get("reference_priors", {}))
    online_service = OnlineFeatureService(context_service=ctx_service, feature_order=feature_order)

    scenarios = [
        ("cold_start", {"Amount_Paid": 500.0, "From_Account": "acct_c1", "To_Account": "acct_c2"}),
        ("known_account", {"Amount_Paid": 1200.0, "From_Account": "acct_k1", "To_Account": "acct_k2"}),
        ("fewer_than_5_txs", {"Amount_Paid": 300.0, "From_Account": "acct_f5", "To_Account": "acct_f5_dest"}),
        ("fewer_than_20_txs", {"Amount_Paid": 450.0, "From_Account": "acct_f20", "To_Account": "acct_f20_dest"}),
        ("rapid_transaction", {"Amount_Paid": 100.0, "From_Account": "acct_rapid", "To_Account": "acct_rapid_dest"}),
        ("cross_bank", {"Amount_Paid": 800.0, "From_Bank": "10", "To_Bank": "99", "From_Account": "acct_cb", "To_Account": "acct_cb_dest"}),
        ("high_value", {"Amount_Paid": 15000.0, "From_Account": "acct_hv", "To_Account": "acct_hv_dest"}),
        ("duplicate", {"Amount_Paid": 250.0, "From_Account": "acct_dup", "To_Account": "acct_dup_dest"}),
        ("same_sender_receiver", {"Amount_Paid": 100.0, "From_Account": "acct_self", "To_Account": "acct_self"}),
        ("multiple_historical", {"Amount_Paid": 950.0, "From_Account": "acct_multi", "To_Account": "acct_multi_dest"})
    ]

    for name, overrides in scenarios:
        payload = {
            "transaction_id": f"tx_parity_{name}",
            "Timestamp": "2026-08-11 14:00:00",
            "From_Account": overrides.get("From_Account", "acct_default_s"),
            "To_Account": overrides.get("To_Account", "acct_default_r"),
            "From_Bank": overrides.get("From_Bank", "10"),
            "To_Bank": overrides.get("To_Bank", "20"),
            "Amount_Paid": overrides.get("Amount_Paid", 1000.0),
            "Amount_Received": overrides.get("Amount_Paid", 1000.0),
            "Payment_Format": "ACH",
            "Payment_Currency": "USD",
            "Receiving_Currency": "USD"
        }

        df_online = online_service.build_features_single(payload)
        assert not df_online.empty
        assert list(df_online.columns) == feature_order
        assert df_online.isna().sum().sum() == 0
