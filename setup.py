import setuptools

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setuptools.setup(
    name="daizy-bot",
    version="0.1",
    author="Artalus",
    description="A VK bot to forward messages from Twitter",
    url="https://github.com/Artalus/daizybot",
    packages=setuptools.find_packages(),
    python_requires='>=3.6',
    install_requires=requirements,
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Console",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.6",
    ],


    entry_points={
        'console_scripts': [
            'daizy=daizy.daizy:main'
        ],
    },
)
