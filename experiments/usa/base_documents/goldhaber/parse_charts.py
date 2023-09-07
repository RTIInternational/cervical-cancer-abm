from PIL import Image
import pandas as pd
import numpy as np


class Chart:
    """
    Extract data points from a line chart stored as an image.

    This implementation is designed to work with the images provided by the
    supplementary material accompanying the following paper:

        Goldhaber-Fiebert JD et al. "Modeling human papillomavirus and cervical
        cancer in the United States for analyses of screening and vaccination".
        Population Health Metrics (2007), 5:11. DOI: 10.1186/1478-7954-5-11
    """

    def __init__(self, file: str, y_ticks: list, x_ticks: list):
        """
        """
        self.image = Image.open(file)
        self.pixels = self.image.load()
        self.grey = self.image.convert("LA")
        self.array = np.asarray(self.grey)[:, :, 0]

        self.y_ticks = y_ticks
        self.x_ticks = x_ticks

        # Find the axis of the chart and their min/max locations
        self.x_axis = self.find_x_axis()
        self.y_axis = self.find_y_axis()
        self.x_axis_min = self.y_axis
        self.x_axis_max = np.where(self.array[self.x_axis, :] == 0)[0][-1]
        self.y_axis_min = np.where(self.array[:, self.y_axis] == 0)[0][0]
        self.y_axis_max = self.x_axis
        self.y_axis_markers = self.find_y_axis_markers()
        self.x_axis_markers = self.find_x_axis_markers()

        if len(self.x_axis_markers) - 1 != len(self.x_ticks):
            raise ValueError("The number of ticks found does not match the number of X ticks provided")
        if len(self.y_axis_markers) != len(self.y_ticks):
            raise ValueError("The number of ticks found does not match the number of Y ticks provided")

    def find_x_axis(self):
        """The x_axis will be the row with the most non-white values.
        """
        x_means = self.array.mean(axis=1)
        return np.where(x_means == min(x_means))[0][0]

    def find_y_axis(self):
        """The y_axis will be the column with the most non-white values.
        """
        y_means = self.array.mean(axis=0)
        return np.where(y_means == min(y_means))[0][0]

    def find_y_axis_markers(self):
        """Look to the left of the y-axis. Find all locations where the previous value was not 0, but the current
        value is 0
        """
        column = self.array[:, self.y_axis - 2]
        return [i for i in np.where((column == 0) & (np.append(column[-1], column[0:-1]) != 0))[0]]

    def find_x_axis_markers(self):
        """Look to the left of the y-axis. Find all locations where the previous value was not 0, but the current
        value is 0
        """
        row = self.array[self.x_axis + 5, self.y_axis :]
        markers = [i for i in np.where((row == 0) & (np.append(row[-1], row[0:-1]) != 0))[0]]
        return [i + self.y_axis for i in markers]

    def find_rates(self, column_names: list):
        """Above the start and stop points, find the two black lines
        """
        values = []
        for i, x_marker_start in enumerate(self.x_axis_markers[:-1]):
            x_marker_stop = self.x_axis_markers[i + 1]
            middle = int((x_marker_stop - x_marker_start) / 2 + x_marker_start)

            column = self.array[: self.x_axis, (middle - 2) : (middle + 2)].mean(axis=1)

            # The first two times we find a 0 and the previous value wasn't a 0, are our markers
            heights = [i for i in np.where((column == 0) & (np.append(column[-1], column[0:-1]) != 0))[0]]
            height = heights[0]
            if len(heights) > 1:
                height = sum(heights[0:2]) / 2
            values.append(self.height_to_value(height))

        df = pd.DataFrame(self.x_ticks)
        df["temp"] = values
        df.columns = column_names

        return df

    def height_to_value(self, height):
        min_h = self.y_axis_markers[0]
        max_h = self.y_axis_markers[-1]
        min_v = self.y_ticks[0]
        max_v = self.y_ticks[-1]
        adjusted_height_p = (max_h - height) / (max_h - min_h)
        return (max_v - min_v) * adjusted_height_p


if __name__ == "__main__":

    x_ticks = ["12_14", "15_19", "20_24", "25_29", "30_34", "35_39", "40_44", "45_49", "50_54", "55_59", "60_64"]
    x_ticks.extend(["65_69", "70_74", "75_79"])
    y_ticks = [0, 2, 4, 6, 8]
    # CIN2,3
    chart = Chart(file="experiments/usa/goldhaber/A-CIN23-Prevalence.png", y_ticks=y_ticks, x_ticks=x_ticks)
    df = chart.find_rates(column_names=["Age_Groups", "Prevalence"])

    # Distribution
    x_ticks = ["CIN1 - HR", "CIN1 - 16/18", "", "CIN23 - HR", "CIN23 - 16", "CIN23 - 18", ""]
    x_ticks.extend(["Cancer - HR", "Cancer 16/18"])
    y_ticks = [0, 20, 40, 60, 80, 100]
    chart = Chart(file="experiments/usa/goldhaber/type_distribution.png", y_ticks=y_ticks, x_ticks=x_ticks)
    distribution_df = chart.find_rates(column_names=["Type", "Percent"])
    distribution_df.to_csv("experiments/usa/goldhaber/distribution.csv", index=False)

    df["HR"] = df["Prevalence"] * distribution_df[distribution_df.Type == "CIN23 - HR"].Percent.values[0] / 100
    df["16"] = df["Prevalence"] * distribution_df[distribution_df.Type == "CIN23 - 16"].Percent.values[0] / 100
    df["18"] = df["Prevalence"] * distribution_df[distribution_df.Type == "CIN23 - 18"].Percent.values[0] / 100
    df.to_csv("experiments/usa/goldhaber/prevalence_cin23.csv", index=False)
