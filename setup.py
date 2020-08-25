import setuptools

long_description="Flint is a Fortran lint tool. It is not yet working, but can currently do some basic tasks. It is currently written as a Python module, but I expect it will use command line tools someday. Flint is not exactly useable at the moment, but it does contain some decent functionality, and has been integrated into a few projects at a very basic level. Currently, tokenization is good, and several very large projects are correctly tokenized. But analysis is still rather weak, and would benefit from feedback from any brave users."

setuptools.setup(
    name="flint",
    version="0.0.1",
    author="Marshall Ward",
    author_email="marshal.ward@gmail.com",
    description="A fortran lint tool",
    long_description=long_description,
    url="https://github.com/marshallward/flint",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
