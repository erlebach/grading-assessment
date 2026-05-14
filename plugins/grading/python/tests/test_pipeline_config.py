from pathlib import Path

import yaml

PIPELINE = Path(__file__).resolve().parents[2] / "config" / "pipeline.yaml"


def test_pipeline_exists():
    assert PIPELINE.is_file()


def test_seeds_per_type_composition_sums_to_total():
    data = yaml.safe_load(PIPELINE.read_text())
    spt = data["seeds_per_type"]
    total = spt["default"]
    comp = spt["composition"]
    assert comp["from_user_curated"] + comp["from_source"] + comp["from_claude_knowledge"] == total


def test_score_bands_present_and_ordered():
    data = yaml.safe_load(PIPELINE.read_text())
    bands = data["score_bands"]
    for name in ("good", "less_good", "wrong"):
        lo, hi = bands[name]
        assert 0.0 <= lo < hi <= 1.0, name
    assert bands["wrong"][1] < bands["less_good"][0]
    assert bands["less_good"][1] < bands["good"][0]


def test_calibration_thresholds_present():
    data = yaml.safe_load(PIPELINE.read_text())
    c = data["calibration"]
    assert 0.0 < c["concept_vote_agreement_min"] <= 1.0
    assert 0.0 < c["score_band_satisfaction_min"] <= 1.0
    assert 0.0 < c["axis_discrimination_delta_min"] <= 1.0
    assert c["max_iterations"] >= 1


def test_parallelism_knobs_present():
    data = yaml.safe_load(PIPELINE.read_text())
    p = data["parallelism"]
    assert p["max_parallel_questions"] >= 1
    assert p["max_parallel_seeds"] >= 1


def test_marker_single_block_present():
    data = yaml.safe_load(PIPELINE.read_text())
    m = data["marker_single"]
    assert isinstance(m["ocr"], bool)
    assert isinstance(m["extract_images"], bool)


def test_profiles_block_has_smoke():
    data = yaml.safe_load(PIPELINE.read_text())
    profiles = data["profiles"]
    assert "smoke" in profiles
    # smoke dials count knobs down to 1
    assert profiles["smoke"]["seeds_per_type"]["default"] == 1
    gr = profiles["smoke"]["generate_rubric"]
    assert gr["good_count"] == 1
    assert gr["less_good_count"] == 1
    assert gr["wrong_count"] == 1
