"""
Author : Wonjun Kim
e-mail : wonjun.kim@seculayer.com
Powered by Seculayer © 2025 AI Team, R&D Center.
"""
from __future__ import annotations

from abc import ABC

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance

from src.common.Constant import Constants
from src.common.LoggerManager import LoggerManager


class BaseService(ABC):
    def __init__(self, client: AsyncQdrantClient):
        self.logger = LoggerManager().get()
        self.constants = Constants()
        self.client = client
        self.batch_size = self.constants.EMBEDDER_BATCH_SIZE

    async def clean_resource(self) -> None:
        """ Clean up resources to prevent memory leaks. """
        try:
            if self.client is not None:
                await self.client.close()
                self.logger.info('Qdrant client connection closed')
        except Exception as e:
            self.logger.error(f"Error closing Qdrant client: {str(e)}")

    @staticmethod
    def _get_distance(distance_str: str) -> Distance:
        """ Convert string representation of distance to Distance enum. """
        distance_map = {
            'Cosine': Distance.COSINE,
            'cosine': Distance.COSINE,
            'Euclidean': Distance.EUCLID,
            'euclidean': Distance.EUCLID,
            'Dot': Distance.DOT,
            'dot': Distance.DOT,
        }
        return distance_map.get(distance_str, Distance.COSINE)
