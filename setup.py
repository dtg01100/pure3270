from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pure3270",
    version="0.2.0",
    author="Pure3270 Developers",
    description="Pure Python 3270 emulator",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[],
    extras_require={
        "dev": ["pytest >= 7.0", "pytest-asyncio >= 0.21", "pytest-benchmark >= 4.0"],
        "test": ["pytest >= 7.0", "pytest-asyncio >= 0.21", "pytest-benchmark >= 4.0"],
    },
    python_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
