# Cervical Cancer Prevention Agent-Based Model

This model simulates the impact of several interventions on cervical cancer outcomes in sub-Saharan Africa. The primary outcomes are cervical cancer incidence, mortality rates, and intervention costs. A secondary outcome (for some countries) is HPV prevalence. The interventions of interest include HPV vaccination, cervical cancer screening, and HIV treatment.

The simulation is implemented using python and primarily `numpy` based state classes. 

## Environment Setup

There are several ways to work with project code locally. 

### VirtualEnv Setup

If you already have python and pip installed on your computer, you can run the following from the repo directory:

```
pip install virtualenv
virtualenv python_env
source python_env/bin/activate
pip install -r docker/requirements.txt
pip install -e .
```

### Docker Setup

```
docker-compose build
```

## Running Scenarios/Iterations

### Terminology

- An _iteration_ is a single model run, simulating the lifetimes of one group of women. It is characterized by a random seed and a set of model parameters.

- A _scenario_ is a collection of iterations that share the same set of model parameters but differ in their random seed. The purpose of a scenario is to observe how much variation one might expect in the model results given a particular set of parameters.

- An _experiment_ is a collection of scenarios whose model parameters differ. The purpose of an experiment is to compare the model results between different sets of model parameters.

### Run.py

We will now provide examples for how to run scenarios or iterations, using Zambia as an example.

You can run one iteration of a scenario with:

```bash
python run.py experiments/zambia/scenario_base
```

You can run one `x` iterations of a scenario and use multiprocessing with:

```bash
python run.py experiments/zambia/scenario_base --n=x --cpus=2
```


### Output

Running the experiment will produce several files and directories:

- An overall log file will be created in the experiment directory.
- One directory per iteration will be created inside each scenario directory. The iteration directory will contain:
    - Any output files containing the model results for that iteration.
    - A log file for that iteration.


## Running the tests

To run the test suite, execute the following command from the project's root directory:

```
pytest
```

## Profiling

```
sudo pyinstrument --html -o pyinstrument_test.html experiments/zambia/src/example.py
```	