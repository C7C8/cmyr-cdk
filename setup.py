import setuptools


with open("README.md") as fp:
    long_description = fp.read()

setuptools.setup(
    name="c7c8-cdk",
    version="0.0.1",

    description="CDK setup for everything I (cmyr) own",
    long_description=long_description,
    long_description_content_type="text/markdown",

    author="author",

    package_dir={"": "aws"},
    packages=setuptools.find_packages(where="aws"),

    install_requires=[
        "aws-aws.core==1.91.0",
    ],

    python_requires=">=3.6",

    classifiers=[
        "Development Status :: 1 - Beta",

        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",

        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",

        "Typing :: Typed",
    ],
)
