"""TF-IDF vector indexing and cosine search, backed by FAISS when available."""

from __future__ import annotations

import itertools
import logging
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger(__name__)

try:
    import faiss  # type: ignore[import-not-found]
except ImportError:  # FAISS wheels are not available on every supported platform.
    faiss = None
    logger.warning("faiss-cpu is unavailable; using the NumPy cosine-search fallback.")


class DrugInteractionSearch:
    """Search verified interaction records using normalized TF-IDF cosine similarity."""

    def __init__(self, interactions: list[dict[str, Any]]) -> None:
        if not interactions:
            raise ValueError("Cannot build a search index without interaction records.")
        self.interactions = interactions
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
        documents = [self._document(row) for row in interactions]
        self.matrix = self.vectorizer.fit_transform(documents).astype(np.float32)
        self.index = None
        if faiss is not None:
            dense = np.ascontiguousarray(self.matrix.toarray(), dtype=np.float32)
            faiss.normalize_L2(dense)
            self.index = faiss.IndexFlatIP(dense.shape[1])
            self.index.add(dense)

    @staticmethod
    def _document(row: dict[str, Any]) -> str:
        return " ".join(
            str(row.get(field, ""))
            for field in (
                "drug1",
                "drug2",
                "severity",
                "mechanism",
                "what_happens",
                "why_harmful",
                "symptoms",
                "precautions",
            )
        )

    @staticmethod
    def _pair_key(drug1: str, drug2: str) -> frozenset[str]:
        return frozenset((drug1.strip().casefold(), drug2.strip().casefold()))

    def search(self, medications: list[str]) -> list[dict[str, Any]]:
        """Return verified selected pairs, ordered by semantic cosine relevance."""
        selected = list(dict.fromkeys(name.strip() for name in medications if name.strip()))
        if len(selected) < 2:
            return []

        queries = [
            f"{drug1} interaction with {drug2} drug medicine safety"
            for drug1, drug2 in itertools.combinations(selected, 2)
        ]
        query_matrix = self.vectorizer.transform(queries).astype(np.float32)
        if self.index is not None:
            query_vectors = np.ascontiguousarray(query_matrix.toarray(), dtype=np.float32)
            faiss.normalize_L2(query_vectors)
            scores, indices = self.index.search(query_vectors, len(self.interactions))
        else:
            query_vectors = query_matrix.toarray()
            record_vectors = self.matrix.toarray()
            scores = query_vectors @ record_vectors.T
            indices = np.argsort(-scores, axis=1)
            scores = np.take_along_axis(scores, indices, axis=1)

        requested_pairs = {
            self._pair_key(first, second) for first, second in itertools.combinations(selected, 2)
        }
        best_scores: dict[int, float] = {}
        for query_scores, row_indices in zip(scores, indices):
            for score, row_index in zip(query_scores, row_indices):
                idx = int(row_index)
                record = self.interactions[idx]
                record_pair = self._pair_key(record["drug1"], record["drug2"])
                if record_pair in requested_pairs:
                    best_scores[idx] = max(best_scores.get(idx, -1.0), float(score))

        ordered = sorted(best_scores, key=best_scores.__getitem__, reverse=True)
        return [
            {**self.interactions[idx], "similarity": best_scores[idx]}
            for idx in ordered
        ]
