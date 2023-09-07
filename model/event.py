from enum import Enum, auto, unique


@unique
class Event(Enum):
    SCREENING_VIA = auto()
    SCREENING_DNA = auto()
    SCREENING_CANCER_INSPECTION = auto()
    DIAGNOSTIC_VIA = auto()
    SURVEILLANCE_VIA = auto()
    SURVEILLANCE_DNA = auto()
    SURVEILLANCE_CANCER_INSPECTION = auto()
    TREATMENT_LEEP = auto()
    TREATMENT_CRYO = auto()
    TREATMENT_CANCER = auto()
    VACCINATION = auto()
