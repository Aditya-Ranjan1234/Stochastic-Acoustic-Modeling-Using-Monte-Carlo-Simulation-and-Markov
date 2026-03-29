<!--
SPDX-FileCopyrightText: Copyright (c) 2021-2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
SPDX-License-Identifier: Apache-2.0
-->
# Sionna AcoustiX: An Open-Source Library for Acosutic Simulation

Sionna-AcoustiX; is an open-source Python library for acosutic impulse response simulation built on top of the open-source software library [TensorFlow](https://www.tensorflow.org) for machine learning.

The official documentation can be found [here](https://nvlabs.github.io/sionna/).

## Installation

Sionna requires [Python](https://www.python.org/) and [Tensorflow](https://www.tensorflow.org/).
In order to run the tutorial notebooks on your machine, you also need [JupyterLab](https://jupyter.org/).
You can alternatively test them on [Google Colab](https://colab.research.google.com/).
Although not necessary, we recommend running Sionna in a [Docker container](https://www.docker.com).

Sionna requires [TensorFlow 2.13-2.15](https://www.tensorflow.org/install) and Python 3.8-3.11. We recommend Ubuntu 22.04. Earlier versions of TensorFlow may still work but are not recommended because of known, unpatched CVEs.

To run the ray tracer on CPU, [LLVM](https://llvm.org) is required by DrJit.  Please check the [installation instructions for the LLVM backend](https://drjit.readthedocs.io/en/latest/firststeps-py.html#llvm-backend). 

We refer to the [TensorFlow GPU support tutorial](https://www.tensorflow.org/install/gpu) for GPU support and the required driver setup.

### Installation using pip

We recommend to do this within a [virtual environment](https://docs.python.org/3/tutorial/venv.html), e.g., using [conda](https://docs.conda.io).
On macOS, you need to install [tensorflow-macos](https://github.com/apple/tensorflow_macos) first.

1.) Install the package
```
    pip install .
```

2.) Test the installation in Python
```
    python
```
```
    >>> import sionna
    >>> print(sionna.__version__)
    0.18.0
```

