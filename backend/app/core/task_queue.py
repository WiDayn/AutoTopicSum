"""任务队列系统"""
import threading
import queue
import time
from typing import Dict, Optional, Callable
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"      # 等待中
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"        # 失败


class Task:
    """任务对象"""
    
    def __init__(self, task_id: str, task_type: str, params: Dict):
        self.task_id = task_id
        self.task_type = task_type
        self.params = params
        self.status = TaskStatus.PENDING
        self.progress = {
            'current': 0,
            'total': 0,
            'message': '等待处理...'
        }
        self.result = None
        self.error = None
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'task_id': self.task_id,
            'task_type': self.task_type,
            'params': self.params,
            'status': self.status.value,
            'progress': self.progress,
            'result': self.result,
            'error': self.error,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


class TaskQueue:
    """任务队列管理器"""
    
    def __init__(self, max_workers: int = 3):
        self.tasks: Dict[str, Task] = {}  # 所有任务
        self.task_queue = queue.Queue()   # 待处理任务队列
        self.max_workers = max_workers
        self.workers = []
        self.handlers: Dict[str, Callable] = {}  # 任务处理器
        self.running = False
        self.lock = threading.Lock()
    
    def register_handler(self, task_type: str, handler: Callable):
        """
        注册任务处理器
        
        Args:
            task_type: 任务类型
            handler: 处理函数，接收 (task, update_progress) 两个参数
        """
        self.handlers[task_type] = handler
        logger.info(f"注册任务处理器: {task_type}")
    
    def submit_task(self, task_id: str, task_type: str, params: Dict) -> Task:
        """
        提交任务
        
        Args:
            task_id: 任务ID
            task_type: 任务类型
            params: 任务参数
            
        Returns:
            Task对象
        """
        task = Task(task_id, task_type, params)
        
        with self.lock:
            self.tasks[task_id] = task
            self.task_queue.put(task)
        
        logger.info(f"任务已提交: {task_id} ({task_type})")
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> list:
        """获取所有任务"""
        with self.lock:
            return list(self.tasks.values())
    
    def start(self):
        """启动工作线程"""
        if self.running:
            return
        
        self.running = True
        for i in range(self.max_workers):
            worker = threading.Thread(
                target=self._worker,
                name=f"TaskWorker-{i}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
        
        logger.info(f"任务队列已启动，工作线程数: {self.max_workers}")
    
    def stop(self):
        """停止工作线程"""
        self.running = False
        logger.info("任务队列已停止")
    
    def _worker(self):
        """工作线程"""
        while self.running:
            try:
                # 获取任务，超时1秒
                task = self.task_queue.get(timeout=1)
                
                # 处理任务
                self._process_task(task)
                
                self.task_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"工作线程错误: {str(e)}")
    
    def _process_task(self, task: Task):
        """
        处理任务
        
        Args:
            task: 任务对象
        """
        try:
            # 更新状态为处理中
            task.status = TaskStatus.PROCESSING
            task.started_at = datetime.now()
            
            # 获取处理器
            handler = self.handlers.get(task.task_type)
            if not handler:
                raise ValueError(f"未找到任务类型 {task.task_type} 的处理器")
            
            # 创建进度更新函数
            def update_progress(current: int, total: int, message: str = ""):
                task.progress = {
                    'current': current,
                    'total': total,
                    'message': message
                }
            
            # 执行处理器
            logger.info(f"开始处理任务: {task.task_id}")
            result = handler(task, update_progress)
            
            # 更新结果
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            
            logger.info(f"任务完成: {task.task_id}")
            
        except Exception as e:
            logger.error(f"任务失败: {task.task_id}, 错误: {str(e)}")
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()


# 全局任务队列实例
task_queue = TaskQueue(max_workers=3)

