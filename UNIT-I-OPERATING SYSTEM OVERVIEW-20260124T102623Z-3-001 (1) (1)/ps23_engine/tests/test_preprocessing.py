import ast
import pytest
from ps23_engine.core.preprocessing import Preprocessor

def test_preprocessor_validation():
    p = Preprocessor()
    assert p.validate_input("print('hello')") == True
    assert p.validate_input("") == False
    assert p.validate_input("invalid syntax {") == False

def test_preprocessor_cleaning():
    p = Preprocessor()
    code = "x = 1 # This is a comment\nprint(x)"
    cleaned, spans = p.clean_code(code)
    assert "# This is a comment" not in cleaned
    assert len(spans) > 0
    assert spans[0]['type'] == 'comment'

def test_preprocessor_normalization():
    p = Preprocessor()
    code = "def calculate_sum(a, b):\n    result = a + b\n    return result"
    normalized = p.normalize_identifiers(code)
    # Check if original names are gone
    assert "calculate_sum" not in normalized
    assert "result" not in normalized
    # Check if generic tokens are present
    assert "var_" in normalized


def test_normalization_preserves_strings_comments_and_line_numbers():
    p = Preprocessor()
    source = (
        "# header\n"
        "def calculate(value):\n"
        "    label = 'calculate value'\n"
        "    # value stays in this comment\n"
        "    return value\n"
    )

    normalized = p.normalize_identifiers(source)

    assert "'calculate value'" in normalized
    assert "# value stays in this comment" in normalized
    assert len(normalized.splitlines()) == len(source.splitlines())
    assert ast.parse(normalized).body[0].lineno == 2
    assert ast.parse(normalized).body[0].body[-1].lineno == 5


def test_normalization_handles_nested_scopes_and_name_collisions():
    p = Preprocessor()
    source = (
        "def outer(value):\n"
        "    var_0 = value\n"
        "    def inner(value):\n"
        "        return var_0 + value\n"
        "    return inner(var_0)\n"
    )

    normalized = p.normalize_identifiers(source)
    tree = ast.parse(normalized)

    assert "outer" not in normalized
    assert "inner" not in normalized
    assert "var_0" in normalized
    assert len({node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}) >= 2
    assert len({node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}) == 2
    assert len(normalized.splitlines()) == len(source.splitlines())


def test_clean_code_preserves_unicode_and_docstring_line_locations():
    p = Preprocessor()
    source = (
        "title = 'café'  # commentaire\n"
        "def f():\n"
        "    \"\"\"Résumé.\"\"\"\n"
        "    return title\n"
    )

    cleaned, spans = p.clean_code(source)

    assert "café" in cleaned
    assert "Résumé." not in cleaned
    assert "commentaire" not in cleaned
    assert len(cleaned.splitlines()) == len(source.splitlines())
    assert {span["type"] for span in spans} == {"comment", "docstring"}
    for span in spans:
        assert source[span["start"]:span["end"]] == span["text"]


def test_normalization_rejects_invalid_syntax():
    with pytest.raises(ValueError, match="Syntax error"):
        Preprocessor().normalize_identifiers("def broken(:")


def test_empty_input_cleaning_and_validation():
    p = Preprocessor()
    assert p.clean_code("") == ("", [])
    assert p.validate_input("") is False


def test_normalization_preserves_identifiers_inside_strings_comments_and_docstrings():
    source = (
        "def calculate(value):\n"
        "    \"\"\"calculate value without rewriting this docstring.\"\"\"\n"
        "    text = 'calculate(value)'\n"
        "    # calculate(value) is only a comment\n"
        "    return value\n"
    )

    normalized = Preprocessor().normalize_identifiers(source)

    assert '"""calculate value without rewriting this docstring."""' in normalized
    assert "'calculate(value)'" in normalized
    assert "# calculate(value) is only a comment" in normalized
    assert len(normalized.splitlines()) == len(source.splitlines())
    assert ast.parse(normalized).body[0].body[-1].lineno == 5


def test_normalization_preserves_line_locations_with_unicode_and_crlf():
    source = "# café\r\ndef calculate(value):\r\n    return value\r\n"
    normalized = Preprocessor().normalize_identifiers(source)
    function = ast.parse(normalized).body[0]

    assert function.lineno == 2
    assert function.body[0].lineno == 3
    assert normalized.count("\r\n") == source.count("\r\n")


def test_clean_code_keeps_line_locations_after_nested_docstrings_and_comments():
    source = (
        "def outer():\n"
        "    \"\"\"outer docs\"\"\"\n"
        "    def inner():\n"
        "        \"\"\"inner docs\"\"\"\n"
        "        return 1  # inline\n"
        "    return inner()\n"
    )
    cleaned, spans = Preprocessor().clean_code(source)
    tree = ast.parse(cleaned)
    inner = tree.body[0].body[0]

    assert {span["type"] for span in spans} == {"docstring", "comment"}
    assert inner.lineno == 3
    assert inner.body[-1].lineno == 5


def test_normalization_rejects_deeply_nested_syntax_without_recursion_failure():
    source = "value = " + "(" * 10_000 + "1" + ")" * 10_000
    with pytest.raises(ValueError, match="Syntax error"):
        Preprocessor().normalize_identifiers(source)
