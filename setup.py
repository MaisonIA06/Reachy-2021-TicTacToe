"""
Setup pour reachy_tictactoe adapté pour Reachy SDK 2021
"""
from setuptools import setup, find_packages
from os import path
import io 

here = path.abspath(path.dirname(__file__))

with io.open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


setup(
    name='reachy_tictactoe_2021',
    version='2.0.0',
    description='TicTacToe playground for Reachy robot (SDK 2021)',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/MaisonIA06/Reachy-2021-TicTacToe',
    author='MaisonIA06',
    author_email='wnaiji@maison-intelligence-artificielle.com',
    packages=find_packages(exclude=['tests']),
    python_requires='>=3.8',
    install_requires=[
        'numpy>=1.19.0,<2',  # NumPy 2.x incompatible avec la stack TFLite
        'zzlog>=1.0.0',
        'reachy-sdk>=0.7.0',  # SDK Reachy 2021
        'opencv-python>=4.5.0',
        'Pillow>=8.0.0',
        'pyquaternion>=0.9.0',
        # Interface web de pilotage (python -m reachy_tictactoe.webapp)
        'fastapi>=0.110',
        'uvicorn>=0.27',
    ],
    extras_require={
        'vision': [
            'tflite-runtime>=2.5.0',  # Pour la vision avec TensorFlow Lite
        ],
        'dev': [
            'pytest>=6.0.0',
            'flake8>=3.8.0',
        ],
    },
    package_data={
        'reachy_tictactoe': [
            'models/*.tflite',
            'models/*.txt',
            'moves/*.npz',
            'sounds/*.mp3',
            'Q-value.npz',
            # Page et assets de l'interface web : sans eux, StaticFiles
            # échoue au démarrage après un pip install non éditable.
            'webapp/static/*',
        ],
    },
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'reachy-tictactoe=reachy_tictactoe.game_launcher:main',
            'reachy-tictactoe-web=reachy_tictactoe.webapp.__main__:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'Topic :: Scientific/Engineering :: Robotics',
    ],
)
