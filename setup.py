from setuptools import setup
from cli import CLI

setup(
    name=CLI,
    version="0.1",
    py_modules="cli",
    install_requires=[
        "Click",
    ],
    entry_points=f"""
        [console_scripts]
        {CLI}=cli:cli
    """,
)
