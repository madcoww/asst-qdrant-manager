"""
Author : Wonjun Kim
e-mail : wonjun.kim@seculayer.com
Powered by Seculayer © 2025 AI Team, R&D Center.
"""
from __future__ import annotations

import os
import tempfile

import aiofiles
from fastapi import APIRouter
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import Request
from fastapi import UploadFile

from src.common.Constant import Constants
from src.utils.NameValidators import validate_collection_name

router = APIRouter(
    prefix=Constants.QDRANT_COLLECTION_ENDPOINT,
    tags=['Collections'],
)


@router.post('/file')
async def create_collection_from_file(
    request: Request,
    file: UploadFile = File(...),
    collection_name: str = Form(default=''),
    target_field: str = Form(default=''),
    meta_field: list[str] = Form(default=[]),
    distance: str = Form(default='Cosine'),
    chunk_size: int = Form(default=1000),
    chunk_overlap: int = Form(default=200),
):
    """
    파일을 업로드하고 컬렉션을 생성합니다.

    - **file**: 업로드할 파일 (json, jsonl, txt, csv, pdf) - 최대 20MB
    - **collection_name**: 생성할 컬렉션 이름
    - **target_field**: 대상 필드명 (json, jsonl, csv용)
    - **meta_field**: 메타데이터 필드명 리스트 (선택사항)
    - **distance**: 거리 측정 방식 (Cosine, Euclidean, Dot)
    - **chunk_size**: 텍스트 청크 크기 (txt, pdf용, 기본값: 1000)
    - **chunk_overlap**: 청크 오버랩 크기 (txt, pdf용, 기본값: 200)
    """
    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
    temp_file_path = None
    try:
        collection_name = validate_collection_name(collection_name)

        # Content-Length 헤더로 파일 크기 사전 검증
        content_length = request.headers.get('content-length')
        if content_length and int(content_length) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail='File too large. Maximum size is 20MB',
            )

        # 파일명 검증
        if not file.filename or '.' not in file.filename:
            raise HTTPException(status_code=400, detail='Invalid filename')

        # 파일 확장자 확인
        file_ext = os.path.splitext(file.filename)[1].lstrip('.').lower()
        if not file_ext:
            raise HTTPException(status_code=400, detail='File must have an extension')
        if file_ext not in ['json', 'jsonl', 'txt', 'csv', 'pdf']:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_ext}")

        # 임시 파일에 청크 단위로 저장 (메모리 절약)
        temp_fd, temp_file_path = tempfile.mkstemp(suffix=f'.{file_ext}')
        os.close(temp_fd)

        total_size = 0
        async with aiofiles.open(temp_file_path, 'wb') as f:
            while chunk := await file.read(8192):  # 8KB씩 스트리밍
                total_size += len(chunk)
                if total_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail='File too large. Maximum size is 20MB',
                    )
                await f.write(chunk)

        # Orchestrator를 통한 비즈니스 로직 처리
        orchestrator = request.app.state.orchestrator
        result = await orchestrator.handle_upload_collection_file(
            file_path=temp_file_path,
            file_ext=file_ext,
            collection_name=collection_name,
            target_field=target_field,
            meta_field=meta_field,
            distance=distance,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        request.app.state.orchestrator.logger.error(
            f"Unexpected error: {str(e)}", exc_info=True,
        )
        raise HTTPException(status_code=500, detail='Internal server error')
    finally:
        # 임시 파일 정리
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


@router.post('/volume')
async def create_collection_from_volume(
        request: Request,
        collection_name: str = Form(default=''),
        target_field: str = Form(default=''),
        meta_field: list[str] = Form(default=[]),
        distance: str = Form(default='Cosine'),
        chunk_size: int = Form(default=1000),
        chunk_overlap: int = Form(default=200),
):
    """
    공유 볼륨의 데이터로부터 컬렉션을 생성합니다.

    **사전 준비:**
    1. 마운트된 볼륨 경로에 '{collection_name}' 디렉토리 생성
    2. 해당 디렉토리에 데이터 파일 배치 (json/jsonl/csv/txt/pdf)
       예: /volume/my_collection/data.json

    **중요:** 디렉토리 이름 = 컬렉션 이름

    - **collection_name**: 컬렉션 이름 (디렉토리 이름과 동일)
    - **target_field**: 대상 필드명 (json, jsonl, csv용)
    - **meta_field**: 메타데이터 필드명 리스트 (선택사항)
    - **distance**: 거리 측정 방식 (Cosine/Euclidean/Dot)
    - **chunk_size**: 텍스트 청크 크기 (txt, pdf용, 기본: 1000)
    - **chunk_overlap**: 청크 오버랩 크기 (txt, pdf용, 기본: 200)
    """
    try:
        # 컬렉션 이름 검증
        collection_name = validate_collection_name(collection_name)

        # Orchestrator를 통한 비즈니스 로직 처리
        orchestrator = request.app.state.orchestrator
        result = await orchestrator.handle_upload_collection_volume(
            collection_name=collection_name,
            target_field=target_field,
            meta_field=meta_field,
            distance=distance,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        return result

    except HTTPException:
        raise
    except ValueError as e:
        # 볼륨 디렉토리나 파일을 찾을 수 없는 경우
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        request.app.state.orchestrator.logger.error(
            f"Unexpected error in volume collection creation: {str(e)}", exc_info=True,
        )
        raise HTTPException(status_code=500, detail='Internal server error')


@router.post('/{collection_name}/append')
async def append_to_collection(
    collection_name: str,
    request: Request,
    file: UploadFile = File(...),
    target_field: str = Form(default=''),
    meta_field: list[str] = Form(default=[]),
    chunk_size: int = Form(default=1000),
    chunk_overlap: int = Form(default=200),
):
    """
    기존 컬렉션에 데이터를 추가합니다.

    - **collection_name**: 데이터 추가할 컬렉션 이름
    - **file**: 업로드할 파일 (json, jsonl, txt, csv, pdf) - 최대 20MB
    - **target_field**: 대상 필드명 (json, jsonl, csv용)
    - **meta_field**: 메타데이터 필드명 리스트 (선택사항)
    - **chunk_size**: 텍스트 청크 크기 (txt, pdf용, 기본값: 1000)
    - **chunk_overlap**: 청크 오버랩 크기 (txt, pdf용, 기본값: 200)
    """
    MAX_FILE_SIZE = 20 * 1024 * 1024
    temp_file_path = None
    try:
        collection_name = validate_collection_name(collection_name)

        # Content-Length 헤더로 파일 크기 사전 검증
        content_length = request.headers.get('content-length')
        if content_length and int(content_length) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail='File too large. Maximum size is 20MB',
            )

        # 파일명 검증
        if not file.filename or '.' not in file.filename:
            raise HTTPException(status_code=400, detail='Invalid filename')

        # 파일 확장자 확인
        file_ext = os.path.splitext(file.filename)[1].lstrip('.').lower()
        if not file_ext:
            raise HTTPException(status_code=400, detail='File must have an extension')
        if file_ext not in ['json', 'jsonl', 'txt', 'csv', 'pdf']:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_ext}")

        # 임시 파일에 청크 단위로 저장 (메모리 절약)
        temp_fd, temp_file_path = tempfile.mkstemp(suffix=f'.{file_ext}')
        os.close(temp_fd)

        total_size = 0
        async with aiofiles.open(temp_file_path, 'wb') as f:
            while chunk := await file.read(8192):  # 8KB씩 스트리밍
                total_size += len(chunk)
                if total_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail='File too large. Maximum size is 20MB',
                    )
                await f.write(chunk)

        orchestrator = request.app.state.orchestrator
        result = await orchestrator.handle_add_points(
            file_path=temp_file_path,
            file_ext=file_ext,
            collection_name=collection_name,
            target_field=target_field,
            meta_field=meta_field,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        request.app.state.orchestrator.logger.error(
            f"Unexpected error: {str(e)}", exc_info=True,
        )
        raise HTTPException(status_code=500, detail='Internal server error')
    finally:
        # 임시 파일 정리
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


@router.delete('/{collection_name}')
async def delete_collection(
    request: Request,
    collection_name: str,
):
    """
    지정된 컬렉션을 삭제합니다.

    - **collection_name**: 삭제할 컬렉션 이름
    """
    try:
        orchestrator = request.app.state.orchestrator
        result = await orchestrator.handle_delete_collection(
            collection_name=collection_name,
        )
        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        request.app.state.orchestrator.logger.error(
            f"Unexpected error: {str(e)}", exc_info=True,
        )
        raise HTTPException(status_code=500, detail='Internal server error')


@router.get('')
async def list_collections(
        request: Request,
):
    """
    모든 컬렉션의 목록을 가져옵니다.
    """
    try:
        orchestrator = request.app.state.orchestrator
        result = await orchestrator.handle_list_collections()
        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        request.app.state.orchestrator.logger.error(
            f"Unexpected error: {str(e)}", exc_info=True,
        )
        raise HTTPException(status_code=500, detail='Internal server error')


@router.get('/{collection_name}')
async def get_collection_info(
    request: Request,
    collection_name: str,
):
    """
    지정된 컬렉션의 상세 정보를 가져옵니다.

    - **collection_name**: 조회할 컬렉션 이름
    """
    try:
        orchestrator = request.app.state.orchestrator
        result = await orchestrator.handle_get_collection_info(
            collection_name=collection_name,
        )
        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        request.app.state.orchestrator.logger.error(
            f"Unexpected error: {str(e)}", exc_info=True,
        )
        raise HTTPException(status_code=500, detail='Internal server error')
