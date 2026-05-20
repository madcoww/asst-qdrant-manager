"""
Author : Wonjun Kim
e-mail : wonjun.kim@seculayer.com
Powered by Seculayer © 2025 AI Team, R&D Center.
"""
from __future__ import annotations

from openai import AsyncOpenAI

from src.common.Constant import Constants
from src.common.LoggerManager import LoggerManager


class OpenAIEmbeddingProcessor:
    def __init__(self, api_key: str = 'dummy'):
        base_url = f"http://{Constants.EMBEDDER_SVC}:{Constants.EMBEDDER_PORT}/{Constants.EMBEDDER_ENDPOINT}"
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = Constants.EMBEDDER_MODEL
        self.batch_size = Constants.EMBEDDER_BATCH_SIZE
        self.logger = LoggerManager().get()
        self.dim_cache: int | None = None

    async def batch_embed_texts(self, texts: list[str]) -> list[list[float]]:
        """텍스트 리스트를 배치 단위로 임베딩. 실패 시 0-벡터로 대체."""
        vectors: list[list[float]] = []
        dim = await self.get_dim()

        for i in range(0, len(texts), self.batch_size):
            batch_texts = texts[i: i + self.batch_size]
            try:
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=batch_texts,
                )
                batch_vectors = [item.embedding for item in response.data]
                processed = i + len(batch_texts)
                self.logger.info(
                    f"Embedded batch {i // self.batch_size + 1}: processed {processed}/{len(texts)} texts",
                )

                if len(batch_vectors) != len(batch_texts):
                    raise RuntimeError(f"Embedding failed: expected {len(batch_texts)} vectors")

            except Exception as e:
                self.logger.error(f"Embedding request failed for batch {i // self.batch_size + 1}: {str(e)}")
                batch_vectors = [[0.0] * dim for _ in batch_texts]

            vectors.extend(batch_vectors)

        return vectors

    async def fetch_dim(self) -> int:
        """임베딩 차원을 테스트 요청으로 확인."""
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=['test'],
            )

            if not response.data or not response.data[0].embedding:
                raise ValueError('Invalid response: missing or empty embedding')

            dim = len(response.data[0].embedding)
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
