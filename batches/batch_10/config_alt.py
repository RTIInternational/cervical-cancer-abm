from src.prep_batch import Scenario, Values


scenarios = {
    "base": Scenario(values=[Values.base]),
    "screen[dna_then_treat]": Scenario(values=[Values.base, Values.dna_then_treat]),
    "screen[dna_then_treat]_at[35_only]": Scenario(
        values=[Values.base, Values.dna_then_treat, Values.screen_at_35_only],
    ),
    "screen[dna_then_treat]_interval[10]": Scenario(values=[Values.base, Values.dna_then_treat, Values.interval_10]),
    "screen[dna_then_treat]_perf[high]": Scenario(
        values=[Values.base, Values.dna_then_treat, Values.performance_high],
    ),
    "screen[dna_then_treat]_perf[low]": Scenario(values=[Values.base, Values.dna_then_treat, Values.performance_low]),
    "screen[dna_then_triage]": Scenario(values=[Values.base, Values.dna_then_triage]),
    "screen[dna_then_triage]_at[35_only]": Scenario(
        values=[Values.base, Values.dna_then_triage, Values.screen_at_35_only],
    ),
    "screen[dna_then_triage]_interval[10]": Scenario(values=[Values.base, Values.dna_then_triage, Values.interval_10]),
    "screen[dna_then_triage]_perf[high]": Scenario(
        values=[Values.base, Values.dna_then_triage, Values.performance_high],
    ),
    "screen[dna_then_triage]_perf[low]": Scenario(
        values=[Values.base, Values.dna_then_triage, Values.performance_low],
    ),
    "screen[dna_then_via]": Scenario(values=[Values.base, Values.dna_then_via]),
    "screen[dna_then_via]_at[35_only]": Scenario(values=[Values.base, Values.dna_then_via, Values.screen_at_35_only]),
    "screen[dna_then_via]_interval[10]": Scenario(values=[Values.base, Values.dna_then_via, Values.interval_10]),
    "screen[dna_then_via]_perf[high]": Scenario(values=[Values.base, Values.dna_then_via, Values.performance_high]),
    "screen[dna_then_via]_perf[low]": Scenario(values=[Values.base, Values.dna_then_via, Values.performance_low]),
    "screen[via]": Scenario(values=[Values.base, Values.via]),
    "screen[via]_at[35_only]": Scenario(values=[Values.base, Values.via, Values.screen_at_35_only]),
    "screen[via]_compliance[40]": Scenario(values=[Values.base, Values.via, Values.compliance_40]),
    "screen[via]_compliance[60]": Scenario(values=[Values.base, Values.via, Values.compliance_60]),
    "screen[via]_interval[10]": Scenario(values=[Values.base, Values.via, Values.interval_10]),
    "screen[via]_perf[high]": Scenario(values=[Values.base, Values.via, Values.performance_high]),
    "screen[via]_perf[low]": Scenario(values=[Values.base, Values.via, Values.performance_low]),
    "vaccinate[20]": Scenario(values=[Values.base, Values.vaccinate_20]),
    "vaccinate[20]_screen[dna_then_triage]_interval[10]": Scenario(
        values=[Values.base, Values.vaccinate_20, Values.dna_then_triage, Values.interval_10]
    ),
    "vaccinate[20]_screen[via]_interval[10]": Scenario(
        values=[Values.base, Values.vaccinate_20, Values.via, Values.interval_10]
    ),
    "vaccinate[50]": Scenario(values=[Values.base, Values.vaccinate_50]),
    "vaccinate[50]_screen[dna_then_triage]_interval[10]": Scenario(
        values=[Values.base, Values.vaccinate_50, Values.dna_then_triage, Values.interval_10]
    ),
    "vaccinate[50]_screen[via]_interval[10]": Scenario(
        values=[Values.base, Values.vaccinate_50, Values.via, Values.interval_10]
    ),
    "vaccinate[80]": Scenario(values=[Values.base, Values.vaccinate_80]),
    "vaccinate[80]_screen[dna_then_triage]_interval[10]": Scenario(
        values=[Values.base, Values.vaccinate_80, Values.dna_then_triage, Values.interval_10]
    ),
    "vaccinate[80]_screen[via]_interval[10]": Scenario(
        values=[Values.base, Values.vaccinate_80, Values.via, Values.interval_10]
    ),
}
