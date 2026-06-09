"""
参数扫描服务
用于批量运行多组实验配置，探索参数空间
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from src.services.task_queue import get_task_queue, TaskInfo, TaskStatus
from src.experiment_manager import ExperimentManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SweepService:
    """
    参数扫描服务
    
    功能:
    - 批量实验配置生成
    - 后台任务执行
    - 进度跟踪
    - 结果汇总分析
    """
    
    def __init__(self):
        """初始化参数扫描服务"""
        self.task_queue = get_task_queue()
        self.experiment_manager = ExperimentManager()
        self.sweep_tasks: Dict[str, Dict[str, Any]] = {}
        
        logger.info("SweepService initialized")
    
    async def start_sweep(
        self,
        sweep_id: str,
        base_config: Dict[str, Any],
        parameter_name: str,
        param_range: List[float],
        param_step: float,
        max_concurrent: int = 3
    ) -> str:
        """
        启动参数扫描任务
        
        Args:
            sweep_id: 扫描任务 ID
            base_config: 基础配置
            parameter_name: 要扫描的参数名
            param_range: [min_value, max_value]
            param_step: 步长
            max_concurrent: 最大并发实验数
        
        Returns:
            str: 任务 ID
        """
        # 生成所有配置组合
        configs = []
        current = param_range[0]
        while current <= param_range[1]:
            config = base_config.copy()
            config[parameter_name] = current
            configs.append(config)
            current += param_step
        
        total_configs = len(configs)
        logger.info(f"Generated {total_configs} configurations for sweep {sweep_id}")
        
        # 创建扫描任务元数据
        self.sweep_tasks[sweep_id] = {
            "sweep_id": sweep_id,
            "parameter_name": parameter_name,
            "param_range": param_range,
            "param_step": param_step,
            "total_configs": total_configs,
            "completed_configs": 0,
            "results": [],
            "errors": [],
            "created_at": datetime.now(),
            "status": "running"
        }
        
        # 提交扫描任务到队列
        await self.task_queue.submit_task(
            task_id=sweep_id,
            task_type="parameter_sweep",
            task_func=self._run_sweep,
            total_steps=total_configs,
            metadata={
                "sweep_id": sweep_id,
                "parameter_name": parameter_name,
                "total_configs": total_configs
            }
        )
        
        logger.info(f"Started sweep task {sweep_id}")
        return sweep_id
    
    async def _run_sweep(self, task_info: TaskInfo):
        """
        执行参数扫描任务
        
        Args:
            task_info: 任务信息
        """
        sweep_id = task_info.task_id
        sweep_data = self.sweep_tasks.get(sweep_id)
        
        if not sweep_data:
            raise ValueError(f"Sweep data not found for {sweep_id}")
        
        configs = sweep_data.get("configs", [])
        max_concurrent = sweep_data.get("max_concurrent", 3)
        
        logger.info(f"Running sweep {sweep_id} with {len(configs)} configs")
        
        # 创建信号量控制并发
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def run_single_experiment(config: Dict[str, Any], index: int):
            """运行单个实验"""
            async with semaphore:
                try:
                    logger.info(f"Running experiment {index+1}/{len(configs)}")
                    
                    # 创建并运行实验
                    experiment_id = f"{sweep_id}_exp_{index}"
                    result = await self._run_experiment(experiment_id, config)
                    
                    # 记录结果
                    sweep_data["results"].append({
                        "index": index,
                        "experiment_id": experiment_id,
                        "config": config,
                        "result": result,
                        "success": True
                    })
                    
                    # 更新进度
                    sweep_data["completed_configs"] += 1
                    self.task_queue.update_progress(sweep_id, sweep_data["completed_configs"])
                    
                    logger.info(f"Experiment {index+1}/{len(configs)} completed")
                    return result
                    
                except Exception as e:
                    logger.error(f"Experiment {index+1} failed: {e}")
                    sweep_data["errors"].append({
                        "index": index,
                        "config": config,
                        "error": str(e)
                    })
                    sweep_data["completed_configs"] += 1
                    self.task_queue.update_progress(sweep_id, sweep_data["completed_configs"])
                    return None
        
        # 并发运行所有实验
        tasks = [
            run_single_experiment(config, i) 
            for i, config in enumerate(configs)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 汇总结果
        sweep_data["status"] = "completed"
        sweep_data["completed_at"] = datetime.now()
        sweep_data["success_count"] = len([r for r in results if r is not None])
        sweep_data["failure_count"] = len([r for r in results if r is None])
        
        logger.info(
            f"Sweep {sweep_id} completed: "
            f"{sweep_data['success_count']} successes, "
            f"{sweep_data['failure_count']} failures"
        )
        
        return {
            "sweep_id": sweep_id,
            "status": "completed",
            "success_count": sweep_data["success_count"],
            "failure_count": sweep_data["failure_count"],
            "results_summary": self._generate_results_summary(sweep_data)
        }
    
    async def _run_experiment(
        self,
        experiment_id: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        运行单个实验
        
        Args:
            experiment_id: 实验 ID
            config: 实验配置
        
        Returns:
            实验结果字典
        """
        # 这里应该调用实际的实验运行逻辑
        # 目前是简化版本
        
        logger.info(f"Running experiment {experiment_id}")
        
        # TODO: 实现真实的实验运行逻辑
        # 目前返回模拟结果
        await asyncio.sleep(0.1)  # 模拟运行时间
        
        return {
            "experiment_id": experiment_id,
            "status": "completed",
            "metrics": {
                "gini_coefficient": 0.35,
                "mean_hostility": 0.25,
                "avg_energy": 75.0
            }
        }
    
    def _generate_results_summary(self, sweep_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成结果汇总
        
        Args:
            sweep_data: 扫描任务数据
        
        Returns:
            结果汇总字典
        """
        successful_results = [
            r for r in sweep_data["results"] if r.get("success")
        ]
        
        if not successful_results:
            return {"message": "No successful experiments"}
        
        # 提取关键指标
        parameter_values = []
        gini_values = []
        hostility_values = []
        
        for result in successful_results:
            config = result["config"]
            metrics = result["result"]["metrics"]
            
            parameter_values.append(config.get(sweep_data["parameter_name"]))
            gini_values.append(metrics.get("gini_coefficient", 0))
            hostility_values.append(metrics.get("mean_hostility", 0))
        
        return {
            "parameter_name": sweep_data["parameter_name"],
            "data_points": len(parameter_values),
            "parameter_range": [min(parameter_values), max(parameter_values)],
            "gini_range": [min(gini_values), max(gini_values)],
            "hostility_range": [min(hostility_values), max(hostility_values)],
            "avg_gini": sum(gini_values) / len(gini_values),
            "avg_hostility": sum(hostility_values) / len(hostility_values)
        }
    
    def get_sweep_status(self, sweep_id: str) -> Optional[Dict[str, Any]]:
        """
        获取扫描任务状态
        
        Args:
            sweep_id: 扫描任务 ID
        
        Returns:
            任务状态字典
        """
        sweep_data = self.sweep_tasks.get(sweep_id)
        if not sweep_data:
            return None
        
        task_info = self.task_queue.get_task(sweep_id)
        
        return {
            "sweep_id": sweep_id,
            "status": sweep_data["status"],
            "progress": task_info.progress if task_info else 0.0,
            "total_configs": sweep_data["total_configs"],
            "completed_configs": sweep_data["completed_configs"],
            "success_count": sweep_data.get("success_count", 0),
            "failure_count": sweep_data.get("failure_count", 0),
            "created_at": sweep_data["created_at"].isoformat(),
            "completed_at": sweep_data.get("completed_at"),
            "errors": sweep_data["errors"][-5:]  # 最近 5 个错误
        }
    
    def get_sweep_results(self, sweep_id: str) -> Optional[Dict[str, Any]]:
        """
        获取扫描任务完整结果
        
        Args:
            sweep_id: 扫描任务 ID
        
        Returns:
            完整结果字典
        """
        sweep_data = self.sweep_tasks.get(sweep_id)
        if not sweep_data:
            return None
        
        if sweep_data["status"] != "completed":
            return {
                "sweep_id": sweep_id,
                "status": sweep_data["status"],
                "message": "Sweep not completed yet"
            }
        
        return {
            "sweep_id": sweep_id,
            "status": "completed",
            "summary": self._generate_results_summary(sweep_data),
            "results": sweep_data["results"],
            "errors": sweep_data["errors"]
        }


# 全局服务实例
_sweep_service: Optional[SweepService] = None


def get_sweep_service() -> SweepService:
    """获取全局参数扫描服务实例"""
    global _sweep_service
    if _sweep_service is None:
        _sweep_service = SweepService()
    return _sweep_service
