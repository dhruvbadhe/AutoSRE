from setuptools import setup, find_packages

setup(
    name="autosre-agent",
    version="1.0.1",
    description="⚡ AutoSRE: Autonomous Incident Response Agent powered by Corrective RAG (CRAG) & Multi-Index Hybrid Search",
    author="Dhruv Badhe",
    packages=find_packages(),
    install_requires=[
        "typer>=0.12.0",
        "rich>=13.7.0",
        "httpx>=0.27.0"
    ],
    entry_points={
        "console_scripts": [
            "autosre=app.cli:app",
        ],
    },
    python_requires=">=3.9",
)
