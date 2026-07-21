import pytest
import tempfile
import os
import asyncio

from kernel.logger import StructuredLogger, LogLevel


def pytest_addoption(parser):
    parser.addoption("--runslow", action="store_true", default=False, help="run slow tests")


@pytest.fixture(scope="session")
def event_loop_policy():
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture
def test_logger():
    log_dir = tempfile.mkdtemp()
    logger = StructuredLogger(
        name="test",
        level=LogLevel.DEBUG,
        log_dir=log_dir
    )
    yield logger
    import shutil
    shutil.rmtree(log_dir, ignore_errors=True)


@pytest.fixture
def temp_dir():
    dirpath = tempfile.mkdtemp()
    yield dirpath
    import shutil
    shutil.rmtree(dirpath, ignore_errors=True)


@pytest.fixture
def temp_file():
    f = tempfile.NamedTemporaryFile(mode='w', delete=False)
    yield f
    f.close()
    os.unlink(f.name)
