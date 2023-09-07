"""
Create a graphic to:
    Can we generate a graphic or table to show what age HPV infection is acquired that eventually leads to cancer.
    Can we look at HIV- and HIV+ women separately.
"""

import math
from pathlib import Path

import pandas as pd
import plotly.express as px
from model.analysis import Analysis
from model.cervical_model import CervicalModel
from model.logger import LoggerFactory
from model.state import CancerState, HivState, HpvState, HpvStrain

# ----- Run the Model
scenario_dir = Path("experiments/zambia/scenario_base/")
model = CervicalModel(scenario_dir=scenario_dir, iteration=0, logger=LoggerFactory().create_logger("log"), seed=1111)
model.run(print_status=True)

# ----- Run the analysis
analysis = Analysis(scenario_dir, iteration=0)


strains = [i.name for i in HpvStrain]
# ----- Find the unique ids of agents who got cancer
se = analysis.state_events
cc = se[se.State.isin(strains) & (se.To == HpvState.CANCER)]
unique_ids = cc.Unique_ID.values
# Filter to only HPV transitions for those agents
hpv = se[(se.Unique_ID.isin(unique_ids)) & (se.State.isin(strains)) & (se.To == HpvState.HPV)]

# ----- For each person, find the momment that got HPV before they got cancer
data = []
for item in cc.itertuples():
    unique_id = item.Unique_ID
    time = item.Time
    hpv_time = hpv[(hpv.Unique_ID == unique_id) & (hpv.State == "SIXTEEN") & (hpv.Time < time)].Time.values[-1]
    age = math.floor(hpv_time / 12) + 9
    if analysis.agent_timeline.loc[unique_id].loc[age].hiv == HivState.HIV:
        data.append((age, "HIV"))
    else:
        data.append((age, "NO HIV"))

df = pd.DataFrame(data, columns=["Age", "HIV Status"])


# df = px.data.tips()
fig = px.histogram(
    df,
    title="Age of HPV Infection for Women That Eventually Got Cervical Cancer",
    x="Age",
    color="HIV Status",
    marginal="box",
    hover_data=df.columns,
)
fig.update_traces(opacity=0.75)
fig.update_layout(barmode="overlay")
# Reduce opacity to see both histograms
fig.update_traces(opacity=0.75)
fig.show()

fig.write_html("example.html")
