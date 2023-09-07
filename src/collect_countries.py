import pandas as pd


def main():
    for country in ["zambia", "japan", "india", "usa"]:
        df = pd.read_csv(f"experiments/{country}/base_documents/calibration/first_pass/analysis_output.csv")
        df = df.sort_values(by=["Cause Check", "Weighted % Diff"], ascending=[False, True]).reset_index(drop=True)
        av = pd.read_csv(f"experiments/{country}/base_documents/calibration/first_pass/analysis_values.csv")

        top50 = df.Scenario.values[0:50]

        av1 = av[top50[0]]
        top50_avg = av[top50].mean(axis=1)
        av50 = av[top50[-1]]

        output = pd.DataFrame([av1, top50_avg, av50]).T
        output.to_csv(f"calibration_temp/{country}.csv")


if __name__ == "__main__":
    main()
