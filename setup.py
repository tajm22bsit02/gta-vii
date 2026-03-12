from setuptools import setup, find_packages

setup(
    name="gta-vii",
    version="0.1.0",
    description="GTA VII - Grand Theft Auto VII Game Implementation",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
    install_requires=[
        "pygame>=2.5.0",
        "numpy>=1.24.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
        ]
    },
)
