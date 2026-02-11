"""
Author : Wonjun Kim
e-mail : wonjun.kim@seculayer.com
Powered by Seculayer © 2025 AI Team, R&D Center.
"""
from __future__ import annotations

from fastapi.middleware.cors import CORSMiddleware

from src.api.Router import app
from src.common.Constant import Constants

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
    expose_headers=['*'],
)


@app.get('/')
async def root():
    return {'message': 'Qdrant Manager Server is running.'}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(
        app=app,
        host='0.0.0.0',
        port=Constants.QDRANT_MANAGER_PORT,
    )
