import asyncio
import pytest
from kernel.scheduler import TaskScheduler, ScheduledTask


class TestScheduledTask:
    def test_defaults(self):
        t = ScheduledTask(name="test", interval=60, callback=lambda: None)
        assert t.enabled is True
        assert t.run_immediately is False
        assert t.max_executions is None
        assert t._execution_count == 0

    def test_with_all_options(self):
        t = ScheduledTask(
            name="test", interval=10, callback=lambda: None,
            run_immediately=True, max_executions=5,
            metadata={"type": "recurring"}
        )
        assert t.run_immediately is True
        assert t.max_executions == 5
        assert t.metadata["type"] == "recurring"


class TestTaskScheduler:
    @pytest.mark.asyncio
    async def test_register_task(self):
        scheduler = TaskScheduler()
        task = ScheduledTask(name="test", interval=60, callback=lambda: None)
        scheduler.register(task)
        assert len(scheduler.get_tasks()) == 1

    @pytest.mark.asyncio
    async def test_add_returns_id(self):
        scheduler = TaskScheduler()
        task_id = scheduler.add("test", 60, lambda: None)
        assert task_id is not None
        assert scheduler.get_task(task_id) is not None

    @pytest.mark.asyncio
    async def test_unregister(self):
        scheduler = TaskScheduler()
        task_id = scheduler.add("test", 60, lambda: None)
        scheduler.unregister(task_id)
        assert scheduler.get_task(task_id) is None

    @pytest.mark.asyncio
    async def test_task_execution(self):
        scheduler = TaskScheduler()
        executed = []

        async def my_task():
            executed.append("ran")

        task_id = scheduler.add("test", 0.05, my_task, run_immediately=True)
        scheduler.start()
        await asyncio.sleep(0.1)
        await scheduler.stop()
        assert len(executed) >= 1

    @pytest.mark.asyncio
    async def test_task_with_max_executions(self):
        scheduler = TaskScheduler()
        count = 0

        def my_task():
            nonlocal count
            count += 1

        scheduler.add("limited", 0.01, my_task, max_executions=3, run_immediately=True)
        scheduler.start()
        await asyncio.sleep(0.15)
        await scheduler.stop()
        assert count >= 1

    @pytest.mark.asyncio
    async def test_pause_and_resume(self):
        scheduler = TaskScheduler()
        executed = []

        async def my_task():
            executed.append("ran")

        task_id = scheduler.add("test", 0.01, my_task, run_immediately=True)
        scheduler.pause(task_id)
        scheduler.start()
        await asyncio.sleep(0.15)
        assert len(executed) == 0
        scheduler.resume(task_id)
        await asyncio.sleep(1.5)
        await scheduler.stop()
        assert len(executed) >= 1

    @pytest.mark.asyncio
    async def test_double_start_noop(self):
        scheduler = TaskScheduler()
        scheduler.start()
        scheduler.start()
        await scheduler.stop()

    @pytest.mark.asyncio
    async def test_summary(self):
        scheduler = TaskScheduler()
        scheduler.add("test", 60, lambda: None)
        summary = scheduler.summary()
        assert summary["total"] == 1
        assert summary["enabled"] == 1
        assert summary["running"] is False

    @pytest.mark.asyncio
    async def test_task_error_does_not_crash(self):
        scheduler = TaskScheduler()

        def failing():
            raise ValueError("task error")

        async def good():
            pass

        scheduler.add("bad", 0.01, failing, run_immediately=True)
        scheduler.add("good", 0.01, good, run_immediately=True)
        scheduler.start()
        await asyncio.sleep(0.1)
        await scheduler.stop()

    @pytest.mark.asyncio
    async def test_sync_callback(self):
        scheduler = TaskScheduler()
        executed = []

        def sync_task():
            executed.append("sync")

        scheduler.add("sync", 0.01, sync_task, run_immediately=True)
        scheduler.start()
        await asyncio.sleep(0.05)
        await scheduler.stop()
        assert len(executed) >= 1

    @pytest.mark.asyncio
    async def test_disabled_task_not_executed(self):
        scheduler = TaskScheduler()
        executed = []

        async def task():
            executed.append("ran")

        t = ScheduledTask(name="disabled", interval=0.01, callback=task, enabled=False)
        scheduler.register(t)
        scheduler.start()
        await asyncio.sleep(0.1)
        await scheduler.stop()
        assert len(executed) == 0
