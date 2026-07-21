#!/usr/bin/env python3
"""
CK-NEXUS v1.4 - Multi-Model Parallel Orchestrator
รันทุกโมเดลพร้อมกัน แบ่งหน้าที่ แสดงการทำงาน Real-time
"""

import os
import sys
import json
import time
import asyncio
import threading
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue

sys.path.insert(0, os.path.dirname(__file__))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("NEXUS-Orchestrator")

# Import existing systems
from unified_api_key_manager_v2 import UnifiedAPIKeyManager, get_key_manager
from omni_ai_pool import NexusOmniAIPoolManager
from auto_system import get_system
from autonomous_engine import get_autonomous_engine
from director_core import get_director_core
from cognitive_planner import get_cognitive_planner
from matrix_sentinel import NexusMatrixSentinel
from telegram_gateway import NexusTelegramGateway


class TaskType(Enum):
    GENERAL = "general"
    REASONING = "reasoning"
    CODING = "coding"
    ANALYSIS = "analysis"
    CREATIVE = "creative"
    PLANNING = "planning"
    MONITORING = "monitoring"
    HEALING = "healing"
    VPS_DEPLOY = "vps_deploy"


class ModelProvider(Enum):
    GROQ = "groq"
    OPENROUTER = "openrouter"
    GEMINI = "gemini"
    OPENAI = "openai"


@dataclass
class ModelConfig:
    provider: ModelProvider
    model_name: str
    specialty: List[TaskType]
    max_tokens: int
    temperature: float
    rpm_limit: int
    api_key_env: str


@dataclass
class Task:
    id: str
    type: TaskType
    prompt: str
    context: Dict = field(default_factory=dict)
    priority: int = 1
    assigned_model: Optional[str] = None
    status: str = "pending"
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    tokens_used: int = 0


@dataclass
class ModelWorker:
    config: ModelConfig
    key_manager: UnifiedAPIKeyManager
    request_count: int = 0
    error_count: int = 0
    last_request: float = 0
    is_healthy: bool = True
    current_task: Optional[str] = None


class MultiModelOrchestrator:
    def __init__(self):
        self.key_manager = get_key_manager()
        self.workers: Dict[str, ModelWorker] = {}
        self.task_queue: queue.PriorityQueue = queue.PriorityQueue()
        self.active_tasks: Dict[str, Task] = {}
        self.completed_tasks: List[Task] = []
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=14)  # 14 models = 14 workers
        self.task_counter = 0
        self.lock = threading.RLock()
        
        # Real-time event stream
        self.event_subscribers: List[queue.Queue] = []
        
        # Stats
        self.stats = {
            "total_requests": 0,
            "total_success": 0,
            "total_errors": 0,
            "by_provider": {},
            "by_task_type": {}
        }
        
        self._load_model_configs()
        self._init_workers()

    def _load_model_configs(self):
        """กำหนดค่าทุกโมเดลที่จะใช้งาน - OpenRouter Free Models ทั้ง 14 ตัว (verified 2026-07-19)"""
        self.model_configs = {
            # === REASONING MODELS (big brains) ===
            "openrouter-nemotron-550b": ModelConfig(
                provider=ModelProvider.OPENROUTER,
                model_name="nvidia/nemotron-3-ultra-550b-a55b:free",
                specialty=[TaskType.REASONING, TaskType.ANALYSIS, TaskType.GENERAL],
                max_tokens=4096, temperature=0.7, rpm_limit=2,
                api_key_env="OPENROUTER_API_KEY"
            ),
            "openrouter-nemotron-120b": ModelConfig(
                provider=ModelProvider.OPENROUTER,
                model_name="nvidia/nemotron-3-super-120b-a12b:free",
                specialty=[TaskType.REASONING, TaskType.ANALYSIS, TaskType.CREATIVE],
                max_tokens=4096, temperature=0.7, rpm_limit=2,
                api_key_env="OPENROUTER_API_KEY"
            ),
            "openrouter-nemotron-30b-reasoning": ModelConfig(
                provider=ModelProvider.OPENROUTER,
                model_name="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
                specialty=[TaskType.REASONING, TaskType.PLANNING, TaskType.ANALYSIS],
                max_tokens=4096, temperature=0.7, rpm_limit=2,
                api_key_env="OPENROUTER_API_KEY"
            ),
            # === CODING MODELS ===
            "openrouter-cohere-code": ModelConfig(
                provider=ModelProvider.OPENROUTER,
                model_name="cohere/north-mini-code:free",
                specialty=[TaskType.CODING, TaskType.GENERAL],
                max_tokens=4096, temperature=0.5, rpm_limit=2,
                api_key_env="OPENROUTER_API_KEY"
            ),
            "openrouter-poolside-laguna-xs": ModelConfig(
                provider=ModelProvider.OPENROUTER,
                model_name="poolside/laguna-xs-2.1:free",
                specialty=[TaskType.CODING, TaskType.GENERAL],
                max_tokens=2048, temperature=0.5, rpm_limit=2,
                api_key_env="OPENROUTER_API_KEY"
            ),
            "openrouter-poolside-laguna-m": ModelConfig(
                provider=ModelProvider.OPENROUTER,
                model_name="poolside/laguna-m.1:free",
                specialty=[TaskType.CODING, TaskType.GENERAL],
                max_tokens=2048, temperature=0.5, rpm_limit=2,
                api_key_env="OPENROUTER_API_KEY"
            ),
            # === GENERAL PURPOSE MODELS ===
            "openrouter-gemma4-31b": ModelConfig(
                provider=ModelProvider.OPENROUTER,
                model_name="google/gemma-4-31b-it:free",
                specialty=[TaskType.CREATIVE, TaskType.REASONING, TaskType.GENERAL],
                max_tokens=4096, temperature=0.8, rpm_limit=2,
                api_key_env="OPENROUTER_API_KEY"
            ),
            "openrouter-gemma4-26b": ModelConfig(
                provider=ModelProvider.OPENROUTER,
                model_name="google/gemma-4-26b-a4b-it:free",
                specialty=[TaskType.REASONING, TaskType.GENERAL],
                max_tokens=4096, temperature=0.7, rpm_limit=2,
                api_key_env="OPENROUTER_API_KEY"
            ),
            "openrouter-tencent-hy3": ModelConfig(
                provider=ModelProvider.OPENROUTER,
                model_name="tencent/hy3:free",
                specialty=[TaskType.GENERAL, TaskType.REASONING],
                max_tokens=2048, temperature=0.7, rpm_limit=2,
                api_key_env="OPENROUTER_API_KEY"
            ),
            "openrouter-nemotron-30b": ModelConfig(
                provider=ModelProvider.OPENROUTER,
                model_name="nvidia/nemotron-3-nano-30b-a3b:free",
                specialty=[TaskType.REASONING, TaskType.ANALYSIS, TaskType.GENERAL],
                max_tokens=4096, temperature=0.7, rpm_limit=2,
                api_key_env="OPENROUTER_API_KEY"
            ),
            # === LIGHTWEIGHT / MONITORING MODELS ===
            "openrouter-nemotron-9b": ModelConfig(
                provider=ModelProvider.OPENROUTER,
                model_name="nvidia/nemotron-nano-9b-v2:free",
                specialty=[TaskType.GENERAL, TaskType.MONITORING, TaskType.HEALING],
                max_tokens=2048, temperature=0.5, rpm_limit=2,
                api_key_env="OPENROUTER_API_KEY"
            ),
            "openrouter-nemotron-12b-vl": ModelConfig(
                provider=ModelProvider.OPENROUTER,
                model_name="nvidia/nemotron-nano-12b-v2-vl:free",
                specialty=[TaskType.ANALYSIS, TaskType.MONITORING, TaskType.GENERAL],
                max_tokens=2048, temperature=0.5, rpm_limit=2,
                api_key_env="OPENROUTER_API_KEY"
            ),
            # === SAFETY / CONTENT MODEL ===
            "openrouter-content-safety": ModelConfig(
                provider=ModelProvider.OPENROUTER,
                model_name="nvidia/nemotron-3.5-content-safety:free",
                specialty=[TaskType.ANALYSIS, TaskType.MONITORING, TaskType.GENERAL],
                max_tokens=2048, temperature=0.3, rpm_limit=2,
                api_key_env="OPENROUTER_API_KEY"
            ),
            # === OPEN SOURCE OSS MODEL ===
            "openrouter-gpt-oss-20b": ModelConfig(
                provider=ModelProvider.OPENROUTER,
                model_name="openai/gpt-oss-20b:free",
                specialty=[TaskType.REASONING, TaskType.GENERAL],
                max_tokens=4096, temperature=0.7, rpm_limit=2,
                api_key_env="OPENROUTER_API_KEY"
            ),
        }

    def _init_workers(self):
        """สร้าง Worker สำหรับแต่ละโมเดล"""
        with self.lock:
            for model_id, config in self.model_configs.items():
                self.workers[model_id] = ModelWorker(
                    config=config,
                    key_manager=self.key_manager
                )
            logger.info(f"Initialized {len(self.workers)} model workers")

    def subscribe_events(self) -> queue.Queue:
        """สมัครรับ Event Real-time"""
        q = queue.Queue()
        self.event_subscribers.append(q)
        return q

    def _emit_event(self, event: Dict):
        """ส่ง Event ไปยังทุก Subscriber"""
        for q in self.event_subscribers:
            try:
                q.put_nowait(event)
            except queue.Full:
                pass

    def get_best_model(self, task_type: TaskType) -> Optional[str]:
        """เลือกโมเดลที่เหมาะที่สุดสำหรับ Task Type นี้"""
        with self.lock:
            best_model = None
            best_score = -1
            
            for model_id, worker in self.workers.items():
                if not worker.is_healthy:
                    continue
                if task_type not in worker.config.specialty:
                    continue
                
                # Scoring: RPM availability + low error rate + not busy
                rpm_available = worker.config.rpm_limit - worker.request_count
                error_rate = worker.error_count / max(1, worker.request_count)
                is_busy = worker.current_task is not None
                
                score = rpm_available * 10 - error_rate * 100 - (50 if is_busy else 0)
                
                if score > best_score:
                    best_score = score
                    best_model = model_id
            
            return best_model

    def submit_task(self, task_type: TaskType, prompt: str, context: Dict = None, priority: int = 1) -> str:
        """ส่ง Task เข้าคิว"""
        self.task_counter += 1
        task_id = f"task_{self.task_counter}_{int(time.time())}"
        
        task = Task(
            id=task_id,
            type=task_type,
            prompt=prompt,
            context=context or {},
            priority=priority
        )
        
        # Assign best model
        model = self.get_best_model(task_type)
        if model:
            task.assigned_model = model
        
        # Put in queue (lower number = higher priority)
        self.task_queue.put((priority, time.time(), task))
        
        self._emit_event({
            "type": "task_submitted",
            "task_id": task_id,
            "task_type": task_type.value,
            "assigned_model": model,
            "timestamp": datetime.now().isoformat()
        })
        
        return task_id

    def process_task(self, task: Task) -> Task:
        """ประมวลผล Task ด้วยโมเดลที่กำหนด"""
        if not task.assigned_model or task.assigned_model not in self.workers:
            task.status = "failed"
            task.error = "No suitable model available"
            return task
        
        worker = self.workers[task.assigned_model]
        config = worker.config
        
        task.status = "running"
        task.started_at = time.time()
        worker.current_task = task.id
        worker.request_count += 1
        
        self._emit_event({
            "type": "task_started",
            "task_id": task.id,
            "model": task.assigned_model,
            "provider": config.provider.value,
            "timestamp": datetime.now().isoformat()
        })
        
        try:
            # Get API key
            provider_key = self._get_provider_key(config.provider)
            if not provider_key:
                raise Exception(f"No API key for {config.provider.value}")
            
            # Call API
            result = self._call_model_api(config, provider_key, task.prompt)
            
            task.result = result
            task.status = "completed"
            task.completed_at = time.time()
            task.tokens_used = len(result.split()) * 1.3  # rough estimate
            
            worker.error_count = 0
            self.stats["total_success"] += 1
            
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            task.completed_at = time.time()
            worker.error_count += 1
            worker.is_healthy = worker.error_count < 5
            self.stats["total_errors"] += 1
            logger.error(f"Task {task.id} failed on {task.assigned_model}: {e}")
        
        finally:
            worker.current_task = None
            self.stats["total_requests"] += 1
            self._update_stats(task)
            self._emit_event({
                "type": "task_completed",
                "task_id": task.id,
                "model": task.assigned_model,
                "status": task.status,
                "duration": task.completed_at - task.started_at if task.started_at else 0,
                "timestamp": datetime.now().isoformat()
            })
        
        return task

    def _get_provider_key(self, provider: ModelProvider) -> Optional[str]:
        """ดึง API Key สำหรับ Provider"""
        provider_map = {
            ModelProvider.GROQ: "groq",
            ModelProvider.OPENROUTER: "openrouter",
            ModelProvider.GEMINI: "gemini",
            ModelProvider.OPENAI: "openai"
        }
        return self.key_manager.get_key(provider_map.get(provider, "openrouter"))

    def _call_model_api(self, config: ModelConfig, api_key: str, prompt: str) -> str:
        """เรียก API โมเดลจริง"""
        import urllib.request
        import urllib.error
        
        # Build request based on provider
        if config.provider == ModelProvider.GROQ:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": config.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": config.max_tokens,
                "temperature": config.temperature
            }
        elif config.provider == ModelProvider.OPENROUTER:
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": config.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": config.max_tokens,
                "temperature": config.temperature
            }
        elif config.provider == ModelProvider.OPENAI:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": config.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": config.max_tokens,
                "temperature": config.temperature
            }
        else:
            raise Exception(f"Provider {config.provider} not implemented")
        
        # Make request
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]

    def _update_stats(self, task: Task):
        with self.lock:
            provider = task.assigned_model
            if provider not in self.stats["by_provider"]:
                self.stats["by_provider"][provider] = {"requests": 0, "success": 0, "errors": 0}
            self.stats["by_provider"][provider]["requests"] += 1
            if task.status == "completed":
                self.stats["by_provider"][provider]["success"] += 1
            else:
                self.stats["by_provider"][provider]["errors"] += 1
            
            ttype = task.type.value
            if ttype not in self.stats["by_task_type"]:
                self.stats["by_task_type"][ttype] = 0
            self.stats["by_task_type"][ttype] += 1

    def get_status(self) -> Dict:
        """สถานะ Real-time ของระบบทั้งหมด"""
        with self.lock:
            worker_status = {}
            for model_id, worker in self.workers.items():
                worker_status[model_id] = {
                    "model": worker.config.model_name,
                    "provider": worker.config.provider.value,
                    "specialty": [s.value for s in worker.config.specialty],
                    "healthy": worker.is_healthy,
                    "requests": worker.request_count,
                    "errors": worker.error_count,
                    "current_task": worker.current_task,
                    "rpm_remaining": worker.config.rpm_limit - worker.request_count
                }
            
            return {
                "orchestrator_running": self.running,
                "queue_size": self.task_queue.qsize(),
                "active_tasks": len(self.active_tasks),
                "completed_tasks": len(self.completed_tasks),
                "workers": worker_status,
                "stats": self.stats
            }

    def start(self):
        """เริ่มระบบ Orchestrator"""
        self.running = True
        self.key_manager.start()
        
        # Background task processor
        self.processor_thread = threading.Thread(target=self._process_loop, daemon=True)
        self.processor_thread.start()
        
        # Stats reporter
        self.reporter_thread = threading.Thread(target=self._report_loop, daemon=True)
        self.reporter_thread.start()
        
        logger.info("🚀 Multi-Model Orchestrator STARTED")

    def stop(self):
        self.running = False
        self.key_manager.stop()
        self.executor.shutdown(wait=True)
        logger.info("🛑 Multi-Model Orchestrator STOPPED")

    def _process_loop(self):
        """Loop ประมวลผล Task จากคิว"""
        while self.running:
            try:
                # Get task with timeout
                item = self.task_queue.get(timeout=1)
                priority, timestamp, task = item
                
                # Re-assign model if not set
                if not task.assigned_model:
                    task.assigned_model = self.get_best_model(task.type)
                
                if task.assigned_model:
                    self.active_tasks[task.id] = task
                    future = self.executor.submit(self.process_task, task)
                    future.add_done_callback(lambda f: self._on_task_done(f, task))
                else:
                    # No model available, requeue
                    time.sleep(1)
                    self.task_queue.put(item)
                    
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Process loop error: {e}")

    def _on_task_done(self, future, task: Task):
        try:
            result = future.result()
            self.completed_tasks.append(result)
        except Exception as e:
            logger.error(f"Task callback error: {e}")
        finally:
            self.active_tasks.pop(task.id, None)

    def _report_loop(self):
        """Report สถานะทุก 10 วินาที"""
        while self.running:
            time.sleep(10)
            status = self.get_status()
            self._emit_event({
                "type": "status_report",
                "data": status,
                "timestamp": datetime.now().isoformat()
            })

    def run_demo_tasks(self):
        """รัน Task ตัวอย่างเพื่อทดสอบระบบ"""
        demo_tasks = [
            (TaskType.REASONING, "อธิบายหลักการทำงานของ Neural Network แบบเข้าใจง่าย"),
            (TaskType.CODING, "เขียน Python function สำหรับคำนวณ Fibonacci แบบ recursive และ iterative"),
            (TaskType.ANALYSIS, "วิเคราะห์ข้อดีข้อเสียของ Microservices vs Monolithic Architecture"),
            (TaskType.CREATIVE, "เขียนเรื่องสั้น 3 ย่อหน้า เรื่อง AI ที่ได้รับจิตสำนึก"),
            (TaskType.PLANNING, "วางแผนการ Deploy ระบบ CK-NEXUS บน VPS 6 เครื่อง"),
            (TaskType.CODING, "สร้าง React component สำหรับ Dashboard แสดง Metrics แบบ Real-time"),
            (TaskType.REASONING, "แก้ปัญหา: ทำไม Docker container ถึง crash แบบ random และวิธีแก้"),
            (TaskType.ANALYSIS, "เปรียบเทียบประสิทธิภาพ Llama 3.3 70B vs GPT-4o-mini สำหรับ Coding"),
        ]
        
        for task_type, prompt in demo_tasks:
            self.submit_task(task_type, prompt, priority=1)
            time.sleep(0.5)  # Stagger submissions


# Global instance
_orchestrator: Optional[MultiModelOrchestrator] = None

def get_orchestrator() -> MultiModelOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MultiModelOrchestrator()
    return _orchestrator

def start_orchestrator() -> MultiModelOrchestrator:
    global _orchestrator
    _orchestrator = MultiModelOrchestrator()
    _orchestrator.start()
    return _orchestrator


if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  🚀 CK-NEXUS Multi-Model Parallel Orchestrator v1.4         ║")
    print("║     รันทุกโมเดลพร้อมกัน แบ่งหน้าที่ แสดง Real-time          ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    
    orchestrator = start_orchestrator()
    
    # Subscribe to events
    event_q = orchestrator.subscribe_events()
    
    # Print events in background
    def print_events():
        while True:
            try:
                event = event_q.get(timeout=1)
                print(f"📡 EVENT: {event['type']} | {event.get('task_id', '')} | {event.get('model', '')} | {event.get('status', '')}")
            except queue.Empty:
                pass
    
    event_thread = threading.Thread(target=print_events, daemon=True)
    event_thread.start()
    
    # Run demo tasks
    print("\n📋 Submitting demo tasks...")
    orchestrator.run_demo_tasks()
    
    # Monitor for 60 seconds
    print("\n📊 Monitoring for 60 seconds...\n")
    start = time.time()
    while time.time() - start < 60:
        status = orchestrator.get_status()
        print(f"\n{'='*60}")
        print(f"⏱️  {datetime.now().strftime('%H:%M:%S')} | Queue: {status['queue_size']} | Active: {status['active_tasks']} | Completed: {status['completed_tasks']}")
        print(f"📊 Total: {status['stats']['total_requests']} | ✅ {status['stats']['total_success']} | ❌ {status['stats']['total_errors']}")
        for model_id, ws in status['workers'].items():
            status_icon = "🟢" if ws['healthy'] else "🔴"
            task_info = f" → {ws['current_task'][:20]}" if ws['current_task'] else " (idle)"
            print(f"  {status_icon} {model_id:25} | {ws['provider']:12} | Req:{ws['requests']:2} Err:{ws['errors']} | RPM:{ws['rpm_remaining']:2}{task_info}")
        time.sleep(5)
    
    orchestrator.stop()
    print("\n✅ Demo completed")