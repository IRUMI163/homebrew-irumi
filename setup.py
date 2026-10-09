from setuptools import setup

setup(
    name="irumi",
    version="1.0.0",
    description="日本語語順スクリプト言語 IRUMI",
    py_modules=["irumi"],
    entry_points={
        "console_scripts": [
            "irumi=irumi:main",
        ],
    },
)
