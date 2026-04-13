"""
Author : Wonjun Kim
e-mail : wonjun.kim@seculayer.com
Powered by Seculayer © 2025 AI Team, R&D Center.
"""
from __future__ import annotations

import os
import uuid
from typing import Any

import httpx
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct

from src.common.Constant import Constants
from src.common.LoggerManager import LoggerManager
from src.core.embedding.OpenAIEmbeddingProcessor import OpenAIEmbeddingProcessor
from src.core.parser.FileParser import FileParser
from src.core.services.CollectionService import CollectionService
from src.core.services.SnapshotService import SnapshotService


class Orchestrator:
    def __init__(self):
        self.logger = LoggerManager().get()
        self.file_parser = FileParser()
        self.constants = Constants()
        self._qdrant_client = AsyncQdrantClient(
            host=self.constants.QDRANT_SVC,
            port=self.constants.QDRANT_PORT,
            timeout=self.constants.QDRANT_TIMEOUT,
        )
        self.embedding_processor = OpenAIEmbeddingProcessor()
        self.collection_service = CollectionService(self._qdrant_client)
        self.snapshot_service = SnapshotService(self._qdrant_client)

    async def handle_upload_collection_file(
            self,
            file_path: str,
            file_ext: str,
            collection_name: str,
            target_field: str = '',
            meta_field: list[str] = None,
            distance: str = 'Cosine',
            chunk_size: int = 1000,
            chunk_overlap: int = 200,
    ) -> dict[str, Any]:
        """
        Process uploaded file and create a Qdrant collection with embeddings.

        Args:
            file_path: Path to the temporary file
            file_ext: File extension (json, jsonl, csv, txt, pdf)
            collection_name: Name of the collection to create
            target_field: Target field for embedding (required for JSON/JSONL/CSV)
            meta_field: List of metadata field names (optional, for JSON/JSONL/CSV)
            distance: Distance metric (Cosine, Euclidean, Dot)
            chunk_size: Text chunk size for TXT/PDF files
            chunk_overlap: Chunk overlap size for TXT/PDF files

        Returns:
            Dict with status, message, collection_name, and records_count

        Raises:
            ValueError: If validation fails or data extraction fails
        """
        if meta_field is None:
            meta_field = []
        self.logger.info(f"Processing file upload: collection={collection_name}, ext={file_ext}")

        data = await self._process_and_validate_file(
            file_path=file_path,
            file_ext=file_ext,
            target_field=target_field,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        try:
            self.logger.info(f"Building collection: {collection_name}")

            # Prepare points with embeddings
            points, dim = await self._prepare_points(data, target_field, meta_field)

            await self.collection_service.build_collection(
                collection_name=collection_name,
                distance=distance,
                dim=dim,
                points=points,
            )
            self.logger.info(f"Collection '{collection_name}' created successfully with {len(points)} records")

            return {
                'status': 'success',
                'message': f"Collection '{collection_name}' created successfully",
                'collection_name': collection_name,
                'records_count': len(points),
            }

        except Exception as e:
            self.logger.error(f"Collection creation failed: {str(e)}")
            raise

    async def handle_upload_collection_volume(
            self,
            collection_name: str,
            target_field: str = '',
            meta_field: list[str] = None,
            distance: str = 'Cosine',
            chunk_size: int = 1000,
            chunk_overlap: int = 200,
    ) -> dict[str, Any]:
        """
        Create a Qdrant collection from data in shared volume.

        Args:
            collection_name: Name of the collection to create
            target_field: Target field for embedding (required for JSON/JSONL/CSV)
            meta_field: List of metadata field names (optional, for JSON/JSONL/CSV)
            distance: Distance metric (Cosine, Euclidean, Dot)
            chunk_size: Text chunk size for TXT/PDF files
            chunk_overlap: Chunk overlap size for TXT/PDF files

        Returns:
            Dict with status, message, collection_name, and records_count

        Raises:
            ValueError: If validation fails or data extraction fails
        """
        if meta_field is None:
            meta_field = []
        self.logger.info(f"Building collection from volume: collection={collection_name}")

        # 볼륨에서 데이터 처리 및 검증
        data = await self._process_and_validate_volume(
            collection_name=collection_name,
            target_field=target_field,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        try:
            self.logger.info(f"Building collection: {collection_name}")

            # Prepare points with embeddings
            points, dim = await self._prepare_points(data, target_field, meta_field)

            await self.collection_service.build_collection(
                collection_name=collection_name,
                distance=distance,
                dim=dim,
                points=points,
            )
            self.logger.info(f"Collection '{collection_name}' created successfully with {len(points)} records")
            return {
                'status': 'success',
                'message': f"Collection '{collection_name}' created successfully",
                'collection_name': collection_name,
                'records_count': len(points),
            }

        except Exception as e:
            self.logger.error(f"Collection creation failed: {str(e)}")
            raise

    async def handle_add_points(
            self,
            file_path: str,
            file_ext: str,
            collection_name: str,
            target_field: str = '',
            meta_field: list[str] = None,
            chunk_size: int = 500,
            chunk_overlap: int = 50,
    ) -> dict[str, Any]:
        """
        Process uploaded file and add points to an existing Qdrant collection.
        Args:
            file_path: Path to the temporary file
            file_ext: File extension (json, jsonl, csv, txt, pdf)
            collection_name: Name of the existing collection
            target_field: Target field for embedding (required for JSON/JSONL/CSV)
            meta_field: List of metadata field names (optional, for JSON/JSONL/CSV)
            chunk_size: Text chunk size for TXT/PDF files
            chunk_overlap: Chunk overlap size for TXT/PDF files
        Returns:
            Dict with status, message, collection_name, and records_count
        Raises:
            ValueError: If validation fails or data extraction fails
        """
        if meta_field is None:
            meta_field = []
        self.logger.info(f"Adding points to collection: collection={collection_name}, ext={file_ext}")

        data = await self._process_and_validate_file(
            file_path=file_path,
            file_ext=file_ext,
            target_field=target_field,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        try:
            self.logger.info(f"Adding points to collection: {collection_name}")

            # Prepare points with embeddings
            points, _ = await self._prepare_points(data, target_field, meta_field)

            await self.collection_service.add_points(
                collection_name=collection_name,
                points=points,
            )
            self.logger.info(f"Added {len(points)} points to collection '{collection_name}'")

            return {
                'status': 'success',
                'message': f"Successfully added {len(points)} points to collection '{collection_name}'",
                'collection_name': collection_name,
                'records_count': len(points),
            }

        except Exception as e:
            self.logger.error(f"Adding points failed: {str(e)}")
            raise

    async def handle_delete_collection(self, collection_name: str) -> dict[str, Any]:
        """
        Delete a collection.

        Args:
            collection_name: Name of the collection to delete

        Returns:
            Dict with status and message

        Raises:
            ValueError: If collection doesn't exist
            RuntimeError: If deletion fails
        """
        self.logger.info(f"Deleting collection: {collection_name}")

        exists = await self.collection_service.collection_exists(collection_name)
        if not exists:
            self.logger.error(f"Collection '{collection_name}' not found")
            raise ValueError(f"Collection '{collection_name}' not found")

        try:
            await self.collection_service.delete_collection(collection_name)
            self.logger.info(f"Collection '{collection_name}' deleted successfully")

            return {
                'status': 'success',
                'message': f"Collection '{collection_name}' deleted successfully",
                'collection_name': collection_name,
            }

        except Exception as e:
            self.logger.error(f"Collection deletion failed: {str(e)}")
            raise

    async def handle_list_collections(self) -> dict[str, Any]:
        """
        List all collections.

        Returns:
            Dict with list of collection names

        Raises:
            RuntimeError: If listing fails
        """
        self.logger.info('Listing all collections')

        try:
            collections = await self.collection_service.collection_list()
            self.logger.info(f"Found {len(collections)} collections")

            return {
                'collections': collections,
                'count': len(collections),
            }

        except Exception as e:
            self.logger.error(f"Failed to list collections: {str(e)}")
            raise

    async def handle_get_collection_info(self, collection_name: str) -> dict[str, Any]:
        """
        Get detailed information about a collection.

        Args:
            collection_name: Name of the collection

        Returns:
            Dict with collection information

        Raises:
            ValueError: If collection doesn't exist
            RuntimeError: If retrieval fails
        """
        self.logger.info(f"Getting info for collection: {collection_name}")

        exists = await self.collection_service.collection_exists(collection_name)
        if not exists:
            self.logger.error(f"Collection '{collection_name}' not found")
            raise ValueError(f"Collection '{collection_name}' not found")

        try:
            collection_info = await self.collection_service.get_collection_info(collection_name)
            self.logger.info(f"Retrieved info for collection '{collection_name}'")

            return collection_info

        except Exception as e:
            self.logger.error(f"Failed to get collection info: {str(e)}")
            raise

    async def _process_and_validate_file(
            self,
            file_path: str,
            file_ext: str,
            target_field: str,
            chunk_size: int,
            chunk_overlap: int,
    ) -> list[dict[str, Any]]:
        """
        Process and validate the uploaded file based on its type.
        Args:
            file_path: Path to the temporary file
            file_ext: File extension (json, jsonl, csv, txt, pdf)
            target_field: Target field for embedding (required for JSON/JSONL/CSV)
            chunk_size: Text chunk size for TXT/PDF files
            chunk_overlap: Chunk overlap size for TXT/PDF files
        Returns:
            Extracted data ready for embedding (always List[Dict])
        Raises:
            ValueError: If validation fails or data extraction fails
        """
        # 입력 파라미터 검증
        # JSON/JSONL/CSV는 target_field 필수, TXT/PDF는 청크 기반이므로 불필요
        if file_ext in ['json', 'jsonl', 'csv'] and not target_field:
            self.logger.error(f"target_field is required for {file_ext} files")
            raise ValueError(f"target_field is required for {file_ext} files")

        if chunk_size <= 0:
            self.logger.error(f"Invalid chunk_size: {chunk_size}")
            raise ValueError('chunk_size must be positive')

        if chunk_overlap < 0:
            self.logger.error(f"Invalid chunk_overlap: {chunk_overlap}")
            raise ValueError('chunk_overlap cannot be negative')

        if chunk_overlap >= chunk_size:
            self.logger.error(f"chunk_overlap ({chunk_overlap}) >= chunk_size ({chunk_size})")
            raise ValueError('chunk_overlap must be smaller than chunk_size')

        try:
            if file_ext == 'json':
                self.logger.info('Processing JSON file')
                data = await self.file_parser.process_json_file(file_path)
            elif file_ext == 'jsonl':
                self.logger.info('Processing JSONL file')
                data = await self.file_parser.process_jsonl_file(file_path)
            elif file_ext == 'csv':
                self.logger.info('Processing CSV file')
                data = await self.file_parser.process_csv_file(file_path)
            elif file_ext == 'txt':
                self.logger.info(f"Processing TXT file (chunk_size={chunk_size}, overlap={chunk_overlap})")
                data = await self.file_parser.process_txt_file(file_path, chunk_size, chunk_overlap)
            elif file_ext == 'pdf':
                self.logger.info(f"Processing PDF file (chunk_size={chunk_size}, overlap={chunk_overlap})")
                data = await self.file_parser.process_pdf_file(file_path, chunk_size, chunk_overlap)
            else:
                raise ValueError(f"Unsupported file type: {file_ext}")

            if not data:
                self.logger.error('No data extracted from file')
                raise ValueError('No data extracted from file')

            self.logger.info(f"Extracted {len(data)} records from file")
            return data

        except Exception as e:
            self.logger.error(f"File processing failed: {str(e)}")
            raise

    async def _process_and_validate_volume(
            self,
            collection_name: str,
            target_field: str,
            chunk_size: int,
            chunk_overlap: int,
    ) -> list[dict[str, Any]]:
        """
        Process and validate the data from shared volume for the specified collection.
        Args:
            collection_name: Name of the collection
            target_field: Target field for embedding (required for JSON/JSONL/CSV)
            chunk_size: Text chunk size for TXT/PDF files
            chunk_overlap: Chunk overlap size for TXT/PDF files

        Returns:
            Extracted data ready for embedding (always List[Dict])
        Raises:
            ValueError: If validation fails or data extraction fails
        """
        # 컬렉션 디렉토리 경로
        collection_dir = f"{self.constants.QDRANT_DATA_VOLUME}/{collection_name}"

        # 디렉토리 존재 여부 확인
        if not os.path.exists(collection_dir):
            self.logger.error(f"Collection directory not found: {collection_dir}")
            raise ValueError(f"Collection directory not found: {collection_name}")

        if not os.path.isdir(collection_dir):
            self.logger.error(f"Path is not a directory: {collection_dir}")
            raise ValueError(f"Path is not a directory: {collection_name}")

        # 지원되는 파일 찾기
        supported_extensions = ['.json', '.jsonl', '.csv', '.txt', '.pdf']
        found_files = []

        for file_name in os.listdir(collection_dir):
            file_ext = os.path.splitext(file_name)[1].lower()
            if file_ext in supported_extensions:
                found_files.append(file_name)

        # 파일 검증
        if not found_files:
            self.logger.error(f"No supported files found in directory: {collection_dir}")
            raise ValueError(
                f"No supported files (.json, .jsonl, .csv, .txt, .pdf) found in collection directory: {collection_name}",
            )

        if len(found_files) > 1:
            self.logger.warning(f"Multiple files found in directory: {found_files}. Using first file: {found_files[0]}")

        # 첫 번째 파일 사용
        file_path = os.path.join(collection_dir, found_files[0])
        self.logger.info(f"Using file: {file_path}")

        # 파일 확장자 추출
        file_ext = os.path.splitext(file_path)[1].lower().lstrip('.')

        # 입력 파라미터 검증
        # JSON/JSONL/CSV는 target_field 필수, TXT/PDF는 청크 기반이므로 불필요
        if file_ext in ['json', 'jsonl', 'csv'] and not target_field:
            self.logger.error(f"target_field is required for {file_ext} files")
            raise ValueError(f"target_field is required for {file_ext} files")

        if chunk_size <= 0:
            self.logger.error(f"Invalid chunk_size: {chunk_size}")
            raise ValueError('chunk_size must be positive')

        if chunk_overlap < 0:
            self.logger.error(f"Invalid chunk_overlap: {chunk_overlap}")
            raise ValueError('chunk_overlap cannot be negative')

        if chunk_overlap >= chunk_size:
            self.logger.error(f"chunk_overlap ({chunk_overlap}) >= chunk_size ({chunk_size})")
            raise ValueError('chunk_overlap must be smaller than chunk_size')

        try:
            # 파일 타입에 따라 처리
            if file_ext == 'json':
                self.logger.info(f"Processing JSON file from volume: {file_path}")
                data = await self.file_parser.process_json_file(file_path)
            elif file_ext == 'jsonl':
                self.logger.info(f"Processing JSONL file from volume: {file_path}")
                data = await self.file_parser.process_jsonl_file(file_path)
            elif file_ext == 'csv':
                self.logger.info(f"Processing CSV file from volume: {file_path}")
                data = await self.file_parser.process_csv_file(file_path)
            elif file_ext == 'txt':
                self.logger.info(
                    f"Processing TXT file from volume (chunk_size={chunk_size}, overlap={chunk_overlap}): {file_path}",
                )
                data = await self.file_parser.process_txt_file(file_path, chunk_size, chunk_overlap)
            elif file_ext == 'pdf':
                self.logger.info(
                    f"Processing PDF file from volume (chunk_size={chunk_size}, overlap={chunk_overlap}): {file_path}",
                )
                data = await self.file_parser.process_pdf_file(file_path, chunk_size, chunk_overlap)
            else:
                raise ValueError(f"Unsupported file type: {file_ext}")

            # 데이터 검증
            if not data:
                self.logger.error('No data extracted from volume file')
                raise ValueError('No data extracted from file')

            self.logger.info(f"Extracted {len(data)} records from volume file for collection: {collection_name}")
            return data

        except Exception as e:
            self.logger.error(f"Volume file processing failed for collection {collection_name}: {str(e)}")
            raise

    async def _prepare_points(
            self,
            data: list[dict[str, Any]],
            target_field: str = '',
            meta_field: list[str] = None,
    ) -> tuple[list[PointStruct], int]:
        """
        Prepare points for Qdrant insertion by generating embeddings.

        Args:
            data: List of dict records
                  - TXT/PDF: chunk-based with {chunk_id, text, metadata}
                  - JSON/JSONL/CSV: structured data with target_field
            target_field: Field name to use for embedding (required for JSON/JSONL/CSV)
            meta_field: List of metadata field names to include (optional, for JSON/JSONL/CSV)

        Returns:
            Tuple of (List[PointStruct], embedding_dimension)
        """
        if meta_field is None:
            meta_field = []
        # 빈 문자열 필터링 (FastAPI Form에서 빈 값이 ['']로 들어올 수 있음)
        meta_field = [f for f in meta_field if f]
        if not data:
            raise ValueError('No data provided for point preparation')

        # 청크 기반 데이터 (TXT/PDF 파일의 청크)
        if 'chunk_id' in data[0] and 'text' in data[0]:
            self.logger.info(f"Processing chunk-based data (TXT/PDF): {len(data)} chunks")
            is_chunk_data = True

            texts = []
            records = []
            for chunk in data:
                # "text" 필드를 임베딩 대상으로 사용
                text_value = chunk['text']
                if not isinstance(text_value, str):
                    self.logger.warning(f"Converting non-string chunk text to string: {type(text_value)}")
                    text_value = str(text_value)
                texts.append(text_value)

                # payload는 전체 청크 데이터 (chunk_id, text, metadata 포함)
                records.append(chunk)

        # 구조화된 데이터 (JSON/JSONL/CSV)
        else:
            self.logger.info(f"Processing structured data (JSON/JSONL/CSV): {len(data)} records")
            is_chunk_data = False

            if not target_field:
                raise ValueError('target_field is required for structured data (JSON/JSONL/CSV)')

            texts = []
            for record in data:
                if target_field not in record:
                    raise ValueError(f"target_field '{target_field}' not found in data record")
                value = record[target_field]
                if not isinstance(value, str):
                    self.logger.warning(f"Converting non-string value to string: {type(value)}")
                    value = str(value)
                texts.append(value)
            records = data

        # 텍스트 임베딩
        vectors = await self.embedding_processor.batch_embed_texts(texts)
        dim = len(vectors[0]) if vectors else await self.embedding_processor.get_dim()

        # 포인트 생성
        points: list[PointStruct] = []
        for idx, (record, vector) in enumerate(zip(records, vectors)):
            # 청크 데이터의 경우 전체 청크 정보를 payload로 사용
            if is_chunk_data:
                payload = record
            # 구조화된 데이터의 경우 meta_field 처리
            elif meta_field:
                # meta_field 가 지정된 경우: meta_field에 있는 필드만 포함
                # (target_field를 포함하려면 meta_field에 명시해야 함)
                payload = {k: v for k, v in record.items() if k in meta_field}

                # 지정된 필드가 record 에 없을 경우 경고
                missing_fields = set(meta_field) - set(record.keys())
                if missing_fields and idx == 0:  # 첫 record 에서만 로그
                    self.logger.warning(f"Some meta_fields not found in records: {missing_fields}")
            else:
                # meta_field 가 없으면 모든 필드를 payload로 사용 (target_field 포함)
                payload = dict(record)

            # 첫 번째 레코드 디버깅 로그
            if idx == 0:
                self.logger.info(f"[DEBUG] target_field: {target_field}")
                self.logger.info(f"[DEBUG] meta_field: {meta_field}")
                self.logger.info(f"[DEBUG] is_chunk_data: {is_chunk_data}")
                self.logger.info(f"[DEBUG] original record keys: {list(record.keys())}")
                self.logger.info(f"[DEBUG] payload keys: {list(payload.keys())}")
                self.logger.info(f"[DEBUG] payload: {payload}")

            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload=payload,
                ),
            )

        self.logger.info(f"Prepared {len(points)} points for insertion with dimension {dim}")
        return points, dim

    async def handle_create_snapshot(self, collection_name: str) -> dict[str, Any]:
        """
        Create a snapshot for the specified collection and return download info.

        Args:
            collection_name: Name of the collection

        Returns:
            Dict with snapshot_name and snapshot_url

        Raises:
            ValueError: If collection doesn't exist
            RuntimeError: If snapshot creation fails
        """
        self.logger.info(f"Creating snapshot for collection: {collection_name}")

        exists = await self.collection_service.collection_exists(collection_name)
        if not exists:
            self.logger.error(f"Collection '{collection_name}' not found")
            raise ValueError(f"Collection '{collection_name}' not found")

        try:
            await self.snapshot_service.create_snapshot(collection_name)

            # Get latest snapshot
            snapshots = await self.snapshot_service.list_snapshots(collection_name)
            if not snapshots:
                raise RuntimeError('No snapshots found after creation')

            snapshot_name = snapshots[-1]
            snapshot_url = self.snapshot_service.get_snapshot_url(collection_name, snapshot_name)

            self.logger.info(f"Snapshot created: {snapshot_name}")

            return {
                'snapshot_name': snapshot_name,
                'snapshot_url': snapshot_url,
            }

        except Exception as e:
            self.logger.error(f"Snapshot creation failed: {str(e)}")
            raise

    async def handle_create_snapshot_full(self):
        """
        Create a full snapshot for all collections and return download info.

        Returns:
            Dict with snapshot_name and snapshot_url

        Raises:
            RuntimeError: If snapshot creation fails
        """
        self.logger.info('Creating full snapshot for all collections')

        try:
            await self.snapshot_service.create_snapshot_full()

            # Get latest full snapshot
            full_list = await self.snapshot_service.list_snapshots_full()
            if not full_list:
                raise RuntimeError('No full snapshots found after creation')

            snapshot_name = full_list[-1]
            snapshot_url = self.snapshot_service.get_full_snapshot_url(snapshot_name)

            self.logger.info(f"Full snapshot created: {snapshot_name}")

            return {
                'snapshot_name': snapshot_name,
                'snapshot_url': snapshot_url,
            }

        except Exception as e:
            self.logger.error(f"Full snapshot creation failed: {str(e)}")
            raise

    async def handle_delete_snapshot(
        self,
        collection_name: str,
        snapshot_name: str,
    ) -> dict[str, Any]:
        """
        Delete a snapshot for the specified collection.

        Args:
            collection_name: Name of the collection
            snapshot_name: Name of the snapshot to delete

        Returns:
            Dict with status and message

        Raises:
            ValueError: If collection or snapshot doesn't exist
            RuntimeError: If deletion fails
        """
        self.logger.info(f"Deleting snapshot: {snapshot_name} from collection: {collection_name}")

        exists = await self.collection_service.collection_exists(collection_name)
        if not exists:
            self.logger.error(f"Collection '{collection_name}' not found")
            raise ValueError(f"Collection '{collection_name}' not found")

        try:
            snapshots = await self.snapshot_service.list_snapshots(collection_name)
            if snapshot_name not in snapshots:
                self.logger.error(f"Snapshot '{snapshot_name}' not found in collection '{collection_name}'")
                raise ValueError(f"Snapshot '{snapshot_name}' not found")
        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to verify snapshot existence: {str(e)}")
            raise RuntimeError(f"Failed to verify snapshot: {str(e)}")

        try:
            await self.snapshot_service.delete_snapshot(
                collection_name=collection_name,
                snapshot_name=snapshot_name,
            )

            self.logger.info(f"Snapshot '{snapshot_name}' deleted successfully")

            return {
                'status': 'success',
                'message': f"Snapshot '{snapshot_name}' deleted successfully",
                'collection_name': collection_name,
                'snapshot_name': snapshot_name,
            }

        except Exception as e:
            self.logger.error(f"Snapshot deletion failed: {str(e)}")
            raise

    async def handle_delete_snapshot_full(self, snapshot_name: str) -> dict[str, Any]:
        """
        Delete a full snapshot.

        Args:
            snapshot_name: Name of the full snapshot to delete

        Returns:
            Dict with status and message

        Raises:
            ValueError: If snapshot doesn't exist
            RuntimeError: If deletion fails
        """
        self.logger.info(f"Deleting full snapshot: {snapshot_name}")

        try:
            full_list = await self.snapshot_service.list_snapshots_full()
            if snapshot_name not in full_list:
                self.logger.error(f"Full snapshot '{snapshot_name}' not found")
                raise ValueError(f"Full snapshot '{snapshot_name}' not found")
        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to verify full snapshot existence: {str(e)}")
            raise RuntimeError(f"Failed to verify full snapshot: {str(e)}")

        try:
            await self.snapshot_service.delete_snapshot_full(snapshot_name)

            self.logger.info(f"Full snapshot '{snapshot_name}' deleted successfully")

            return {
                'status': 'success',
                'message': f"Full snapshot '{snapshot_name}' deleted successfully",
                'snapshot_name': snapshot_name,
            }

        except Exception as e:
            self.logger.error(f"Full snapshot deletion failed: {str(e)}")
            raise

    async def handle_list_snapshots(self, collection_name: str) -> dict[str, Any]:
        """
        List all snapshots for the specified collection.

        Args:
            collection_name: Name of the collection

        Returns:
            Dict with collection_name and list of snapshot names

        Raises:
            ValueError: If collection doesn't exist
            RuntimeError: If listing fails
        """
        self.logger.info(f"Listing snapshots for collection: {collection_name}")

        exists = await self.collection_service.collection_exists(collection_name)
        if not exists:
            self.logger.error(f"Collection '{collection_name}' not found")
            raise ValueError(f"Collection '{collection_name}' not found")

        try:
            snapshot_names = await self.snapshot_service.list_snapshots(collection_name)

            self.logger.info(f"Found {len(snapshot_names)} snapshots for collection '{collection_name}'")

            return {
                'collection_name': collection_name,
                'snapshots': snapshot_names,
                'count': len(snapshot_names),
            }

        except Exception as e:
            self.logger.error(f"Failed to list snapshots: {str(e)}")
            raise

    async def handle_list_snapshots_full(self) -> dict[str, Any]:
        """
        List all full snapshots.

        Returns:
            Dict with list of full snapshot names

        Raises:
            RuntimeError: If listing fails
        """
        self.logger.info('Listing all full snapshots')

        try:
            snapshot_names = await self.snapshot_service.list_snapshots_full()

            self.logger.info(f"Found {len(snapshot_names)} full snapshots")

            return {
                'snapshots': snapshot_names,
                'count': len(snapshot_names),
            }

        except Exception as e:
            self.logger.error(f"Failed to list full snapshots: {str(e)}")
            raise

    async def handle_download_snapshot(self, snapshot_url: str) -> bytes:
        """
        Download snapshot file content from URL.

        Args:
            snapshot_url: URL to download snapshot from

        Returns:
            Snapshot file content as bytes

        Raises:
            RuntimeError: If download fails
        """
        self.logger.info(f"Downloading snapshot from: {snapshot_url}")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(snapshot_url, timeout=120.0)
                response.raise_for_status()
            self.logger.info(f"Snapshot '{snapshot_url}' downloaded successfully")
            return response.content
        except Exception as e:
            self.logger.error(f"Snapshot download failed: {str(e)}")
            raise RuntimeError(f"Snapshot download failed: {str(e)}")

    async def handle_download_snapshot_full(self, snapshot_name: str) -> bytes:
        """
        Download full snapshot file content from Qdrant snapshot storage.

        Args:
            snapshot_name: Name of the snapshot to download

        Returns:
            Snapshot file content as bytes

        Raises:
            ValueError: If snapshot doesn't exist
            RuntimeError: If download fails
        """
        self.logger.info(f"Downloading full snapshot: {snapshot_name}")
        try:
            # Verify snapshot exists
            full_list = await self.snapshot_service.list_snapshots_full()
            if snapshot_name not in full_list:
                self.logger.error(f"Full snapshot '{snapshot_name}' not found in snapshot list")
                raise ValueError(f"Snapshot '{snapshot_name}' not found")

            # Build URL and download
            download_url = self.snapshot_service.get_full_snapshot_url(snapshot_name)
            self.logger.info(f"Downloading full snapshot from: {download_url}")

            async with httpx.AsyncClient() as client:
                response = await client.get(download_url, timeout=300.0)
                response.raise_for_status()

            self.logger.info(f"Full snapshot '{snapshot_name}' downloaded successfully")
            return response.content
        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"Full snapshot download failed: {str(e)}")
            raise RuntimeError(f"Full snapshot download failed: {str(e)}")

    async def handle_recover_snapshot_from_file(
        self,
        collection_name: str,
        snapshot_content: bytes,
    ) -> dict[str, Any]:
        """
        Restore a collection from uploaded snapshot file.
        Uses Qdrant HTTP API to upload snapshot file.

        Args:
            collection_name: Name of the collection to restore
            snapshot_content: Snapshot file content as bytes

        Returns:
            Dict with status, message, collection_name, and collection_info

        Raises:
            ValueError: If snapshot content is empty
            RuntimeError: If restoration fails
        """
        self.logger.info(f"Restoring collection from file: {collection_name}")

        if not snapshot_content:
            self.logger.error('Empty snapshot content')
            raise ValueError('Empty snapshot file')

        try:
            await self.snapshot_service.recover_snapshot_file(
                collection_name=collection_name,
                snapshot_content=snapshot_content,
            )

            collection_info = await self.collection_service.get_collection_info(collection_name)

            self.logger.info(f"Collection '{collection_name}' restored successfully from file")

            return {
                'status': 'success',
                'message': f"Collection '{collection_name}' restored successfully",
                'collection_name': collection_name,
                'collection_info': collection_info,
            }

        except Exception as e:
            self.logger.error(f"Collection restoration from file failed: {str(e)}")
            raise

    async def handle_recover_snapshot_from_volume(
        self,
        collection_name: str,
        snapshot_name: str,
    ) -> dict[str, Any]:
        """
        Restore a collection from existing snapshot in shared volume.
        Uses AsyncQdrantClient API to recover from file:// URI.

        Note: This method does NOT require the collection to exist beforehand.
        The snapshot recovery will create or overwrite the collection.

        Args:
            collection_name: Name of the collection to restore
            snapshot_name: Name of the snapshot to restore from

        Returns:
            Dict with status, message, collection_name, and collection_info

        Raises:
            ValueError: If snapshot doesn't exist in volume
            RuntimeError: If restoration fails
        """
        self.logger.info(f"Restoring collection from volume: {collection_name}, snapshot: {snapshot_name}")

        if not snapshot_name:
            self.logger.error('snapshot_name is required for volume recovery')
            raise ValueError('snapshot_name is required')

        try:
            await self.snapshot_service.recover_snapshot_volume(
                collection_name=collection_name,
                snapshot_name=snapshot_name,
            )

            collection_info = await self.collection_service.get_collection_info(collection_name)

            self.logger.info(f"Collection '{collection_name}' restored successfully from snapshot '{snapshot_name}'")

            return {
                'status': 'success',
                'message': f"Collection '{collection_name}' restored from snapshot '{snapshot_name}'",
                'collection_name': collection_name,
                'snapshot_name': snapshot_name,
                'collection_info': collection_info,
            }

        except Exception as e:
            self.logger.error(f"Collection restoration from volume failed: {str(e)}")
            raise

    async def cleanup_resources(self):
        """Clean up resources on shutdown."""
        self.logger.info('Cleaning up Orchestrator resources')
        try:
            if self._qdrant_client is not None:
                await self._qdrant_client.close()
                self.logger.info('Qdrant client connection closed')
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
