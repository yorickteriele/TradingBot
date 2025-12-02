from setuptools import setup, find_packages

setup(
    name="trading_bot",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        line.strip()
        for line in open("requirements.txt")
        if line.strip() and not line.startswith("#") and not line.startswith("-")
    ],
    python_requires=">=3.9",
    author="yorickteriele",
    description="An AI-powered trading bot with news analysis capabilities",
    keywords="trading, ai, news-analysis, finance",
)