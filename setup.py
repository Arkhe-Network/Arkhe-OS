from setuptools import setup, find_packages

setup(
    name="arkhe-os-substrates",
    version="5.6.0",
    description="ARKHE OMEGA-TEMP v5.6.0 — Cathedral Operating System",
    author="Rafael Oliveira",
    author_email="rafael@safecore.ai",
    url="https://safecore.ai/arkhe",
    packages=find_packages(),
    install_requires=[
        "pytest>=7.0.0",
        "pytest-asyncio>=0.21.0",
        "PyJWT>=2.0.0",
        "cryptography>=3.0",
        "requests>=2.25.0",
        "flask>=2.0.0",
    ],
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "arkhe=arkhe_cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
