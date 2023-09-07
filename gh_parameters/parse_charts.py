from PIL import Image
import pandas as pd


class Chart:
    """
    Extract data points from a line chart stored as an image.

    This implementation is designed to work with the images provided by the
    supplementary material accompanying the following paper:

        Goldhaber-Fiebert JD et al. "Modeling human papillomavirus and cervical
        cancer in the United States for analyses of screening and vaccination".
        Population Health Metrics (2007), 5:11. DOI: 10.1186/1478-7954-5-11

    Several assumptions are made:

      1. The image contains a single chart.

      2. The background of the chart area is a solid color that doesn't appear
         elsewhere in the image. (The "chart area" is where the data lines are
         drawn, so it excludes parts of the image like axes, titles, and
         margins.)

      3. The lines are solid and drawn using a single color. No aliasing has
         been applied to avoid "jagged" lines, which would change the color
         along the edge of the lines.

      4. The x-axis represents ages.

    To extract data from a line in the chart, the user supplies the line's color
    and the desired ages, and the corresponding y-values along the line are
    returned. Because a line in the image has thickness, the algorithm finds all
    possible y-values for a given age and takes the midpoint. y-values are found
    by looking for every pixel in the chart area with the given age and
    selecting the ones with the given color.

    The data extraction method isn't perfect. Inaccuracies may result from the
    following factors:

      1. For charts with multiple lines, the lines may overlap, which results in
         lines being wholly or partially obscured in some locations. For ages
         where this happens, the y-value will either be missing or will be
         slightly larger or smaller than it should be (depending on whether the
         lower or upper portion of the line was obscured).

      2. The lines in the image have been drawn to be aesthetically pleasing.
         Especially at points appearing at a "vertex" along the line, the
         midpoint of the line's thickness may not correspond exactly with the
         data point represented there.

      3. The chart area in these images has a very small border which isn't
         accounted for in the algorithm implemented here.

    The user is advised to inspect the extracted values and adjust them to
    address any such inaccuracies.
    """

    def __init__(self, file, line_colors, ages = range(10, 76),
                 x_min = 9.5, x_max = 75.5, y_min = 0, y_max = None,
                 bgcolor = (192, 192, 192, 255),
    ):
        """
        Create a new chart containing one or more data lines.

        Arguments
        ---------
        file - File name of the image containing the chart.

        line_colors - Dictionary mapping line names to a color value. Colors
          must be specified as a (R,G,B,A) tuple with values in the range
          [0,255].

        ages - Iterable of age values for which the y-values in the chart should
          be extracted.

        x_min, x_max - Minimum and maximum ages represented along the x-axis in
          the chart.

        y_min, y_max - Minimum and maximum values represented along the y-axis
          in the chart.

        bgcolor - Color appearing in the background of the chart area. Must be
          specified as a (R,G,B,A) tuple with values in the range [0,255].
        """

        self.bgcolor = bgcolor
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max

        self.image = self.crop_to_chart_area(file)
        self.pixels = self.image.load()

        self.lines = {
            name: Line(name, line_colors[name], ages)
            for name in line_colors
        }

        for line in self.lines.values():
            line.y = self.find_line_y(line)

    def interpolate_line(self, line_name, ages):
        """
        Compute y-values by linearly interpolating between two points on the line.

        This method may be useful to compute y-values for points that were
        obscured by other lines in the image. It would generally be useful only
        if the obscured points fell approximately on a straight line between
        neighboring points.

        Arguments
        ---------
        line_name - Name of line whose values should be interpolated.

        ages - Iterable of age values defining the interpolation. The first and
          last ages form the anchors of the interpolation, and y-values for
          these ages must be non-null. The y-values for the interior ages will
          be recomputed such that they fall on the line connecting the anchor
          points.
        """

        line = self.lines[line_name]

        ages = list(ages)
        x_start = ages[0]
        x_end = ages[-1]

        y_start = line[x_start]
        y_end = line[x_end]

        x_range = x_end - x_start
        y_range = y_end - y_start

        for x in ages[1:-1]:
            line[x] = y_start + ((x - x_start) / x_range) * y_range

    def export(self, file, num_decimals = 2):
        """
        Export all the data points to a CSV file.

        Arguments
        ---------
        file - Name of the CSV file to create.

        num_decimals - Round values to this many decimals before exporting. Set
          to None to disable rounding.
        """

        df = pd.DataFrame({line.name: line.y for line in self.lines.values()})
        df.index.name = 'age'

        # Prevent exporting null values.
        nulls = df.isnull()
        if nulls.sum().sum() > 0:
            for col_name in nulls:
                col = nulls[col_name]
                if col.sum() > 0:
                    print('Null values found in line "{}" at ages: {}'.format(col_name, list(col[col].index)))
            raise RuntimeError('Null values detected.')

        if num_decimals is not None:
            df = df.round(num_decimals)

        df.to_csv(file, encoding = 'utf-8')

    def find_line_y(self, line):
        return [self.find_y(x, line.color) for x in line.x]

    def find_y(self, x, color):
        x_pixel = self.get_pixel_from_x_value(x)
        y_pixels = [p for p in range(self.image.height) if self.pixels[x_pixel, p] == color]
        if (len(y_pixels) > 0):
            y_pixel_avg = sum(y_pixels) / len(y_pixels)
            return self.get_y_value_from_pixel(y_pixel_avg)
        return None

    def get_pixel_from_x_value(self, x):
        return int(self.image.width * (x - self.x_min) / (self.x_max - self.x_min))

    def get_y_value_from_pixel(self, pixel):
        return self.y_min + (1 - pixel/self.image.height) * (self.y_max - self.y_min)

    def crop_to_chart_area(self, file):
        image = Image.open(file)
        pixels = image.load()

        left = image.width
        right = 0
        upper = image.height
        lower = 0

        for r in range(image.width):
            for c in range(image.height):
                if pixels[r, c] == self.bgcolor:
                    if r < left: left = r
                    if r > right: right = r
                    if c < upper: upper = c
                    if c > lower: lower = c

        return image.crop((left, upper, right, lower))

    def __getitem__(self, line_name):
        return self.lines[line_name]


class Line:
    """
    Data line on a chart.

    The x- and y-coordinates of the line are stored as a Pandas Series, with the
    x-coordinates represented by the index and the y-coordinates represented by
    the values. The x-coordinates must be specified upon instantiation and are
    not expected to be changed afterwards. The y-coordinates should be assigned
    after instantiation and may be changed later as needed.
    """

    def __init__(self, name, color, x):
        self.name = name
        self.color = color
        self.x = x
        self.data = pd.Series(index = self.x)

    @property
    def y(self):
        return self.data

    @y.setter
    def y(self, y):
        self.data = pd.Series(y, index = self.x)

    def __getitem__(self, i):
        return self.data[i]

    def __setitem__(self, i, value):
        self.data[i] = value
    

if __name__ == '__main__':

    # Step through the charts of interest from the Goldhaber-Fiebert paper,
    # extracting and exporting the data points from each one.


    chart_name = 'normal_to_hpv'
    chart = Chart(
        file = f'images/{chart_name}.png',
        line_colors = {
            'sixteen': (255, 0, 0, 255),
            'eighteen': (255, 153, 0, 255),
            'high_risk': (255, 255, 0, 255),
            'low_risk': (0, 255, 255, 255),
        },
        y_max = 140,
    )
    chart.interpolate_line('low_risk', range(14, 17))
    chart.interpolate_line('low_risk', range(50, 66))
    chart.interpolate_line('low_risk', range(65, 76))
    chart.interpolate_line('sixteen', range(22, 26))
    chart.interpolate_line('sixteen', range(26, 31))
    chart.interpolate_line('sixteen', range(49, 57))
    chart.interpolate_line('sixteen', range(62, 71))
    chart.export(f'{chart_name}.csv')


    chart_name = 'hpv_to_cin1'
    Chart(
        file = f'images/{chart_name}.png',
        line_colors = {
            'high_risk': (255, 0, 255, 255),
            'low_risk': (0, 255, 255, 255),
        },
        y_max = 120,
    ).export(f'{chart_name}.csv')


    chart_name = 'hpv_cin1_to_cin23'
    Chart(
        file = f'images/{chart_name}.png',
        line_colors = {
            'high_risk': (255, 0, 255, 255),
            'low_risk': (0, 255, 255, 255),
        },
        y_max = 50,
    ).export(f'{chart_name}.csv')


    chart_name = 'cin23_to_cancer'
    Chart(
        file = f'images/{chart_name}.png',
        line_colors = {
            'high_risk': (255, 0, 255, 255),
        },
        y_max = 80,
    ).export(f'{chart_name}.csv')


    chart_name = 'cin23_to_normal'
    Chart(
        file = f'images/{chart_name}.png',
        line_colors = {
            'normal': (255, 204, 153, 255),
        },
        y_max = 400,
    ).export(f'{chart_name}.csv')


    chart_name = 'alive_to_dead'
    Chart(
        file = f'images/{chart_name}.png',
        line_colors = {
            'dead': (255, 204, 153, 255),
        },
        y_max = 3500,
    ).export(f'{chart_name}.csv')
