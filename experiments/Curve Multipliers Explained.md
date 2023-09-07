### General overview

Our goal is not to match the target values with this process. Our goal is to match the change between age groups. Example: A drop of 51% from age group 1 to group 2 is the goal - not matching a target of 11.9.

Why? When using age specific multipliers

#### The Calibration Process: An Outline

In our experiment, matching the progression of strain 16 is the most important because cancer incidence is the most important target. Furthermore, strain 16 needs to cause 50% of all cancer. High risk is second at 30% of all cancer, and 18 is last with 20%.

When a women reaches cancer in any stage, this becomes her final status. Therefore, the transitions along each strain will have a (small) interaction with other strains in the same and older age groups. Therefore, the calibrating curve multipliers for strains and age groups relies on other strains and age groups. We complete the process in a specific order:

* Sixteen: 25-29
* High-Risk: 25-29
* Eighteen: 25-29
* Low-Risk: 25-29
* Sixteen: 30-34
* High-Risk: 30-34
* ....

## Curve Multipliers Explained

It is likely that country target values do not follow the same "curve" as Goldhabers. Consider the following table:

| Age        | Goldhaber Target | New Target  |
| ---------- |:----------------:| -----------:|
| 15-24      | 20               | 24          |
| 25-29      | 18               | 12          |
| 35-39     | 16               | 8           |
| 40-45      | 20               | 16          |
| 45-50      | 20               | 8           |

Notice that the targets have different outcome curves.  The original (Goldhaber) targets dips for middle, and then increases again towards the end. However, the new target is consistently moving up and down. A wide range of sources is also used, contributing to this problem:

* Multipliers and distributions from Goldhaber
* Transition Rates from the U.S
* Transition Rates from South Africa and Zambia
* Death Rates from Zambia (Spectrum Model)

We could start calibration by creating lots of parameter sets for standard multipliers, but we would likely never match our new target values. We implement what we are calling curve multipliers to help achieve our new targets.

### Understanding the Difference in Multipliers

Consider the original rates per 1,000 women (the blue doted line below). A single multiplier will either raise or lower the entire curve (the purple dashed line below). These single multipliers are what Goldhaber calibrated, and what we will calibrate at the end of calibration.

However, when we apply this to a region/country whose actual prevalence targets do not follow the same target curve that this original rate will give us, we implement what we are calling "curve multipliers". To do this, we apply a multiplier to each age range. If the rates need to be higher early on, but lower towards the end, we can fix this with such multipliers. Our new curve is the orange long-dahsed line.

<img src="zambia/base_documents/data/curves.jpg " alt="alt text" width="550" height="350">

[This file](multipliers.csv) contains one iteration of the original Goldhaber multipliers. Since we are in a different region, we have adjusted the range of potential multipliers. We used subject matter expertese to help find good starting values.

### Understanding the Calibration Process

Previous Zambian versions (1, 2, and 3) followed a very complex calibration process. We have simplified this as much as possible. Here is the general overview

* We select the middle value of all the "standard multipliers" and fix them for the entire curve calibration process
* Each multiplier is calibrated in a specfic order. The age group of the first strain must be finished before the corresponding age group of the next strain starts(16 -> HR -> 18 -> LR)
* Age groups are completed in order
* We cast a wide net of multipliers from 0.01 to 10 for each
* We compare the results from the calibration runs, to the desired targets
* We build a predictive model using the target values as the X, and multipliers as the Y
* We plug in our desired target into the model and recieve a predicted multiplier to use
* This multiplier is saved and used for that specific curve multiplier going forward
* We move to the next age group or strain and repeat this process
