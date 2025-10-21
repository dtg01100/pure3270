from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pure3270",
    version="0.3.1",
    author="Pure3270 Developers",
    description="Pure Python 3270 emulator",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[],
    extras_require={
        "dev": [
            "pytest >= 7.0",
            "pytest-asyncio >= 0.21",
            "pytest-benchmark >= 4.0",
            "pytest-cov >= 5.0",
            "flake8 >= 7.0",
            "black >= 24.0",
            "isort >= 5.13",
        ],
        "test": [
            "pytest >= 7.0",
            "pytest-asyncio >= 0.21",
            "pytest-benchmark >= 4.0",
            "pytest-cov >= 5.0",
            "flake8 >= 7.0",
            "black >= 24.0",
            "isort >= 5.13",
        ],
    },
    python_requires=">=3.10",
    classifiers=[
        "Programming Language :: Python :: 3",
        # Dropped Python 3.9 support
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
