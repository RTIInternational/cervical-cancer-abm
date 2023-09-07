from pathlib import Path

import pandas as pd
from model.analysis import Analysis
from model.state import CancerState, HpvState, HpvStrain

from src.helper_functions import combine_age_groups


def run_analysis(scenario_dir: Path, iteration: int):

    analysis = Analysis(scenario_dir, iteration)

    hpv_age_groups = [16, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 100]
    cin23_age_groups = [20, 30, 40, 50, 100]
    cancer_age_groups = [15, 40, 45, 50, 55, 60, 80, 100]

    # ----- The HPV Prevalence Targets -------------------------------------------------------------------------------
    # (1) ----- Low-Risk HPV Prevalence
    df = analysis.prevalence(field=HpvStrain.LOW_RISK.name, states=(HpvState.HPV.value,),)
    results_df = combine_age_groups(df=df * 100, ages=hpv_age_groups, target="HPV_LR").loc[0:10]
    # (2) ----- High-Risk HPV Prevalence
    df = analysis.prevalence(field=HpvStrain.HIGH_RISK.name, states=(HpvState.HPV,),)
    results_df = results_df.append(combine_age_groups(df=df * 100, ages=hpv_age_groups, target="HPV_HR").loc[0:10])
    # (3) ----- 16
    df = analysis.prevalence(field=HpvStrain.SIXTEEN.name, states=(HpvState.HPV,),)
    results_df = results_df.append(combine_age_groups(df=df * 100, ages=hpv_age_groups, target="HPV_16").loc[0:10])
    # (4) ----- 18
    df = analysis.prevalence(field=HpvStrain.EIGHTEEN.name, states=(HpvState.HPV,),)
    results_df = results_df.append(combine_age_groups(df=df * 100, ages=hpv_age_groups, target="HPV_18").loc[0:10])

    # ----- The 6 CIN23 Prevalence Targets -----------------------------------------------------------------------------
    # (5) ----- High-Risk
    df = analysis.prevalence(field=HpvStrain.HIGH_RISK.name, states=(HpvState.CIN_2_3,),)
    results_df = results_df.append(combine_age_groups(df=df * 100, ages=cin23_age_groups, target="CIN23_HR").loc[0:3])
    # (6) ----- SIXTEEN
    df = analysis.prevalence(field=HpvStrain.SIXTEEN.name, states=(HpvState.CIN_2_3,),)
    results_df = results_df.append(combine_age_groups(df=df * 100, ages=cin23_age_groups, target="CIN23_16").loc[0:3])
    # (7) ----- EIGHTEEN
    df = analysis.prevalence(field=HpvStrain.EIGHTEEN.name, states=(HpvState.CIN_2_3,),)
    results_df = results_df.append(combine_age_groups(df=df * 100, ages=cin23_age_groups, target="CIN23_18").loc[0:3])

    # ----- The Cancer Incidence Targets -------------------------------------------------------------------------------
    # (8) ----- Cancer Incidence Overall
    df = 100_000 * analysis.incidence(CancerState.id, CancerState.LOCAL.value)
    results_df = results_df.append(combine_age_groups(df=df, ages=cancer_age_groups, target="Cancer_Inc").loc[0:5])

    # ----- Where did the Cancer come from -----------------------------------------------------------------------------
    # (9) ----- Cause of Cancer
    cancer_16 = list(analysis.agent_events[HpvStrain.SIXTEEN.name]["To"].values).count(HpvState.CANCER.value)
    cancer_18 = list(analysis.agent_events[HpvStrain.EIGHTEEN.name]["To"].values).count(HpvState.CANCER.value)
    cancer_hr = list(analysis.agent_events[HpvStrain.HIGH_RISK.name]["To"].values).count(HpvState.CANCER.value)
    cancer_total = max(sum([cancer_16, cancer_18, cancer_hr]), 1)
    percent_16 = cancer_16 / cancer_total
    percent_18 = cancer_18 / cancer_total
    percent_hr = cancer_hr / cancer_total
    temp_df = pd.DataFrame()
    temp_df["Target"] = ["Cause of Cancer: 16", "Cause of Cancer: 18", "Cause of Cancer: HR"]
    temp_df["Age"] = "N/A"
    temp_df["Model"] = [percent_16, percent_18, percent_hr]
    results_df = results_df.append(temp_df)

    # ---- Save as CSV
    results_df.columns = ["Target", "Age", str(iteration)]
    results_df.to_csv(analysis.iteration_dir.joinpath("analysis_values.csv"), index=False)
