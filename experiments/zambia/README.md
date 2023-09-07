# Zambia Model

## Parameter sources

Parameters for the transition matrices were obtained from several sources:

- The [Goldhaber paper](../../gh_parameters).
- Our calibration procedure - which are produced if this README is followed:

  - [age-specific HPV multipliers](base_documents/hpv_curve_multipliers.csv)
  - [age-specific CIN2/3 multipliers](base_documents/cin23_curve_multipliers.csv)
  - [age-specific HIV multipliers](base_documents/hiv_multipliers.csv)
  - [overall HPV multipliers](base_documents/multipliers.csv)

- Values produced by the EMOD model:

  - [death rates](/experiments/winter_sim/base_documents/parameters/final_mortality.csv)
  - [HIV incidence rates](base_documents/parameters/normal_to_hiv.csv)

- When parameters are unavailable, we use expert level input as needed. These values are documented and explanations are provided.

## Calibration

Please see [this](../README.MD) if you have not calibrated Zambia yet.

## Calibraiton Continued: Creating Predictive Models

As this model has 100s of multipliers and parameters, and we can't run millions of parameter sets, we are building predictive models to filter out potentially bad parameter sets.

### Prep Scenarios

On mallard:

```bash
docker-compose run  -d cervical_cancer bash -c "python3 experiments/zambia/src/mass_runs/prep_mass_runs.py  --n=3000 --cpus=40"
```

### Run Scenarios

```bash
docker-compose run -d cervical_cancer bash -c "python3 experiments/zambia/src/mass_runs/run_mass_runs.py --cpus=40"
```

### Collect Results

To build predictive models in the next step, bring the analysis from remote to local.

From local: `experiments/zambia/results/first_pass`:

```bash
sudo scp <user>@cds-mallard.rtp.rti.org:/home/<user>/cervical-cancer-v2/experiments/zambia/{analysis_values.csv,analysis_output.csv,selected_multipliers.csv} .
```

### Build predictive models

Based on the performance of the random multipliers selected, build random forest models to predict how well randomly selected multipliers will do. These predictive models reduce the number of scenarios that need to be ran by almost 500 to 1. Therefore, if we wanted to run 1m scenarios, we can get away with only running 2,000 scenarios.

Run

`python experiments/zambia/src/create_models.py`

## Run One Last Round of Models

### Sync again

```bash
rsync -avz -e "ssh" --progress . <user>@cds-mallard.rtp.rti.org:/home/<user>/cervical-cancer-v2 --exclude '.git' --exclude 'python_env'
```

### Remove old runs

From mallard: `rm -rf /home/<user>/cervical-cancer-v2/experiments/zambia/scenario*`

### Prep Scenarios

Note that this will take longer to create than last time, as each parameter set must pass a bunch of model tests before it is accepted.

On mallard:

```bash
docker-compose run  -d cervical_cancer bash -c "python3 experiments/zambia/src/mass_runs/prep_mass_runs.py  --n=3000 --cpus=40 --test_params=True"
```

### Run Scenarios

```bash
docker-compose run -d cervical_cancer bash -c "python3 experiments/zambia/src/mass_runs/run_mass_runs.py --cpus=40"
```

### Collect Results

From local: `experiments/zambia/results/final_pass`:

```bash
sudo scp <user>@cds-mallard.rtp.rti.org:/home/<user>/cervical-cancer-v2/experiments/zambia/{analysis_values.csv,analysis_output.csv,selected_multipliers.csv} .
```

## Run Intervention Scenarios

There are several steps to run the intervention scenarios.

1. Move files if you haven't already:

 ```bash
 rsync -avz -e "ssh" --progress . <user>@cds-mallard.rtp.rti.org:/home/<user>/cervical-cancer-v2 --exclude '.git' --exclude 'python_env'
 ```

2. Create set of pickle files for each of the top 50 parameter sets (3 minutes):

 ```bash
 docker-compose run cervical_cancer bash -c "python3 experiments/zambia/src/batches/create_transitions.py"
 ```

3. Prepare the batch (10 seconds):

- NOTE: Careful. System file links may not work outside of the docker container.

 ```bash
 docker-compose run cervical_cancer bash -c "python3 experiments/zambia/src/batches/prep_batch.py batch_10 50"
 ```

4. Run and analye the batch (4 hours):

 ```bash
 docker-compose run -d cervical_cancer bash -c "python3 experiments/zambia/src/batches/run_batch.py batch_10 40 1111"
 ```

5. Combine results (10 seconds)

 ```bash
 docker-compose run cervical_cancer bash -c "python3 experiments/zambia/src/batches/combine_batch.py batch_10"
 ```

6. Bring to local (from local main repo)

 ```bash
 scp <user>@cds-mallard.rtp.rti.org:/home/<user>/cervical-cancer-v2/experiments/zambia/batch_10/combined_results.csv <repo>/experiments/zambia/batch_10/
 ```

## Variance Analysis

#### To test how much variance runs have across different seeds

Follow steps 1-3 above, and then run:

```bash
docker-compose run -d cervical_cancer bash -c "python3 experiments/zambia/src/variance_analysis.py"
```
