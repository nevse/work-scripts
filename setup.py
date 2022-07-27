import setuptools

setuptools.setup(
    name="project-conv-nevse",
    version="0.0.14",
    author="EN",
    author_email="nevse@gmail.com",
    description="csrpoj packagereference converter",
    long_description_content_type='text/markdown',
    url="https://github.com/nevse/work-scripts",
    project_urls={
        "Bug Tracker": "https://github.com/nevse/work-scripts/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
    entry_points={
        'console_scripts': [
            'conv=conv_package.conv:main',
        ],
    }    
)