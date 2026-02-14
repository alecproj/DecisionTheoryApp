from app.algorithms.example.schema import validate_input
from app.algorithms.example.algo import run
from app.reporting.reporter import MarkdownReporter

def test_example_algorithm_report():
    typed = validate_input({"a": 1, "b": 4})
    rep = MarkdownReporter()
    run(typed, rep)
    md = rep.get_markdown()
    assert "Example algorithm" in md
    assert "a+b" in md
