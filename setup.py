#!/usr/bin/env python3

from setuptools import setup


setup(
    name="deepplan",
    version="0.5.0",
    description="A local, agent-friendly planning kernel with a thin Python SDK surface.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="LEE Kyungjae",
    license="MIT",
    python_requires=">=3.9",
    py_modules=[
        "deepplan",
        "deepplan_agent",
        "deepplan_client",
        "deepplan_server",
        "deepplan_store",
    ],
    packages=["deepplan_sdk"],
)
