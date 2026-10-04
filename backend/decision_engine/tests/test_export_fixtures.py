from backend.decision_engine import export_fixtures


def test_output_fixtures_match_the_pipeline():
    assert export_fixtures.main(["--check"]) == 0, "run: python -m backend.decision_engine.export_fixtures"
