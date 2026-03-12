"""Setup configuration for cli-anything-touchdesigner."""

from setuptools import setup, find_packages

setup(
    name="cli-anything-touchdesigner",
    version="1.0.0",
    description="TouchDesigner CLI for AI Agents — part of the CLI-Anything ecosystem",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="CLI-Anything Contributors",
    license="MIT",
    python_requires=">=3.9",
    packages=find_packages(),
    install_requires=[
        "click>=8.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "cli-anything-touchdesigner=cli_anything_touchdesigner.cli:main",
            "td-cli=cli_anything_touchdesigner.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Software Development :: Libraries",
    ],
    keywords="touchdesigner cli agent ai automation vfx",
)
