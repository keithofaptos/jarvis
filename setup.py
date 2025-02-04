from setuptools import setup, find_packages

setup(
    name="jarvis-assistant",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pyaudio>=0.2.13",
        "pygame>=2.6.1",
        "SpeechRecognition>=3.10.0",
        "requests>=2.31.0",
        "numpy>=1.24.0",
        "keyboard>=0.13.5",
        "python-dotenv>=1.0.0",
    ],
    include_package_data=True,
    package_data={
        'jarvis': ['sounds/*.mp3', 'sounds/startup.mp3', 'sounds/endapp.mp3'],
    },
    entry_points={
        'console_scripts': [
            'jarvis=jarvis.cli:main',
        ],
    },
    author="Keith Beaudoin",
    author_email="your.email@example.com",  # Update this
    description="JARVIS - A voice-controlled AI assistant",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    url="https://github.com/keithofaptos/jarvis",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)
