import io
import tokenize
from functools import lru_cache
from typing import FrozenSet, List


MAX_SOURCE_CHARS = 2_000_000


_TOKEN_CACHE_SOURCE_CHARS = 65_536


def _tokenize_source(source: str):
    if len(source) > MAX_SOURCE_CHARS:
        raise ValueError("source exceeds the 2,000,000-character limit")
    ignored = {
        tokenize.COMMENT,
        tokenize.NL,
        tokenize.NEWLINE,
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.ENDMARKER,
    }
    tokens = []
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type not in ignored:
                tokens.append(token.string)
    except (tokenize.TokenError, IndentationError):
        pass
    return tuple(tokens)


@lru_cache(maxsize=1024)
def _cached_tokens(source: str):
    return _tokenize_source(source)


@lru_cache(maxsize=4096)
def _cached_ngrams(tokens: tuple, n_gram: int) -> FrozenSet[tuple]:
    if len(tokens) < n_gram:
        return frozenset()
    return frozenset(
        tuple(tokens[index : index + n_gram])
        for index in range(len(tokens) - n_gram + 1)
    )


class TokenBaseline:
    """Token-based similarity baseline using normalized n-gram overlap."""

    def __init__(self, n_gram: int = 3):
        if n_gram <= 0:
            raise ValueError("n_gram must be positive")
        self.n_gram = n_gram

    def _get_ngrams(self, tokens: List[str]) -> FrozenSet[tuple]:
        return _cached_ngrams(tuple(tokens), self.n_gram)

    def tokenize(self, source: str) -> List[str]:
        if len(source) <= _TOKEN_CACHE_SOURCE_CHARS:
            return list(_cached_tokens(source))
        return list(_tokenize_source(source))

    def compute_similarity(self, source1: str, source2: str) -> float:
        tokens1 = self.tokenize(source1)
        tokens2 = self.tokenize(source2)

        if not tokens1 or not tokens2:
            return 0.0

        ngrams1 = self._get_ngrams(tokens1)
        ngrams2 = self._get_ngrams(tokens2)

        if not ngrams1 or not ngrams2:
            return 0.0

        intersection = ngrams1.intersection(ngrams2)
        union = ngrams1.union(ngrams2)
        return len(intersection) / len(union)
