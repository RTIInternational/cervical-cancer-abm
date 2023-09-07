# Experiments

This README.md will walk you through preperation and calibration of an experiment. Replace `<country>` with the country of interest. 

### Preperation

Before you begin, follow the main [README](../../README.md) to prepare a virtual environment. You can then prepare the experiment and run a baseline scenario by running: 

```
source python_env/bin/activate
export COUNTRY=<country_name>
python src/prep.py  experiments/$COUNTRY/
```

If you run the following:

```
python src/check_targets.py experiments/$COUNTRY
```

And the `experiments/$COUNTRY/base_documents/curve_multipliers.csv` file has not been prepared, you will run the experiment as is using the base transition matrices. This assumes that `curve_multipliers.csv` has `1` values in the `Current` column for all rows. If you compare the model output to a country's targets, you will see major issues. 

## Calibration

We need to use multipliers to calibrate to these targets. There are two types:

- *standard multipleirs*: which raise or lower transition probabilities for all ages agroups. This is what Goldhaber used.
- *curve multipliers*: which raise or lower transition probabilities for a specific age group only. This is because the target curve for our countries maybe different than that of the US.


### Part #1: Manual Setup

1. Open the curve multipleirs:

	- ```open experiments/$COUNTRY/base_documents/curve_multipliers.csv```
	- set all `Current` values to 1 and save.

2. Check the targets: 

	- ```python src/check_targets.py experiments/$COUNTRY```
	
3. Update triangle distributions (manual process)

	- `open experiments/$COUNTRY/scenario_base/iteration_0/analysis_values.csv`
	- Copy/paste the `0` column into this file: `open experiments/$COUNTRY/base_documents/check_targets.xlsx` in the `Run Value` column
	- Review the target for the first age group of each group (they are marked in red)
	- If the first age group is 20% off or more (for really small targets, allow 50% off), you need a different mode for the triangle distribution that effects this target
	- Update the triangle distribution in this file: `open experiments/$COUNTRY/base_documents/multipliers.csv`


### Part #2: Age-Group Curve Calibration

1. From Local: Move files:

	```
	rsync -avz -e "ssh" --progress . $USER@$SERVER.rtp.rti.org:/home/$USER/cervical-cancer-v2 --exclude '.git' --exclude 'python_env'
	```

2. From Server: Run Calibration (~8-10 hours):

	```
	export COUNTRY=<country_name>
	docker-compose run -d cervical_cancer bash -c "python3 src/curve_calibration.py experiments/$COUNTRY/"
	```

3. When finished, from Local: Copy `curve_multipliers.csv`. 

	```
	scp $USER@$SERVER.rtp.rti.org:/home/$USER/cervical-cancer-v2/experiments/$COUNTRY/base_documents/curve_multipliers.csv experiments/$COUNTRY/base_documents/
	```

4. From Local: Run to test these new multipliers:

```bash
python src/check_targets.py experiments/$COUNTRY
```

When complete, compare the analysis values with the targets as done in part 1. This is a subjective comparison. Small targets, such as `.2%` may have a value of `.4%` in the run (100% off). This is a large proportion difference, but actually quite close in relation to how small the target is. If targets all are "relatively" close, move on.

### Part #2: Checking Life

We want to check to see if a "normal" model has similar life expectancy to that of the "real" women of a country.

- Zambia: [63.3](https://www.macrotrends.net/countries/ZMB/zambia/life-expectancy) in 2018
- Japan: [87.3](https://www.nippon.com/en/features/h00250/life-expectancy-for-japanese-men-and-women-at-new-record-high.html) Women in 2018. 
- India: [71.2](https://knoema.com/atlas/India/topics/Demographics/Age/Female-life-expectancy-at-birth) in 2020
- USA: [81](https://www.ssa.gov/oact/STATS/table4c6.html) in 2016

You can check this with: `open experiments/$COUNTRY/scenario_base/iteration_0/results.csv`

If the value is not within ~.5 a year, update the multiplier in `open experiments/$COUNTRY/base_documents/life_multiplier.csv` and rerun `src/check_targets.py`. This value can lower life expectancy (if value < 1) or raise life expectancy (if value is greater than 1). 

### Part #3: HIV

Only Zambia has HIV. We calibrated this by manually updating the `hiv_multipliers.csv` in Zambia until an appropriate level was reached.


### A quick note on Agent Count

Different components have different agent counts. Agent count determines how long something takes to run. Depending on compute resources, and the importance of the component, different agent counts are used.

- Curve Calibration: `100k`. These values will be used for all models. We use a high agent count here.
- Mass Runs (2k+ models): `100k`. With so many models, we need to limit the agents, but we still need enough to assess accuracy.
- Target Checking: `50k`. Only one model is ran here, but it is a local run.


## Run 2k Parameter Sets

We have limited compute resources. 2k sets takes about 20 hours to complete on Baldur. 


1. Remove old scenarios from server:

	```
	sudo rm -rf experiments/$COUNTRY/scenario*
	```

2. Prepare scenarios on server (~1-2 minutes):

	```
	docker-compose run -d cervical_cancer bash -c "python3 src/prep_mass_runs.py experiments/$COUNTRY  --n=2000"
	```

3. Run scnearios on server (~24 hours):

	```
	docker-compose run -d cervical_cancer bash -c "python3 src/run_mass_runs.py experiments/$COUNTRY"
	```

4. Collect results (from local):

	```
	sudo scp $USER@$SERVER.rtp.rti.org:/home/$USER/cervical-cancer-v2/experiments/$COUNTRY/{analysis_values.csv,analysis_output.csv,selected_multipliers.csv} experiments/$COUNTRY/base_documents/calibration/first_pass
	```

## Collect Countries

After all countries are finished, you can collect their results with:

```bash
python src/collect_countries.py
```

This will place one file per country here: `<repo>/calibration_temp/`. You then need to manually add each country to the calibration file: `calibration_temp/calibration_comparison.xlsx`. Send this to Sujha. 



## Run Intervention Scenarios

After parameter sets have been created for a country, you can now run intervention scenarios. Unless `--country=$COUNTRY` is used for a script, all 4 countries will be ran at one time.

1. Sync Files to Remote:

	```
	rsync -avz -e "ssh" --progress . $USER@$SERVER.rtp.rti.org:/home/$USER/cervical-cancer-v2 --exclude '.git' --exclude 'python_env'
	```

2. Create set of pickle files for each of the top 50 parameter sets (3 minutes): 

	```
	docker-compose run cervical_cancer bash -c "python3 src/create_batch_transitions.py"
	```

3. Prepare the batch of interventions (10 seconds):

	- **NOTE:** System file links will not work outside of the docker container.

	```
	docker-compose run cervical_cancer bash -c "python3 src/prep_batch.py batch_10"
	```

4. Run and analye the batch (4 hours): 

	```
	docker-compose run -d cervical_cancer bash -c "python3 src/run_batch.py batch_10"
	```

5. Combine results (10 seconds)

	```
	docker-compose run cervical_cancer bash -c "python3 src/combine_batch.py batch_10"
	```
	
6. Bring to local (from local main repo)
	
	```
	scp $USER@$SERVER.rtp.rti.org:/home/$USER/cervical-cancer-v2/experiments/$COUNTRY/batch_10/combined_results.csv experiments/$COUNTRY/batch_10/
	```



## Variance Analysis

####To test how much variance runs have across different seeds:

Follow steps 1-3 above, and then run:

```
docker-compose run -d cervical_cancer bash -c "python3 experiments/zambia/src/variance_analysis.py"
```