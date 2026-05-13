from pathlib import Path

from plugins.grading.python.validate_run import validate_run_folder, RunValidationReport


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "run_smoke"


def test_validate_run_folder_passes_on_fixture():
    report = validate_run_folder(FIXTURE)
    assert isinstance(report, RunValidationReport)
    assert report.ok, report.errors


def test_validate_run_folder_reports_missing_universal_rubric(tmp_path):
    # Build a partial-fixture run missing the universal rubric.
    bad = tmp_path / "bad_run"
    (bad / "rubrics" / "fixture" / "Qfix01").mkdir(parents=True)
    (bad / "rubrics" / "fixture" / "Qfix01" / "rubric.yaml").write_text(
        (FIXTURE / "rubrics" / "fixture" / "Qfix01" / "rubric.yaml").read_text()
    )
    report = validate_run_folder(bad)
    assert not report.ok
    assert any("universal_rubric.yaml" in e for e in report.errors)
