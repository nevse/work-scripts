import setuptools

setuptools.setup(
    name="devtools-pkg",
    version="0.0.4",
    author="EN",
    author_email="nevse@gmail.com",
    description="devtools-pkg",
    url="https://github.com/nevse/work-scripts",
    project_urls={
        "Bug Tracker": "https://github.com/nevse/work-scripts/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    packages=setuptools.find_packages(where="scripts"),
    python_requires=">=3.6",
    scripts=["scripts/conv", "scripts/conv.py"]
)