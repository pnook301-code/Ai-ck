"""CK-NEXUS AIOS — pip install packaging."""
from setuptools import setup, find_packages
import os

here = os.path.abspath(os.path.dirname(__file__))
version = {}
with open(os.path.join(here, "ck_nexus_cli", "__init__.py")) as f:
    exec(f.read(), version)

setup(
    name="ck-nexus-aios",
    version=version.get("__version__", "1.0.0"),
    description="CK-NEXUS Enterprise AI Operating System",
    long_description=open(os.path.join(here, "README.md")).read() if os.path.exists(os.path.join(here, "README.md")) else "",
    long_description_content_type="text/markdown",
    author="CK-NEXUS Team",
    license="Proprietary",
    packages=find_packages(exclude=["tests*", "tests.*"]),
    python_requires=">=3.11",
    install_requires=["uvicorn", "fastapi"],
    extras_require={"dev": ["pytest", "pytest-asyncio", "ruff"], "video": ["opencv-python-headless", "faster-whisper"]},
    entry_points={"console_scripts": ["ck-nexus=ck_nexus_cli.main:main"]},
    classifiers=["Development Status :: 4 - Beta", "Programming Language :: Python :: 3.12", "Topic :: Software Development :: Libraries :: Application Frameworks"],
)
