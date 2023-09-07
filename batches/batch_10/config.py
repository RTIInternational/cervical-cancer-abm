from src.prep_batch import Scenario, Values


scenarios = {
    "base": Scenario(values=[Values.base]),
    "screen[dna_then_treat]": Scenario(values=[Values.base, Values.dna_then_treat]),
    "screen[dna_then_triage]": Scenario(values=[Values.base, Values.dna_then_triage]),
    "screen[dna_then_via]": Scenario(values=[Values.base, Values.dna_then_via]),
    "screen[via]": Scenario(values=[Values.base, Values.via]),
    "vaccinate[20]": Scenario(values=[Values.base, Values.vaccinate_20]),
    "vaccinate[50]": Scenario(values=[Values.base, Values.vaccinate_50]),
    "vaccinate[80]": Scenario(values=[Values.base, Values.vaccinate_80]),
}
