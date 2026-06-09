"""
异步任务队列服务
用于管理后台批量实验任务
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskInfo:
    """任务信息"""
    task_id: str
    task_type: str
    status: TaskStatus = TaskStatus.PENDING
    total_steps: int = 0
    completed_steps: int = 0
    progress: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status.value,
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "progress": self.progress,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "result": self.result,
            "metadata": self.metadata
        }


class TaskQueue:
    """
    异步任务队列管理器
    
    功能:
    - 任务提交与调度
    - 进度跟踪
    - 错误处理
    - 结果缓存
    """
    
    def __init__(self, max_concurrent_tasks: int = 5):
        """
        初始化任务队列
        
        Args:
            max_concurrent_tasks: 最大并发任务数
        """
        self.max_concurrent_tasks = max_concurrent_tasks
        self.tasks: Dict[str, TaskInfo] = {}
        self.queue: asyncio.Queue = asyncio.Queue()
        self._workers: List[asyncio.Task] = []
        self._shutdown = False
        
        # 启动工作线程
        for i in range(max_concurrent_tasks):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self._workers.append(worker)
        
        logger.info(f"TaskQueue initialized with {max_concurrent_tasks} workers")
    
    async def _worker(self, worker_name: str):
        """
        工作线程 - 从队列中获取任务并执行
        
        Args:
            worker_name: 工作线程名称
        """
        logger.info(f"{worker_name} started")
        
        while not self._shutdown:
            try:
                # 等待任务
                task_func, task_info = await self.queue.get()
                
                if task_func is None:
                    # 收到关闭信号
                    break
                
                # 更新任务状态为运行中
                task_info.status = TaskStatus.RUNNING
                task_info.started_at = datetime.now()
                
                logger.info(f"{worker_name} executing task {task_info.task_id}")
                
                try:
                    # 执行任务
                    result = await task_func(task_info)
                    task_info.result = result
                    task_info.status = TaskStatus.COMPLETED
                    task_info.completed_at = datetime.now()
                    logger.info(f"{worker_name} completed task {task_info.task_id}")
                    
                except Exception as e:
                    logger.error(f"{worker_name} failed task {task_info.task_id}: {e}")
                    task_info.status = TaskStatus.FAILED
                    task_info.error_message = str(e)
                    task_info.completed_at = datetime.now()
                
                finally:
                    self.queue.task_done()
                    
            except asyncio.CancelledError:
                logger.info(f"{worker_name} cancelled")
                break
            except Exception as e:
                logger.error(f"{worker_name} error: {e}")
                await asyncio.sleep(1)  # 避免死循环
        
        logger.info(f"{worker_name} stopped")
    
    async def submit_task(
        self,
        task_id: str,
        task_type: str,
        task_func: Callable,
        total_steps: int = 1,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TaskInfo:
        """
        提交新任务到队列
        
        Args:
            task_id: 任务唯一标识
            task_type: 任务类型
            task_func: 任务执行函数 (async)
            total_steps: 总步骤数 (用于进度计算)
            metadata: 元数据
        
        Returns:
            TaskInfo: 任务信息对象
        """
        task_info = TaskInfo(
            task_id=task_id,
            task_type=task_type,
            total_steps=total_steps,
            metadata=metadata or {}
        )
        
        self.tasks[task_id] = task_info
        await self.queue.put((task_func, task_info))
        
        logger.info(f"Submitted task {task_id} ({task_type})")
        return task_info
    
    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """
        获取任务信息
        
        Args:
            task_id: 任务 ID
        
        Returns:
            TaskInfo 或 None
        """
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[TaskInfo]:
        """获取所有任务"""
        return list(self.tasks.values())
    
    def update_progress(self, task_id: str, completed_steps: int):
        """
        更新任务进度
        
        Args:
            task_id: 任务 ID
            completed_steps: 已完成的步骤数
        """
        task_info = self.tasks.get(task_id)
        if task_info and task_info.total_steps > 0:
            task_info.completed_steps = completed_steps
            task_info.progress = completed_steps / task_info.total_steps
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务 ID
        
        Returns:
            bool: 是否成功取消
        """
        task_info = self.tasks.get(task_id)
        if not task_info:
            return False
        
        if task_info.status == TaskStatus.RUNNING:
            # 运行中的任务无法直接取消，需要任务自己检查取消标志
            logger.warning(f"Cannot directly cancel running task {task_id}")
            return False
        
        if task_info.status == TaskStatus.PENDING:
            task_info.status = TaskStatus.CANCELLED
            task_info.completed_at = datetime.now()
            logger.info(f"Cancelled pending task {task_id}")
            return True
        
        return False
    
    async def shutdown(self, timeout: float = 5.0):
        """
        关闭任务队列
        
        Args:
            timeout: 等待超时时间 (秒)
        """
        logger.info("Shutting down TaskQueue...")
        self._shutdown = True
        
        # 发送关闭信号
        for _ in range(self.max_concurrent_tasks):
            await self.queue.put((None, None))
        
        # 等待工作线程完成
        try:
            await asyncio.wait_for(
                asyncio.gather(*self._workers, return_exceptions=True),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning("Timeout waiting for workers to shutdown")
            
            # 强制取消
            for worker in self._workers:
                worker.cancel()
        
        logger.info("TaskQueue shutdown complete")
    
    async def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> TaskInfo:
        """
        等待任务完成
        
        Args:
            task_id: 任务 ID
            timeout: 超时时间 (秒)
        
        Returns:
            TaskInfo: 完成后的任务信息
        
        Raises:
            asyncio.TimeoutError: 超时未完成
        """
        start_time = datetime.now()
        
        while True:
            task_info = self.get_task(task_id)
            if not task_info:
                raise ValueError(f"Task {task_id} not found")
            
            if task_info.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return task_info
            
            if timeout and (datetime.now() - start_time).total_seconds() > timeout:
                raise asyncio.TimeoutError(f"Task {task_id} timeout after {timeout}s")
            
            await asyncio.sleep(0.5)  # 轮询间隔


# 全局任务队列实例
_task_queue: Optional[TaskQueue] = None


def get_task_queue() -> TaskQueue:
    """获取全局任务队列实例"""
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue(max_concurrent_tasks=5)
    return _task_queue


async def shutdown_task_queue():
    """关闭全局任务队列"""
    global _task_queue
    if _task_queue:
        await _task_queue.shutdown()
        _task_queue = None
