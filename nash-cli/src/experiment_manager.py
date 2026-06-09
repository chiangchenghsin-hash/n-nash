"""
Experiment Manager — 实验管理器桩模块
为 sweep_service 提供最小的 ExperimentManager 依赖。
"""

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExperimentManager:
    """实验管理器桩类 — 实际实验运行逻辑由 model.py 提供"""

    def __init__(self):
        logger.info("ExperimentManager placeholder initialized")
