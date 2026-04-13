"""
Author : Wonjun Kim
e-mail : wonjun.kim@seculayer.com
Powered by Seculayer © 2025 AI Team, R&D Center.
"""
from __future__ import annotations

from typing import cast

from src.common.ConfigManager import ConfigManager
from src.utils.Singleton import Singleton


class Constants(metaclass=Singleton):
    __config_manager = ConfigManager()

    QDRANT_MANAGER_SVC = __config_manager.get('qdrant_manager_svc')
    QDRANT_MANAGER_PORT = int(cast(int, __config_manager.get('qdrant_manager_port')))
    QDRANT_COLLECTION_ENDPOINT = __config_manager.get('qdrant_collection_endpoint')
    QDRANT_SNAPSHOTS_ENDPOINT = __config_manager.get('qdrant_snapshots_endpoint')

    QDRANT_SVC = __config_manager.get('qdrant_svc')
    QDRANT_PORT = int(cast(int, __config_manager.get('qdrant_port')))
    QDRANT_TIMEOUT = float(cast(float, __config_manager.get('qdrant_timeout')))
    QDRANT_DATA_VOLUME = __config_manager.get('qdrant_data_volume')
    QDRANT_SNAPSHOT_VOLUME = __config_manager.get('qdrant_snapshot_volume')

    EMBEDDER_SVC = __config_manager.get('embedder_svc')
    EMBEDDER_PORT = int(cast(int, __config_manager.get('embedder_port')))
    EMBEDDER_ENDPOINT = __config_manager.get('embedder_endpoint')
    EMBEDDER_MODEL = cast(str, __config_manager.get('embedder_model'))
    EMBEDDER_BATCH_SIZE = int(cast(int, __config_manager.get('embedder_batch_size')))
