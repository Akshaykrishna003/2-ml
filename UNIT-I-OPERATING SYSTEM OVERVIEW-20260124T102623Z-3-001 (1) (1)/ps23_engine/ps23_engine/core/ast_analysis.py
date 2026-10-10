import ast
from collections import Counter
from functools import lru_cache
from typing import Dict


MAX_SOURCE_CHARS = 2_000_000
_AST_CACHE_SOURCE_CHARS = 65_536


def _compute_ast_features(source: str):
    if source is None:
        return (), ""
    if len(source) > MAX_SOURCE_CHARS:
        raise ValueError("source exceeds the 2,000,000-character limit")
    if not source.strip():
        return (), ""
    try:
        tree = ast.parse(source)
    except (SyntaxError, RecursionError):
        return (), ""

    distribution = tuple(sorted(Counter(type(node).__name__ for node in ast.walk(tree)).items()))

    def dump_structure(node):
        if not isinstance(node, ast.AST):
            return ""
        if isinstance(node, ast.Constant):
            return "Constant"
        if isinstance(node, ast.Name):
            return "Name"
        if isinstance(node, ast.arg):
            return "arg"
        node_type = type(node).__name__
        children = []
        for field, value in ast.iter_fields(node):
            if field in {"name", "id", "arg", "attr"}:
                continue
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        children.append(dump_structure(item))
            elif isinstance(value, ast.AST):
                children.append(dump_structure(value))
        return f"{node_type}({','.join(children)})"

    return distribution, dump_structure(tree)


@lru_cache(maxsize=1024)
def _cached_ast_features(source: str):
    return _compute_ast_features(source)


class ASTAnalyzer:
    """Analyze Python ASTs for shape-based similarity and evidence extraction."""

    def get_node_distribution(self, source: str) -> Dict[str, int]:
        distribution, _ = self._features(source)
        return dict(distribution)

    def get_structure_hash(self, source: str) -> str:
        _, structure = self._features(source)
        return structure

    def extract_features(self, source: str):
        """Parse once and return reusable node-count and structure features."""
        distribution, structure = self._features(source)
        return {"node_distribution": dict(distribution), "structure_hash": structure}

    def _features(self, source: str):
        if source is None:
            return (), ""
        if len(source) > MAX_SOURCE_CHARS:
            raise ValueError("source exceeds the 2,000,000-character limit")
        if len(source) <= _AST_CACHE_SOURCE_CHARS:
            return _cached_ast_features(source)
        return _compute_ast_features(source)

    def compute_structural_similarity(self, source1: str, source2: str) -> float:
        dist1 = self.get_node_distribution(source1)
        dist2 = self.get_node_distribution(source2)

        if not dist1 or not dist2:
            return 0.0

        all_nodes = sorted(set(dist1).union(dist2))
        v1 = [dist1.get(node, 0) for node in all_nodes]
        v2 = [dist2.get(node, 0) for node in all_nodes]

        dot_product = sum(a * b for a, b in zip(v1, v2))
        mag1 = sum(a * a for a in v1) ** 0.5
        mag2 = sum(b * b for b in v2) ** 0.5

        if mag1 == 0 or mag2 == 0:
            return 0.0
        return dot_product / (mag1 * mag2)
