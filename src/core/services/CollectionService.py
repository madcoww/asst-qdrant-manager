"""
Author : Wonjun Kim
e-mail : wonjun.kim@seculayer.com
Powered by Seculayer © 2025 AI Team, R&D Center.
"""
from __future__ import annotations

from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import PointStruct
from qdrant_client.models import VectorParams

from src.core.services.BaseService import BaseService


class CollectionService(BaseService):
    def __init__(self, client: AsyncQdrantClient):
        super().__init__(client)

    async def create_collection(self, collection_name: str, distance: str, dim: int) -> None:
        """
        Create a Qdrant collection with specified parameters.

        Args:
            collection_name: Name of the collection to create
            distance: Distance metric (Cosine, Euclidean, Dot)
            dim: Vector dimension size
        """
        coll_params = dict(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=dim,
                distance=self._get_distance(distance),
            ),
        )
        try:
            await self.client.get_collection(collection_name)
            self.logger.info(f"Collection {collection_name} already exists. Deleting it.")
            exists = True
        except UnexpectedResponse:
            self.logger.info(f"Collection {collection_name} does not exist. Creating new one.")
            exists = False

        if exists:
            await self.client.delete_collection(collection_name)
            self.logger.info(f"Deleted existing collection: {collection_name}")

        try:
            await self.client.create_collection(**coll_params)
            self.logger.info(f"Created collection: {collection_name} with dimension {dim}")
        except UnexpectedResponse as e:
            self.logger.error(f"Failed to create collection {collection_name}: {str(e)}")
            raise

    async def build_collection(
            self,
            collection_name: str,
            distance: str,
            dim: int,
            points: list[PointStruct],
    ) -> None:
        """
        Build Qdrant collection: create and upload points in batches.

        Args:
            collection_name: Name of the collection to create
            distance: Distance metric (Cosine, Euclidean, Dot)
            dim: Vector dimension size
            points: List of PointStruct objects ready for insertion
        """
        await self.create_collection(collection_name, distance, dim)
        await self._upsert_points(collection_name, points)

    async def add_points(
            self,
            collection_name: str,
            points: list[PointStruct],
    ) -> None:
        """
        Add points to an existing Qdrant collection.

        Args:
            collection_name: Name of the collection to add points to
            points: List of PointStruct objects ready for insertion
        """
        try:
            await self.client.get_collection(collection_name)
            self.logger.info(f"Collection {collection_name} exists. Adding points.")

        except UnexpectedResponse:
            self.logger.error(f"Collection {collection_name} does not exist")
            raise ValueError(f"Collection {collection_name} does not exist")

        await self._upsert_points(collection_name, points)

    async def collection_exists(self, collection_name: str) -> bool:
        """Check if a Qdrant collection exists."""
        try:
            await self.client.collection_exists(collection_name)
            self.logger.info(f"Collection {collection_name} exists")
            return True
        except UnexpectedResponse:
            self.logger.info(f"Collection {collection_name} does not exist")
            return False

    async def delete_collection(self, collection_name: str) -> None:
        """Delete a Qdrant collection."""
        try:
            await self.client.delete_collection(collection_name)
            self.logger.info(f"Deleted collection: {collection_name}")
        except UnexpectedResponse as e:
            self.logger.error(f"Failed to delete collection {collection_name}: {str(e)}")
            raise

    async def collection_list(self) -> list[str]:
        """List all Qdrant collections."""
        try:
            collections = await self.client.get_collections()
            coll_names = [coll.name for coll in collections.collections]
            self.logger.info(f"Retrieved {len(coll_names)} collections")
            return coll_names
        except UnexpectedResponse as e:
            self.logger.error(f"Failed to list collections: {str(e)}")
            raise

    async def get_collection_info(self, collection_name: str) -> dict[str, Any]:
        """
        Get detailed information about a collection.

        Args:
            collection_name: Name of the collection

        Returns:
            Dictionary containing collection info (vectors_count, status, etc.)
        """
        try:
            collection_info = await self.client.get_collection(collection_name)

            info_dict = {
                'name': collection_name,
                'vectors_count': collection_info.vectors_count,
                'points_count': collection_info.points_count,
                'status': collection_info.status,
                'optimizer_status': collection_info.optimizer_status,
                'indexed_vectors_count': getattr(collection_info, 'indexed_vectors_count', None),
            }

            self.logger.info(f"Retrieved collection info for '{collection_name}': {info_dict['points_count']} points")
            return info_dict

        except UnexpectedResponse as e:
            self.logger.error(f"Failed to get collection info for {collection_name}: {str(e)}")
            raise

    async def _upsert_points(
            self,
            collection_name: str,
            points: list[PointStruct],
    ) -> None:
        """
        Upsert points into a Qdrant collection in batches.

        Args:
            collection_name: Name of the collection
            points: List of PointStruct objects ready for insertion
        """
        total_points = len(points)
        self.logger.info(f"Upserting {total_points} points in batches of {self.batch_size}")

        try:
            for i in range(0, total_points, self.batch_size):
                batch = points[i:i + self.batch_size]
                await self.client.upsert(
                    collection_name=collection_name,
                    points=batch,
                )
                self.logger.info(
                    f"Upserted batch {i // self.batch_size + 1}: "
                    f"{i + len(batch)}/{total_points} points",
                )

            self.logger.info(
                f"Successfully upserted all {total_points} points "
                f"into collection {collection_name}",
            )
        except UnexpectedResponse as e:
            self.logger.error(
                f"Failed to upsert points into collection {collection_name}: {str(e)}",
            )
            raise
