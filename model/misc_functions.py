import numpy as np
import pandas as pd
from bisect import bisect


def create_cdf(probability_list: list) -> list:
    """ Convert a list of probabilities, into a cumulative distribution function

    Parameters
    ----------
    probability_list : a list of probabilities that add to 1
    """
    cdf = list()
    cdf.append(probability_list[0])
    for i in range(1, len(probability_list)):
        cdf.append(cdf[-1] + probability_list[i])
    cdf[len(cdf) - 1] = 1
    return cdf


def normalize(probability_list: list, return_cdf=True) -> list:
    """ Normalize a list of probabilities and create the cdf for them

    Parameters
    ----------
    probability_list : list of probabilities. May not add to 1, as one probability may have been removed.
    """
    total = sum(probability_list)
    probability_list = [item / total for item in probability_list]
    if return_cdf:
        return create_cdf(probability_list)
    return probability_list


def random_selection(random: float, cdf: list, options: list) -> object:
    """ Given cumulative distribution function and a list of options, make a random selection

    Parameters
    ----------
    random: a random number between 0 and 1
    cdf : a list containing the cumulative distribution values. Ex [0, .2, .3, .7, 1.0]
    options : a list containing the options that can be selected
    """
    return options[bisect(cdf, random)]


def filter_hpv_dict(hpv_dict, strain):
    new_dict = dict()
    for k, v in hpv_dict.items():
        if k[1] == strain:
            new_dict[k] = v
    return new_dict


class Dynamic2DArray:
    """
    Expandable numpy array designed to be faster than np.append.
    Based on: https://stackoverflow.com/a/7134033
    Slightly slower than using Python lists but way more memory efficient.
    """

    def __init__(self, num_columns: int, dtype=np.uint32):
        self.num_columns = num_columns
        self.capacity = 100
        self.size = 0
        self.data = np.zeros((self.capacity, self.num_columns), dtype=dtype)

    def add_row(self, row: np.ndarray):
        if self.size == self.capacity:
            self.capacity *= 2
            newdata = np.zeros((self.capacity, self.num_columns))
            newdata[: self.size] = self.data
            self.data = newdata

        self.data[self.size] = row
        self.size += 1

    def finalize(self):
        return self.data[: self.size]

    def __getitem__(self, *args, **kwargs):
        return self.data.__getitem__(*args, **kwargs)

    def __setitem__(self, *args, **kwargs):
        """
        Note: allowing access to this might allow users to do something unexpected
        if they set rows that don't "exist" yet but are part of the capacity.
        """
        return self.data.__setitem__(*args, **kwargs)


class EventStorage:
    def __init__(self, column_names: list, store_events: bool = True):
        """EventStorage is used to record changes to state variables or to record events in a model

        Args:
            column_names (list): A list of the column names
            store_events (bool, optional): Should events be stored. Defaults to True. This parameter can be used to
                turn off storing of events to save time and memory.
        """
        self.store_events = store_events
        self.column_names = column_names
        self.data = []

    def record_event(self, row: tuple):
        """Record a change to a state variable

        Args:
            row (tuple): A tuple of values to be recorded. Must match the length of `self.column_names`
        """
        if self.store_events:
            self.data.append(row)

    def make_events(self) -> pd.DataFrame:
        """ Convert the array to a DataFrame """
        return pd.DataFrame(self.data, columns=self.column_names)
