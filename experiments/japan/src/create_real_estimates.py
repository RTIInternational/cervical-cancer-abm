import pandas as pd
from collections import defaultdict
import plotly.express as px
import plotly

results = pd.read_csv("experiments/japan/results/final_pass/top_50.csv")

scenarios = [item for item in results.columns if "scenario" in item]
age_groups = results[(results.Category == "Cancer Incidence")].Age_Group.values
pop = 126_265_000
women_pop = pop * 0.50
population = {
    "15_39": women_pop * (40 - 15) / (64 - 15) * 0.595,  # Proportion of age 15-64 was .506
    "40_44": women_pop * (45 - 40) / (64 - 15) * 0.595,
    "45_49": women_pop * (50 - 45) / (64 - 15) * 0.595,
    "50_54": women_pop * (55 - 50) / (64 - 15) * 0.595,
    "55_59": women_pop * (60 - 55) / (64 - 15) * 0.595,
    "60_79": women_pop * (65 - 60) / (64 - 15) * 0.595 + (0.284 * 0.75) * women_pop,
}

values = defaultdict(list)
for age_group in age_groups:
    for item in scenarios:
        v1 = results[(results.Category == "Cancer Incidence") & (results.Age_Group == age_group)][item].values[0]
        values[age_group].append(v1 / 100_000 * population[age_group])

for age_group in age_groups:
    df = pd.DataFrame(values[age_group])
    fig = px.histogram(df, x=0, nbins=10)
    ag = age_group.replace("_", "-")
    fig.update_layout(
        title=f"Number of Cervical Cancer Occurences Across 50 Model Runs: {ag}",
        xaxis_title="Incidence Count",
        yaxis_title="Number of Runs",
    )
    plotly.offline.plot(fig, filename=f"{ag}.html")
