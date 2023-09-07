import pandas as pd
import plotly
import plotly.graph_objs as go
import seaborn as sns


def combine_age_groups(df=None, ages=None, yearly=False, initial_age=9, num_steps=1092, column_out='Model',
                       incidence=False):
    if yearly:
        ages = list(range(initial_age, initial_age + int(num_steps / 12) + 1))
        average = []
        for i in range(len(ages) - 1):
            average.append(sum(df[i * 12:((i + 1) * 12)]) / 12 * 100)
    else:
        values = [0]
        for i in range(len(ages) - 1):
            values.append(
                (ages[i + 1] - ages[0]) * 12
            )
        average = []
        for i in range(len(values) - 1):
            if incidence:
                average.append(round(sum(df[values[i]:values[i + 1]]) / ((values[i + 1] - values[i]) / 12), 4))
            else:
                average.append(round(sum(df[values[i]:values[i + 1]]) / (values[i + 1] - values[i]), 4) * 100)

    df_final = pd.DataFrame()
    df_final['age'] = ages[0:(len(ages) - 1)]
    df_final[column_out] = average

    return df_final


def combine_age_groups2(df=None, ages=None, yearly=False, initial_age=9, num_steps=1092, column_out='Model'):
    if yearly:
        ages = list(range(initial_age, initial_age + int(num_steps / 12) + 1))
        average = []
        for i in range(len(ages) - 1):
            average.append(sum(df[i * 12:((i + 1) * 12)]))
    else:
        values = [0]
        for i in range(len(ages) - 1):
            values.append(
                (ages[i + 1] - ages[0]) * 12
            )
        average = []
        for i in range(len(values) - 1):
            average.append(round(sum(df[values[i]:values[i + 1]]) / ((values[i + 1] - values[i]) / 12), 4))

    df_final = pd.DataFrame()
    df_final['age'] = ages[0:(len(ages) - 1)]
    df_final[column_out] = average

    return df_final


def add_columns(df_g=None):
    df_g.loc[df_g.shape[0]] = ['80-84', float('nan'), float('nan')]
    df_g.loc[df_g.shape[0]] = ['85-89', float('nan'), float('nan')]
    df_g.loc[df_g.shape[0]] = ['90-94', float('nan'), float('nan')]
    df_g.loc[df_g.shape[0]] = ['95-100', float('nan'), float('nan')]

    return df_g


def grab_file(file_name=None, trim_to=None):
    df_g = pd.read_csv(file_name)

    df_g.loc[-1] = ['9-11', float('nan'), float('nan')]
    df_g.index = df_g.index + 1
    df_g = df_g.sort_index()

    df_g.loc[df_g.shape[0]] = ['80-84', float('nan'), float('nan')]
    df_g.loc[df_g.shape[0]] = ['85-89', float('nan'), float('nan')]
    df_g.loc[df_g.shape[0]] = ['90-94', float('nan'), float('nan')]
    df_g.loc[df_g.shape[0]] = ['95-100', float('nan'), float('nan')]

    df_g['ages_trimmed'] = trim_to

    return df_g


def grab_cancer_inc(cancer_fn='experiments/2017-06-26-compare-to-goldhaber-2007/targets/cancer_incidence.csv'):
    df_g = pd.read_csv(cancer_fn)
    df_g.loc[-1] = ['9-20', float('nan'), float('nan')]
    df_g.index = df_g.index + 1
    df_g = df_g.sort_index()
    df_g = add_columns(df_g)

    return df_g


def comparison_chart(gold_df=None, gold_ages=None, df=None, df_age=None, title='Title', y_axis='Y-Axis',
                     x_axis='X-Axis', filename='file', y_range=None, open_plot=False):
    age_groups = gold_df[gold_ages]

    trace0 = go.Scatter(
        x=age_groups,
        y=gold_df['lower'],
        name='Goldhaber Lower Bounds',
        line=dict(
            color=('rgb(45, 193, 90)'),
            width=4)
    )
    trace1 = go.Scatter(
        x=age_groups,
        y=gold_df['upper'],
        name='Goldhaber Upper Bounds',
        line=dict(
            color=('rgb(45, 193, 90)'),
            width=4)
    )
    trace2 = go.Scatter(
        x=df_age,
        y=df['Model'],
        name='Model Output',
        line=dict(
            color=('rgb(139, 139, 139)'),
            width=4)
    )

    data = [trace0, trace1, trace2]

    # Edit the layout
    layout = dict(title=title,
                  height=1000,
                  xaxis=dict(title=x_axis),
                  yaxis=dict(title=y_axis, range=y_range),
                  )

    fig = dict(data=data, layout=layout)

    #  Make sure you save it locally and not online!
    plotly.offline.plot(fig, filename=filename, show_link=False, auto_open=open_plot)


def iteration_plot(analysis=None, df=None, filename='filename', auto_open=False,
                   x_axis=None, y_axis=None, title=None, range_list=None):

    colors = ["windows blue", "amber", "greyish", "faded green", "dusty purple",
              'steel blue', 'sand brown', 'rose red', 'peach', 'pale olive', "black"]

    df['Average'] = df.ix[:, 1:11].mean(axis=1)

    def make_trace(y, i):
        return dict(
            x=age_groups,
            y=y,
            name='iteration_' + str(i),
            line=dict(color=(sns.xkcd_rgb[colors[i]]), width=1)
        )
    age_groups = analysis.params.age_ranges

    traces = []
    for i in range(10):
        traces.append(make_trace(df['Model_' + str(i)], i))

    traces.append(dict(
        x=age_groups,
        y=df['Average'],
        name='Average of Iterations',
        line=dict(color=(sns.xkcd_rgb[colors[10]]), width=4)
    ))
    # Edit the layout
    layout = dict(title=title,
                  height=800,
                  xaxis=dict(title=x_axis),
                  yaxis=dict(title=y_axis, range=range_list),
                  )
    fig = dict(data=traces, layout=layout)
    #  Make sure you save it locally and not online!
    plotly.offline.plot(fig, filename=filename, show_link=False, auto_open=auto_open)
