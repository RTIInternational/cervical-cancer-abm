import os
from pathlib import Path

import pandas as pd
from model.analysis import Analysis
from model.state import CancerState, HivState, HpvState, HpvStrain
from src.mass_run_analysis import analyze_results


def combine_age_groups(df, ages, target):
    average = []
    for i in range(len(ages) - 1):
        age_range = range(ages[i], ages[i + 1])
        value = round(df.loc[age_range].mean(), 4)
        average.append(value)

    age = []
    for i in range(len(ages) - 2):
        age.append(str(ages[i]) + "_" + str(ages[i + 1]))
    age.append(str(ages[len(ages) - 2]) + "+")

    df_final = pd.DataFrame()
    df_final["Age"] = age
    df_final["Model"] = average
    df_final.insert(loc=0, column="Target", value=target)

    return df_final


def run_analysis(scenario_dir: Path, iteration: int):

    analysis = Analysis(scenario_dir, iteration)

    hpv_age_groups = [9, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 100]
    hiv_age_groups = [18, 25, 30, 35, 40, 45, 50, 55, 60]
    hiv_age_groups2 = [15, 50, 60]
    cancer_age_groups = [15, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 100]

    hiv_negative = dict([("hiv", HivState.NORMAL.value)])
    hiv_positive = dict([("hiv", HivState.HIV.value)])

    # ----- The 6 HPV Prevalence Targets -------------------------------------------------------------------------------
    # (1) ----- Low-Risk HPV Prevalence - Non HIV
    df = analysis.prevalence(field=HpvStrain.LOW_RISK.name, states=(HpvState.HPV.value,), filter_dict=hiv_negative)
    results_df = combine_age_groups(df=df * 100, ages=hpv_age_groups, target="HPV_LR_NOHIV").loc[0:7]

    # (2) ----- Low-Risk HPV Prevalence - HIV Infected
    df = analysis.prevalence(field=HpvStrain.LOW_RISK.name, states=(HivState.HIV,), filter_dict=hiv_positive)
    results_df = results_df.append(combine_age_groups(df=df * 100, ages=hpv_age_groups, target="HPV_LR_HIV").loc[0:7])

    # (3) ----- High-Risk HPV Prevalence - Non HIV
    df = analysis.prevalence(field=HpvStrain.HIGH_RISK.name, states=(HpvState.HPV,), filter_dict=hiv_negative)
    results_df = results_df.append(combine_age_groups(df=df * 100, ages=hpv_age_groups, target="HPV_HR_NOHIV").loc[0:7])

    # (4) ----- High-Risk HPV Prevalence - HIV Infected
    df = analysis.prevalence(field=HpvStrain.HIGH_RISK.name, states=(HpvState.HPV,), filter_dict=hiv_positive)
    results_df = results_df.append(combine_age_groups(df=df * 100, ages=hpv_age_groups, target="HPV_HR_HIV").loc[0:7])

    # (5) ----- 16
    df = analysis.prevalence(field=HpvStrain.SIXTEEN.name, states=(HpvState.HPV,),)
    results_df = results_df.append(combine_age_groups(df=df * 100, ages=hpv_age_groups, target="HPV_16").loc[0:7])

    # (6) ----- 18
    df = analysis.prevalence(field=HpvStrain.EIGHTEEN.name, states=(HpvState.HPV,),)
    results_df = results_df.append(combine_age_groups(df=df * 100, ages=hpv_age_groups, target="HPV_18").loc[0:7])

    # ----- The 6 CIN23 Prevalence Targets -----------------------------------------------------------------------------
    # (7) ----- High-Risk: no hiv
    df = analysis.prevalence(field=HpvStrain.HIGH_RISK.name, states=(HpvState.CIN_2_3,), filter_dict=hiv_negative)
    results_df = results_df.append(
        combine_age_groups(df=df * 100, ages=hpv_age_groups, target="CIN23_HR_NOHIV").loc[0:7]
    )

    # (8) ----- High-Risk HIV
    df = analysis.prevalence(field=HpvStrain.HIGH_RISK.name, states=(HpvState.CIN_2_3,), filter_dict=hiv_positive)
    results_df = results_df.append(combine_age_groups(df=df * 100, ages=hpv_age_groups, target="CIN23_HR_HIV").loc[0:7])

    # (9) ----- SIXTEEN: no hiv
    df = analysis.prevalence(field=HpvStrain.SIXTEEN.name, states=(HpvState.CIN_2_3,), filter_dict=hiv_negative)
    results_df = results_df.append(
        combine_age_groups(df=df * 100, ages=hpv_age_groups, target="CIN23_16_NOHIV").loc[0:7]
    )

    # (10) ----- SIXTEEN: hiv
    df = analysis.prevalence(field=HpvStrain.SIXTEEN.name, states=(HpvState.CIN_2_3,), filter_dict=hiv_positive)
    results_df = results_df.append(combine_age_groups(df=df * 100, ages=hpv_age_groups, target="CIN23_16_HIV").loc[0:7])

    # (11) ----- EIGHTEEN: no hiv
    df = analysis.prevalence(field=HpvStrain.EIGHTEEN.name, states=(HpvState.CIN_2_3,), filter_dict=hiv_negative)
    results_df = results_df.append(
        combine_age_groups(df=df * 100, ages=hpv_age_groups, target="CIN23_18_NOHIV").loc[0:7]
    )

    # (12) ----- EIGHTEEN: hiv
    df = analysis.prevalence(field=HpvStrain.EIGHTEEN.name, states=(HpvState.CIN_2_3,), filter_dict=hiv_positive)
    results_df = results_df.append(combine_age_groups(df=df * 100, ages=hpv_age_groups, target="CIN23_18_HIV").loc[0:7])

    # ----- The Cancer Incidence Targets -------------------------------------------------------------------------------
    # (13) ----- Cancer Incidence Overall
    df = 100_000 * analysis.incidence(CancerState.id, CancerState.LOCAL.value)
    results_df = results_df.append(combine_age_groups(df=df, ages=cancer_age_groups, target="Cancer_Inc").loc[0:6])

    # ----- Where did the Cancer come from -----------------------------------------------------------------------------
    # (14) ----- Cause of Cancer
    cancer_16 = list(analysis.agent_events[HpvStrain.SIXTEEN.name]["To"].values).count(HpvState.CANCER.value)
    cancer_18 = list(analysis.agent_events[HpvStrain.EIGHTEEN.name]["To"].values).count(HpvState.CANCER.value)
    cancer_hr = list(analysis.agent_events[HpvStrain.HIGH_RISK.name]["To"].values).count(HpvState.CANCER.value)
    cancer_total = sum([cancer_16, cancer_18, cancer_hr])
    percent_16 = cancer_16 / cancer_total
    percent_18 = cancer_18 / cancer_total
    percent_hr = cancer_hr / cancer_total
    temp_df = pd.DataFrame()
    temp_df["Target"] = ["Cause of Cancer: 16", "Cause of Cancer: 18", "Cause of Cancer: HR"]
    temp_df["Age"] = "N/A"
    temp_df["Model"] = [percent_16, percent_18, percent_hr]
    results_df = results_df.append(temp_df)

    # ----- The Two HIV Prevalence Target ------------------------------------------------------------------------------
    # (15) ----- HIV Prevalence in Women (15-24)
    df = analysis.prevalence(field=HivState.id, states=(HivState.HIV,),)
    results_df = results_df.append(combine_age_groups(df=df * 100, ages=hiv_age_groups, target="HIV_Prev").loc[0])
    results_df = results_df.append(combine_age_groups(df=df * 100, ages=hiv_age_groups2, target="HIV_Prev").loc[0])

    # ---- Save as CSV
    results_df.columns = ["Target", "Age", str(iteration)]
    results_df.to_csv(analysis.iteration_dir.joinpath("analysis_values.csv"), index=False)
