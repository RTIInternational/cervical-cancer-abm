# India

## Calibration: Step One

Follow the guide [here](../README.md) to calibrate this country's model.

## Calibration: Step Two

There are no secondary steps for India.

## Transition Matrices

#### Life

- Overall mortality comes from [this](base_documents/data/India input data April 22 2021.xlsx) file (the `mortality census` sheet). We used [this](base_documents/data/mortality.xlsx) to convert the raw numbers to deaths per 10,000, which produced the [file](base_documents/data/mortality.csv) that is used.
- Cervical cancer mortality comes from the rates used in the Zambian Model.

#### HIV

- We are not modeling HIV for India

#### HPV, Cancer Progression, Cancer Detection

- See Zambia's [README.md](../zambia/README.md)

## Running Lots of Models

After the calibrations is complete, you should have a single set of parameters that produce a decent performing model across all targets. However, there are a lot of moving pieces. Instead of using this single parameter set, we run thousands of random parameter sets and select the best performing 50. We need to run a lot of models.

### Prep Scenarios (5-10 minutes)

```bash
docker-compose run  -d cervical_cancer bash -c "python3.8 src/prep_mass_runs.py experiment/japan --n=2000"
```

### Run Scenarios (2-20 hours)

Run time fluctuates depending on the server being used and the number of women in the model.

```bash
docker-compose run  -d cervical_cancer bash -c "python3.8 src/run_mass_runs.py experiment/japan"
```

### Collect Results

From local: `experiments/japan/results/final_pass`:

```bash
sudo scp <user>@cds-baldur.rtp.rti.org:/home/<user>/cervical-cancer-v2/experiments/japan/{analysis_values.csv,analysis_output.csv,selected_multipliers.csv} .
```
