from ps23_engine.core.baseline import TokenBaseline

def test_token_baseline_identical():
    baseline = TokenBaseline()
    code = "def hello(): print('world')"
    assert baseline.compute_similarity(code, code) == 1.0

def test_token_baseline_different():
    baseline = TokenBaseline()
    code1 = "def hello(): print('world')"
    code2 = "def goodbye(): print('mars')"
    similarity = baseline.compute_similarity(code1, code2)
    assert 0.0 <= similarity < 1.0

def test_token_baseline_empty():
    baseline = TokenBaseline()
    assert baseline.compute_similarity("", "print(1)") == 0.0


def test_tokenization_ignores_comments_and_whitespace_but_keeps_strings():
    baseline = TokenBaseline()
    code = "value = 'value'  # identifier in comment\nprint(value)"
    changed = "value='value'\n# another comment\nprint(value)"

    assert baseline.tokenize(code) == baseline.tokenize(changed)
    assert baseline.compute_similarity(code, changed) == 1.0


def test_token_baseline_detects_operator_changes():
    baseline = TokenBaseline()
    assert baseline.compute_similarity("return value < limit", "return value > limit") < 1.0


def test_token_baseline_rejects_oversized_input():
    import pytest

    with pytest.raises(ValueError, match="character limit"):
        TokenBaseline().tokenize("x" * 2_000_001)
