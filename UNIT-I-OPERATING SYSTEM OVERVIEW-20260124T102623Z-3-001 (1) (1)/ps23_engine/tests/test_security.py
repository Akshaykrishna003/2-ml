import json

import pytest

from benchmarks.prepare_dataset import write_dataset
from ps23_engine.core.ast_analysis import ASTAnalyzer
from ps23_engine.core.baseline import TokenBaseline
from ps23_engine.core.preprocessing import Preprocessor


def test_source_analysis_does_not_execute_submission(tmp_path):
    marker = tmp_path / "execution-marker"
    source = "open({!r}, 'w').write('executed')".format(str(marker))

    ASTAnalyzer().get_node_distribution(source)
    Preprocessor().normalize_identifiers(source)
    TokenBaseline().tokenize(source)

    assert not marker.exists()


def test_malformed_and_deeply_nested_input_fail_closed():
    analyzer = ASTAnalyzer()
    assert analyzer.get_node_distribution("def invalid(:") == {}
    assert analyzer.compute_structural_similarity("def invalid(:", "x = 1") == 0.0
    assert analyzer.get_node_distribution("x = " + "(" * 10_000 + "1" + ")" * 10_000) == {}
    assert Preprocessor().validate_input("x = " + "(" * 10_000 + "1" + ")" * 10_000) is False


def test_oversized_text_is_rejected_by_all_source_processors():
    source = "x = 1\n" * 400_001

    with pytest.raises(ValueError, match="character limit"):
        ASTAnalyzer().get_node_distribution(source)
    with pytest.raises(ValueError, match="character limit"):
        Preprocessor().clean_code(source)
    with pytest.raises(ValueError, match="character limit"):
        Preprocessor().normalize_identifiers(source)
    with pytest.raises(ValueError, match="character limit"):
        TokenBaseline().tokenize(source)
    assert Preprocessor().validate_input(source) is False


def test_dataset_writer_does_not_hide_invalid_output_path(tmp_path):
    with pytest.raises((IsADirectoryError, PermissionError)):
        write_dataset(tmp_path)


def test_dataset_writer_emits_jsonl_without_executable_serialization(tmp_path):
    output = tmp_path / "dataset.jsonl"
    record_count = write_dataset(output)
    records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]

    assert record_count == len(records)
    assert records
    assert all(record["dataset"] == "PS-23 synthetic controlled corpus v1" for record in records)
