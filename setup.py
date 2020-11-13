from setuptools import setup

with open("README.rst") as readme:
    README = readme.read()

setup(
    name="dataclasses",
    version="0.8",
    description="A backport of the dataclasses module for Python 3.6",
    long_description=README,
    url="https://github.com/ericvsmith/dataclasses",
    author="Eric V. Smith",
    author_email="eric@python.org",
    license="Apache",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    packages=["dataclasses"],
    python_requires=">=3.6",
)
