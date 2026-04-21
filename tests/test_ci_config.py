from pathlib import Path


def test_ci_workflow_runs_lint_typecheck_and_tests_for_prs_and_main() -> None:
    workflow = Path(".github/workflows/ci.yml")

    assert workflow.exists(), "Expected GitHub Actions workflow at .github/workflows/ci.yml"

    content = workflow.read_text(encoding="utf-8")

    assert "pull_request:" in content
    assert "push:" in content
    assert "main" in content
    assert "uv sync --extra dev" in content
    assert "uv run ruff check ." in content
    assert "uv run pyright" in content
    assert "uv run pytest -q" in content
