import ast
import pytest
from ps23_engine.core.ast_analysis import ASTAnalyzer

def test_ast_node_distribution():
    analyzer = ASTAnalyzer()
    code = "def f(x): return x + 1"
    dist = analyzer.get_node_distribution(code)
    assert "FunctionDef" in dist
    assert "Return" in dist
    assert "BinOp" in dist

def test_ast_similarity_identical():
    analyzer = ASTAnalyzer()
    code = "def f(x): return x + 1"
    assert analyzer.compute_structural_similarity(code, code) == pytest.approx(1.0)

def test_ast_similarity_different():
    analyzer = ASTAnalyzer()
    code1 = "def f(x): return x + 1"
    code2 = "class C: pass"
    similarity = analyzer.compute_structural_similarity(code1, code2)
    assert 0.0 <= similarity < 1.0

def test_ast_syntax_error():
    analyzer = ASTAnalyzer()
    assert analyzer.get_node_distribution("invalid syntax {") == {}
    assert analyzer.compute_structural_similarity("invalid syntax {", "print(1)") == 0.0


def test_ast_detects_operator_changes_in_structure_and_distribution():
    analyzer = ASTAnalyzer()
    less_than = "def f(value): return value < 3"
    greater_than = "def f(value): return value > 3"

    assert analyzer.get_structure_hash(less_than) != analyzer.get_structure_hash(greater_than)
    assert analyzer.compute_structural_similarity(less_than, greater_than) < 1.0


def test_ast_empty_and_large_comment_only_inputs():
    analyzer = ASTAnalyzer()
    assert analyzer.get_node_distribution("") == {}
    assert analyzer.compute_structural_similarity("", "x = 1") == 0.0

    large_source = "# " + ("safe test data " * 100_000)
    assert analyzer.get_node_distribution(large_source) == {"Module": 1}


def test_ast_deep_nesting_fails_without_executing_input():
    analyzer = ASTAnalyzer()
    deeply_nested = "x = " + "(" * 10_000 + "1" + ")" * 10_000
    # The parser may reject nesting at its configured syntax limit, but must not
    # execute the input or leak a recursion failure from feature extraction.
    assert analyzer.get_node_distribution(deeply_nested) == {}


def test_ast_reports_source_location_after_normalization():
    from ps23_engine.core.preprocessing import Preprocessor

    source = "# header\n\ndef original(value):\n    return value > 1\n"
    normalized = Preprocessor().normalize_identifiers(source)
    function = ast.parse(normalized).body[0]

    assert function.lineno == 3
    assert function.body[0].lineno == 4


def test_ast_rejects_oversized_source():
    import pytest

    with pytest.raises(ValueError, match="character limit"):
        ASTAnalyzer().get_node_distribution("x = 1\n" * 400_000)
