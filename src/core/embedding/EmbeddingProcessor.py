"""
Author : Wonjun Kim
e-mail : wonjun.kim@seculayer.com
Powered by Seculayer © 2025 AI Team, R&D Center.
"""
from __future__ import annotations

import httpx

from src.common.Constant import Constants
from src.common.LoggerManager import LoggerManager


class EmbeddingProcessor:
    def __init__(self):
        self.embedding_url = f"http://{Constants.EMBEDDER_SVC}:{Constants.EMBEDDER_PORT}{Constants.EMBEDDER_ENDPOINT}"
        self.batch_size = Constants.EMBEDDER_BATCH_SIZE
        self.logger = LoggerManager().get()
        self.dim_cache: int | None = None

    async def batch_embed_texts(self, texts: list[str]) -> list[list[float]]:
        """텍스트 리스트를 배치 단위로 임베딩. 실패 시 0-벡터로 대체."""
        vectors: list[list[float]] = []
        dim = await self.get_dim()  # 임베딩 차원 확인

        async with httpx.AsyncClient() as client:
            for i in range(0, len(texts), self.batch_size):
                batch_texts = texts[i:i+self.batch_size]
                try:
                    response = await client.post(
                        self.embedding_url,
                        json={'texts': batch_texts},
                        timeout=120.0,
                    )
                    response.raise_for_status()
                    batch_vectors = response.json().get('vectors', [])
                    processed = i + len(batch_texts)
                    self.logger.info(
                        f"Embedded batch {i // self.batch_size + 1}: processed {processed}/{len(texts)} texts",
                    )

                    # 벡터 수 불일치 시 오류 발생
                    if len(batch_vectors) != len(batch_texts):
                        raise RuntimeError(f"Embedding failed: expected {len(batch_texts)} vectors")

                except httpx.HTTPError as e:
                    self.logger.error(f"Embedding request failed for batch {i // self.batch_size + 1}: {str(e)}")
                    batch_vectors = [[0.0]*dim for _ in batch_texts]

                vectors.extend(batch_vectors)

        return vectors

    async def fetch_dim(self) -> int:
        """임베딩 차원을 임베더 서비스에 테스트 요청을 보내 확인."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.embedding_url,
                    json={'texts': ['test']},
                    timeout=30.0,
                )
                response.raise_for_status()
                vectors = response.json().get('vectors')

                if not vectors or not isinstance(vectors, list) or not vectors[0]:
                    raise ValueError("Invalid response: missing or empty 'vectors' field")

                dim = len(vectors[0])
                self.dim_cache = dim
                self.logger.info(f"Embedding dimension detected: {dim}")
                return dim

        except Exception as e:
            self.logger.error(f"Failed to fetch embedding dimension: {str(e)}")
            raise RuntimeError(f"Failed to fetch embedding dimension: {str(e)}") from e

    async def get_dim(self) -> int:
        """캐시된 차원 반환, 없으면 fetch_dim() 실행"""
        if self.dim_cache is not None:
            return self.dim_cache

        self.logger.info('Embedding dimension not cached — fetching from embedder...')
        return await self.fetch_dim()
