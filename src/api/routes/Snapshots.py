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
from fastapi.responses import StreamingResponse

from src.common.Constant import Constants

router = APIRouter(
    prefix=Constants.QDRANT_SNAPSHOTS_ENDPOINT,
    tags=['Snapshots'],
)


@router.post('/collections/{collection_name}')
async def create_and_download_snapshot(
        request: Request,
        collection_name: str,
):
    """
    컬렉션의 스냅샷을 생성하고 파일로 반환합니다.

    - **collection_name**: 스냅샷을 생성할 컬렉션 이름
    """
    try:
        orchestrator = request.app.state.orchestrator

        # 스냅샷 생성 및 정보 조회
        snapshot_info = await orchestrator.handle_create_snapshot(collection_name)
        snapshot_name = snapshot_info['snapshot_name']
        snapshot_url = snapshot_info['snapshot_url']

        # 스냅샷 다운로드
        snapshot_content = await orchestrator.handle_download_snapshot(snapshot_url)

        # 스트리밍 응답 반환
        return StreamingResponse(
            iter([snapshot_content]),
            media_type='application/octet-stream',
            headers={
                'Content-Disposition': f"attachment; filename={snapshot_name}",
            },
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        request.app.state.orchestrator.logger.error(
            f"Unexpected error: {str(e)}", exc_info=True,
        )
        raise HTTPException(status_code=500, detail='Internal server error')


@router.delete('/collections/{collection_name}/{snapshot_name}')
async def delete_snapshot(
        request: Request,
        collection_name: str,
        snapshot_name: str,
):
    """
    컬렉션의 특정 스냅샷을 삭제합니다.

    - **collection_name**: 컬렉션 이름
    - **snapshot_name**: 삭제할 스냅샷 이름
    """
    try:
        orchestrator = request.app.state.orchestrator
        result = await orchestrator.handle_delete_snapshot(
            collection_name=collection_name,
            snapshot_name=f"{snapshot_name}.snapshot",
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


@router.get('/collections/{collection_name}')
async def list_snapshots(
        request: Request,
        collection_name: str,
):
    """
    컬렉션의 모든 스냅샷 목록을 가져옵니다.

    - **collection_name**: 컬렉션 이름
    """
    try:
        orchestrator = request.app.state.orchestrator
        result = await orchestrator.handle_list_snapshots(
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


@router.post('/collections/{collection_name}/restore/file')
async def restore_collection_from_file(
        request: Request,
        collection_name: str,
        file: UploadFile = File(...),
):
    """
    스냅샷 파일로부터 컬렉션을 복원합니다 (파일 업로드 방식).

    - **collection_name**: 복원할 컬렉션 이름
    - **file**: 스냅샷 파일 - 최대 20MB
    """
    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
    temp_file_path = None
    try:
        # Content-Length 헤더로 파일 크기 사전 검증
        content_length = request.headers.get('content-length')
        if content_length and int(content_length) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail='File too large. Maximum size is 20MB',
            )

        temp_fd, temp_file_path = tempfile.mkstemp(suffix='.snapshot')
        os.close(temp_fd)

        total_size = 0
        async with aiofiles.open(temp_file_path, 'wb') as f:
            while chunk := await file.read(8192):
                total_size += len(chunk)
                if total_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail='File too large. Maximum size is 20MB',
                    )
                await f.write(chunk)

        async with aiofiles.open(temp_file_path, 'rb') as f:
            snapshot_content = await f.read()

        orchestrator = request.app.state.orchestrator
        result = await orchestrator.handle_recover_snapshot_from_file(
            collection_name=collection_name,
            snapshot_content=snapshot_content,
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


@router.post('/collections/{collection_name}/restore/volume')
async def restore_collection_from_volume(
        request: Request,
        collection_name: str,
        snapshot_name: str = Form(default=''),
):
    """
    Qdrant 서버에 이미 존재하는 스냅샷으로부터 컬렉션을 복원합니다.

    - **collection_name**: 복원할 컬렉션 이름
    - **snapshot_name**: 복원할 스냅샷 이름
    """
    try:
        orchestrator = request.app.state.orchestrator
        result = await orchestrator.handle_recover_snapshot_from_volume(
            collection_name=collection_name,
            snapshot_name=f"{snapshot_name}.snapshot",
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


@router.post('/full')
async def create_and_download_full_snapshot(
        request: Request,
):
    """
    모든 컬렉션의 Full 스냅샷을 생성하고 파일로 반환합니다.
    """
    try:
        orchestrator = request.app.state.orchestrator

        # Full 스냅샷 생성 및 정보 조회
        snapshot_info = await orchestrator.handle_create_snapshot_full()
        snapshot_name = snapshot_info['snapshot_name']

        # 스냅샷 다운로드 (이름만 전달)
        snapshot_full_content = await orchestrator.handle_download_snapshot_full(snapshot_name)

        return StreamingResponse(
            iter([snapshot_full_content]),
            media_type='application/octet-stream',
            headers={
                'Content-Disposition': f"attachment; filename={snapshot_name}",
            },
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        request.app.state.orchestrator.logger.error(
            f"Unexpected error: {str(e)}", exc_info=True,
        )
        raise HTTPException(status_code=500, detail='Internal server error')


@router.delete('/full/{snapshot_name}')
async def delete_full_snapshot(
        request: Request,
        snapshot_name: str,
):
    """
    Full 스냅샷을 삭제합니다.

    - **snapshot_name**: 삭제할 Full 스냅샷 이름
    """
    try:
        orchestrator = request.app.state.orchestrator
        result = await orchestrator.handle_delete_snapshot_full(
            snapshot_name=f"{snapshot_name}.snapshot",
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


@router.get('/full')
async def list_full_snapshot(
        request: Request,
):
    """
    모든 Full 스냅샷의 목록을 가져옵니다.
    """
    try:
        orchestrator = request.app.state.orchestrator
        result = await orchestrator.handle_list_snapshots_full()

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
