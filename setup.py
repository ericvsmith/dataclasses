from setuptools import setup

with open('README.rst') as readme:
    README = readme.read()

setup(
    name='dataclasses',
    version='0.5+',
    description='An implementation of PEP 557: Data Classes',
    long_description=README,
    url='https://github.com/ericvsmith/dataclasses',
    author='Eric V. Smith',
    author_email='eric@python.org',
    license='Apache',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3.6',
    ],
    py_modules=['dataclasses']
)
