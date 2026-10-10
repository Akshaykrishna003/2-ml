import ast
import tokenize
from io import StringIO
from typing import Any, Dict, List, Tuple


MAX_SOURCE_CHARS = 2_000_000


class Preprocessor:
    """Normalize Python source and preserve source spans for evidence extraction."""

    def __init__(self):
        self.id_map: Dict[str, str] = {}
        self.id_counter = 0
        self._reserved_ids = set()

    def _get_normalized_id(self, original_id: str) -> str:
        if original_id not in self.id_map:
            while True:
                normalized = f"var_{self.id_counter}"
                self.id_counter += 1
                if normalized not in self._reserved_ids and normalized not in self.id_map.values():
                    break
            self.id_map[original_id] = normalized
        return self.id_map[original_id]

    def _line_offsets(self, source: str) -> List[int]:
        offsets = [0]
        for line in source.splitlines(keepends=True):
            offsets.append(offsets[-1] + len(line))
        return offsets

    def _token_offset(self, position: Tuple[int, int], offsets: List[int]) -> int:
        line, col = position
        return offsets[line - 1] + col

    def _ast_offset(self, position: Tuple[int, int], source_lines: List[str], offsets: List[int]) -> int:
        line, byte_col = position
        prefix = source_lines[line - 1].encode("utf-8")[:byte_col].decode("utf-8")
        return offsets[line - 1] + len(prefix)

    def _collect_docstring_spans(self, source: str) -> List[Tuple[int, int]]:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []

        offsets = self._line_offsets(source)
        source_lines = source.splitlines(keepends=True)
        spans: List[Tuple[int, int]] = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if not getattr(node, "body", None):
                continue
            first_stmt = node.body[0]
            if isinstance(first_stmt, ast.Expr) and isinstance(first_stmt.value, ast.Constant) and isinstance(first_stmt.value.value, str):
                start = self._ast_offset((first_stmt.lineno, first_stmt.col_offset), source_lines, offsets)
                end = self._ast_offset((first_stmt.end_lineno, first_stmt.end_col_offset), source_lines, offsets)
                spans.append((start, end))
        return sorted(spans)

    def clean_code(self, source: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Strip comments and docstrings while preserving a span log for evidence."""
        if len(source) > MAX_SOURCE_CHARS:
            raise ValueError("source exceeds the 2,000,000-character limit")
        if not source:
            return "", []

        removed_spans: List[Dict[str, Any]] = []
        offsets = self._line_offsets(source)

        try:
            tree = ast.parse(source)
        except SyntaxError:
            tree = None

        if tree is not None:
            for start, end in self._collect_docstring_spans(source):
                removed_spans.append({
                    "type": "docstring",
                    "start": start,
                    "end": end,
                    "text": source[start:end],
                })

        reader = StringIO(source).readline
        try:
            for tok in tokenize.generate_tokens(reader):
                if tok.type == tokenize.COMMENT:
                    removed_spans.append({
                        "type": "comment",
                        "start": self._token_offset(tok.start, offsets),
                        "end": self._token_offset(tok.end, offsets),
                        "text": tok.string,
                    })
        except (tokenize.TokenError, IndentationError):
            pass

        if not removed_spans:
            return source, []

        combined = []
        last_end = 0
        for span in sorted(removed_spans, key=lambda item: item["start"]):
            start = span["start"]
            end = span["end"]
            if start < last_end:
                continue
            combined.append(source[last_end:start])
            last_end = max(last_end, end)
        combined.append(source[last_end:])
        return "".join(combined), removed_spans

    def normalize_identifiers(self, source: str) -> str:
        """Replace all identifiers with deterministic generic tokens."""
        if len(source) > MAX_SOURCE_CHARS:
            raise ValueError("source exceeds the 2,000,000-character limit")
        self.id_map = {}
        self.id_counter = 0
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            raise ValueError(f"Syntax error during normalization: {exc}") from exc

        self._reserved_ids = {
            node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
        }
        self._reserved_ids.update(
            node.arg for node in ast.walk(tree) if isinstance(node, ast.keyword) and node.arg is not None
        )
        renames: Dict[str, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                renames.setdefault(node.id, self._get_normalized_id(node.id))
            elif isinstance(node, ast.arg):
                renames.setdefault(node.arg, self._get_normalized_id(node.arg))
            elif isinstance(node, ast.FunctionDef):
                renames.setdefault(node.name, self._get_normalized_id(node.name))
            elif isinstance(node, ast.AsyncFunctionDef):
                renames.setdefault(node.name, self._get_normalized_id(node.name))
            elif isinstance(node, ast.ClassDef):
                renames.setdefault(node.name, self._get_normalized_id(node.name))

        source_lines = source.splitlines(keepends=True)
        offsets = self._line_offsets(source)
        replacements: List[Tuple[int, int, str]] = []
        tokens = list(tokenize.generate_tokens(StringIO(source).readline))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Name, ast.arg)):
                identifier = node.id if isinstance(node, ast.Name) else node.arg
                if identifier in renames:
                    start = self._ast_offset((node.lineno, node.col_offset), source_lines, offsets)
                    end = self._ast_offset((node.end_lineno, node.end_col_offset), source_lines, offsets)
                    replacements.append((start, end, renames[identifier]))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                keyword = "class" if isinstance(node, ast.ClassDef) else "def"
                row_tokens = [
                    token for token in tokens
                    if token.start[0] == node.lineno and token.type == tokenize.NAME
                ]
                keyword_index = next(
                    (index for index, token in enumerate(row_tokens) if token.string == keyword),
                    None,
                )
                if keyword_index is None:
                    continue
                name_token = next(
                    (token for token in row_tokens[keyword_index + 1:] if token.string == node.name),
                    None,
                )
                if name_token is not None:
                    start = self._token_offset(name_token.start, offsets)
                    end = self._token_offset(name_token.end, offsets)
                    replacements.append((start, end, renames[node.name]))

        result = source
        for start, end, replacement in sorted(replacements, reverse=True):
            result = result[:start] + replacement + result[end:]
        return result

    def validate_input(self, source: str) -> bool:
        if not source or len(source) > MAX_SOURCE_CHARS or not source.strip():
            return False
        try:
            ast.parse(source)
            return True
        except (SyntaxError, RecursionError):
            return False
