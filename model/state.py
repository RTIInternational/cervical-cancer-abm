import numpy as np

from typing import List
from enum import IntEnum, Enum, unique, auto


class EventState:
    def __init__(
        self, enum: IntEnum, transition_dict: dict,
    ):
        # --- inputs
        self.enum = enum
        self.transition_dict = transition_dict
        # --- numpy arrays
        self.values = None
        self.probabilities = None
        # --- quality of life variables
        self.integers = [item.value for item in enum]
        self.names = [item.name for item in enum]

    def initiate(self, count: int, state: Enum, dtype: type = np.int16):
        self.values = np.zeros(count, dtype=dtype)
        self.values.fill(state.value)

    def find_probabilities(self, keys: List[tuple]) -> np.array:
        """ Given a set of keys, create a list of probabilities
        """

        # Return the probabilities
        probabilities = np.zeros(len(keys))
        for i in range(len(keys)):
            probabilities[i] = self.transition_dict[keys[i]]
        return probabilities


class GenericState(IntEnum):
    def __str__(self):
        return self.name.lower()


class Empty:
    """ An empty state to house extra arrays or dictionaries
    """

    def __init__(self, data_type):
        self.data_type = data_type


@unique
class HpvState(GenericState):
    NORMAL = auto()
    HPV = auto()
    CIN_1 = auto()
    CIN_2_3 = auto()
    CANCER = auto()


@unique
class HpvStrain(GenericState):
    SIXTEEN = auto()
    EIGHTEEN = auto()
    HIGH_RISK = auto()
    LOW_RISK = auto()


@unique
class HpvImmunity(GenericState):
    NORMAL = auto()
    NATURAL = auto()
    VACCINE = auto()


@unique
class HivState(GenericState):
    NORMAL = auto()
    HIV = auto()


@unique
class CancerState(GenericState):
    NORMAL = auto()
    LOCAL = auto()
    REGIONAL = auto()
    DISTANT = auto()
    DEAD = auto()


@unique
class CancerDetectionState(GenericState):
    UNDETECTED = auto()
    DETECTED = auto()


@unique
class TimeSinceCancerDetectionState(GenericState):
    UNDETECTED = auto()
    WITHIN_5_YEARS = auto()
    BEYOND_5_YEARS = auto()


@unique
class LifeState(GenericState):
    ALIVE = auto()
    DEAD = auto()


# ---- Setup the IDs
HpvState.id = "hpv"
HpvStrain.id = "hpv_strain"
HpvImmunity.id = "hpv_immunity"
HivState.id = "hiv"
CancerState.id = "cancer"
CancerDetectionState.id = "cancer_detection"
TimeSinceCancerDetectionState.id = "time_since_cancer_detection"
LifeState.id = "life"

HpvState.int = 0
HpvStrain.int = 1
HpvImmunity.int = 2
HivState.int = 3
CancerState.int = 4
CancerDetectionState.int = 5
TimeSinceCancerDetectionState.int = 6
LifeState.int = 7
AgeGroup = GenericState("AgeGroup", {"AGE_{}".format(a): a for a in range(9, 101)})

# HPV Strains
HpvStrain.SIXTEEN.int = 16
HpvStrain.EIGHTEEN.int = 18
HpvStrain.HIGH_RISK.int = 20
HpvStrain.LOW_RISK.int = 22

# Integer_map
int_map = {}
for item in [HpvState, HpvStrain, HpvImmunity, HivState, CancerState, CancerDetectionState, LifeState]:
    int_map[item.int] = item.id
int_map[TimeSinceCancerDetectionState.int] = TimeSinceCancerDetectionState.id
for item in HpvStrain:
    int_map[HpvStrain(item).int] = HpvStrain(item).name
