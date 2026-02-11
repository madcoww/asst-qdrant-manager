"""
Author : Wonjun Kim
e-mail : wonjun.kim@seculayer.com
Powered by Seculayer © 2025 AI Team, R&D Center.
"""
from __future__ import annotations

import httpx
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse

from src.core.services.BaseService import BaseService


class SnapshotService(BaseService):
    def __init__(self, client: AsyncQdrantClient):
        super().__init__(client)

    async def create_snapshot(self, collection_name: str) -> bool:
        """Create a snapshot for the specified collection."""
        try:
            result = await self.client.create_snapshot(collection_name=collection_name)
            self.logger.info(f"Snapshot created for collection: {collection_name}, result: {result}")
            return True
        except UnexpectedResponse as e:
            if e.status_code == 404:
                self.logger.error(f"Collection '{collection_name}' not found")
                raise ValueError(f"Collection '{collection_name}' not found")
            self.logger.error(f"Failed to create snapshot for collection {collection_name}: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to create snapshot: {str(e)}")
        except Exception as e:
            self.logger.error(f"Failed to create snapshot for collection {collection_name}: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to create snapshot: {str(e)}")

    async def delete_snapshot(self, collection_name: str, snapshot_name: str) -> bool:
        """Delete a snapshot for the specified collection."""
        try:
            await self.client.delete_snapshot(collection_name=collection_name, snapshot_name=snapshot_name)
            self.logger.info(f"Snapshot {snapshot_name} deleted for collection: {collection_name}")
            return True
        except UnexpectedResponse as e:
            if e.status_code == 404:
                if "doesn't exist" in str(e).lower() or 'not found' in str(e).lower():
                    self.logger.error(f"Collection or snapshot not found: {collection_name}/{snapshot_name}")
                    raise ValueError(f"Collection '{collection_name}' or snapshot '{snapshot_name}' not found")
            self.logger.error(
                f"Failed to delete snapshot {snapshot_name} for collection {collection_name}: {str(e)}", exc_info=True,
            )
            raise RuntimeError(f"Failed to delete snapshot: {str(e)}")
        except Exception as e:
            self.logger.error(
                f"Failed to delete snapshot {snapshot_name} for collection {collection_name}: {str(e)}", exc_info=True,
            )
            raise RuntimeError(f"Failed to delete snapshot: {str(e)}")

    async def list_snapshots(self, collection_name: str) -> list[str]:
        """List all snapshots for the specified collection."""
        try:
            snapshots = await self.client.list_snapshots(collection_name=collection_name)
            snapshot_names = [snapshot.name for snapshot in snapshots]
            self.logger.info(f"Retrieved {len(snapshot_names)} snapshots for collection: {collection_name}")
            return snapshot_names
        except UnexpectedResponse as e:
            if e.status_code == 404:
                self.logger.error(f"Collection '{collection_name}' not found")
                raise ValueError(f"Collection '{collection_name}' not found")
            self.logger.error(f"Failed to list snapshots for collection {collection_name}: {str(e)}")
            raise RuntimeError(f"Failed to list snapshots: {str(e)}")
        except Exception as e:
            self.logger.error(f"Failed to list snapshots for collection {collection_name}: {str(e)}")
            raise RuntimeError(f"Failed to list snapshots: {str(e)}")

    async def recover_snapshot_volume(self, collection_name: str, snapshot_name: str) -> bool:
        """
        Recover a collection from a snapshot stored in shared volume.
        """
        try:
            snapshot_path = self.get_snapshot_volume_path(collection_name, snapshot_name)
            await self.client.recover_snapshot(
                collection_name=collection_name,
                location=snapshot_path,
            )
            self.logger.info(f"Snapshot {snapshot_name} restored for collection: {collection_name}")
            return True
        except UnexpectedResponse as e:
            error_msg = str(e).lower()
            if e.status_code == 404 or (e.status_code == 400 and 'does not exist' in error_msg):
                self.logger.error(f"Snapshot '{snapshot_name}' not found for collection '{collection_name}'")
                raise ValueError(f"Snapshot '{snapshot_name}' not found in collection '{collection_name}'")
            self.logger.error(
                f"Failed to restore snapshot {snapshot_name} for collection {collection_name}: {str(e)}", exc_info=True,
            )
            raise RuntimeError(f"Failed to restore snapshot: {str(e)}")
        except Exception as e:
            self.logger.error(
                f"Failed to restore snapshot {snapshot_name} for collection {collection_name}: {str(e)}", exc_info=True,
            )
            raise RuntimeError(f"Failed to restore snapshot: {str(e)}")

    async def recover_snapshot_file(
        self,
        collection_name: str,
        snapshot_content: bytes,
    ) -> bool:
        """
        Upload snapshot file directly to Qdrant and recover collection.

        Uses Qdrant's snapshot upload API (POST /collections/{name}/snapshots/upload)
        to directly upload and restore from snapshot file without requiring shared storage.

        Args:
            collection_name: Name of the collection to restore
            snapshot_content: Snapshot file content as bytes

        Returns:
            True if successful, False otherwise
        """
        try:
            # Qdrant snapshot upload endpoint (공식 문서 참조)
            upload_url = (
                f"http://{self.constants.QDRANT_SVC}:{self.constants.QDRANT_PORT}"
                f"/collections/{collection_name}/snapshots/upload"
            )

            self.logger.info(f"Uploading snapshot to Qdrant: {upload_url}")

            async with httpx.AsyncClient() as client:
                files = {'snapshot': ('snapshot.snapshot', snapshot_content, 'application/octet-stream')}

                response = await client.post(
                    upload_url,
                    files=files,
                    params={'priority': 'snapshot'},  # 공식 문서 권장
                    timeout=300.0,
                )
                response.raise_for_status()

            self.logger.info(f"Snapshot uploaded and collection '{collection_name}' recovered successfully")
            return True

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                self.logger.error('Snapshot upload endpoint not found or invalid collection')
                raise ValueError('Invalid snapshot or collection configuration')
            self.logger.error(f"HTTP error during snapshot upload: {str(e)}")
            raise RuntimeError(f"Snapshot upload failed: {str(e)}")
        except Exception as e:
            self.logger.error(f"Failed to upload and recover snapshot for collection {collection_name}: {str(e)}")
            raise RuntimeError(f"Snapshot upload failed: {str(e)}")

    def get_snapshot_url(self, collection_name: str, snapshot_name: str) -> str:
        """Construct the snapshot URL for the specified collection and snapshot."""
        base_url = f"http://{self.constants.QDRANT_SVC}:{self.constants.QDRANT_PORT}"
        return f"{base_url}/collections/{collection_name}/snapshots/{snapshot_name}"

    def get_full_snapshot_url(self, snapshot_name: str) -> str:
        """Construct the full snapshot URL for the specified snapshot."""
        base_url = f"http://{self.constants.QDRANT_SVC}:{self.constants.QDRANT_PORT}"
        return f"{base_url}/snapshots/{snapshot_name}"

    def get_snapshot_volume_path(self, collection_name: str, snapshot_name: str) -> str:
        """
        Construct the snapshot path for the specified collection and snapshot.
        Returns file:// URI for local snapshot recovery.
        """
        return f"file://{self.constants.QDRANT_SNAPSHOT_VOLUME}/{collection_name}/{snapshot_name}"

    async def create_snapshot_full(self):
        """Create snapshots for all collections."""
        try:
            await self.client.create_full_snapshot()
            self.logger.info('Snapshots created for all collections')
            return True
        except Exception as e:
            self.logger.error(f"Failed to create snapshots for all collections: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to create snapshots for all collections: {str(e)}")

    async def delete_snapshot_full(self, snapshot_name: str) -> bool:
        """Delete a snapshot for all collections."""
        try:
            await self.client.delete_full_snapshot(snapshot_name=snapshot_name)
            self.logger.info(f"Snapshot {snapshot_name} deleted for all collections")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete snapshot {snapshot_name} for all collections: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to delete snapshot for all collections: {str(e)}")

    async def list_snapshots_full(self) -> list[str]:
        """List all snapshots for all collections."""
        try:
            snapshots = await self.client.list_full_snapshots()
            snapshot_names = [snapshot.name for snapshot in snapshots]
            self.logger.info(f"Retrieved {len(snapshot_names)} snapshots for all collections")
            return snapshot_names
        except Exception as e:
            self.logger.error(f"Failed to list snapshots for all collections: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to list snapshots for all collections: {str(e)}")
