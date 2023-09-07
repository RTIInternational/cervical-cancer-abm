## Files Readme

There are a lot of required files per country. Most files have some element of manual creation. This readme tries to explain those creation steps in detail.

### `curve_multipliers`

- `Target_Row`: Numeric: 0 through the length of the curve multipliers
- `State`: The `HPV_STATE` state of the probability to be effected
- `Strain`: the `HPV_STRAIN` strain of the probability to be effected
- `HIV`: The `HIV_STATE` state of the probability to be effected
- `Age`: The age group. This should match the age group from the `targets` file. The main difference is the first age group is always `<X` instead of `X1_X2`. This helps calibrate the first value.
- `Target`: The target value from the `targets` file. Should match the state and strain in question.
- `Current`: The current value of the age specific curve multiplier. This is the value being calibrated. When running `curve_calibration.py` this value is not used. It is set by the calibration.
- `Round`: The round of the calibration process. It is important that age groups and states follow a specific order. Rules of thumb:
  - `HPV` before `CIN23` before `CANCER`
  - `LR` targets are independent since they don't effect cancer totals
  -  Youngest age groups first

### `five_year_survival`

Contains 3 values. The five year survival rate for the 3 different stages of cancer.

### `hiv_multipliers`

Only effects Zambia. Values to raise or lower HIV rates for different age groups.

### `life_multiplier`

A single value to raise or lower probably of deaths for all women. This will (hopefully) not be needed, as the death probabilities should align to the target for life expectancy. This can be used to raise or lower life expectancy.

### `multipleirs`

This contains the original multiplier set (for Zambia) or a condensed multiplier set for other countries. These triangle distributions are calibrated last.

- `STRAIN`: The `HPV_STRAIN`
- `FROM_STATE`: The current `HPV_STATE` state
- `TO_STATE`: The next `HPV_STATE` state. A multiplier will increase or decrease the probability of going `FROM_STATE` to `TO_STATE`
- `IMMUNITY`: One of 3 values (`NATURAL`, `VACCINE`, `All`).
  - `NATURAL`: Natural immunity. People build some natural immunity when they return to `NORMAL` from having `HPV`
  - `VACCINE`: When people are vaccinated, we assume they are 100% immune from HPV
  - `ALL`: Ignore immunity. All probabilities should be updated, regardless of immunity status
- `HIV`: Only important for Zambia. Either `All` to update both `HIV` and `Non-HIV` HIV statuses, or `HIV` to only update the `HPV` probabilities for people with `HIV`
- `LOW`, `HIGH`, `PEAK`: The triangle distribution for the multipliers

### `check_targets`

This file is used to compare the targets to a single runs output. This is primarily used with the `check_targets.py` script.

- `Value`: The target value
- `Run Value`: The value from the simulation
- `% Diff`: The percent difference between the two values
- `Target Group`, `Average`: The average difference for all rows of a single target
