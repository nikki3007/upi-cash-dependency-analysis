import pandas as pd
from scipy import stats

df = pd.read_csv("data/cleaned/tableA_bankwise_2019_vs_2023.csv")

df.columns = df.columns.str.strip()

# changing strings to numbers for calculating mean and standard deviation
df["Vol_Pct_Change"] = pd.to_numeric(
    df["Vol_Pct_Change"].astype(str).str.strip(),
    errors="coerce"
)
print(df[df["Vol_Pct_Change"].isna()][["Bank_Name", "Bank_Type", "Vol_Pct_Change"]])

print(df.head())

# Remove extra spaces from bank types
df["Bank_Type"] = df["Bank_Type"].str.strip()

# Separate percentage changes
public = df[df["Bank_Type"] == "Public"]["Vol_Pct_Change"].dropna()

private = df[df["Bank_Type"] == "Private"]["Vol_Pct_Change"].dropna()

print("Public banks:", len(public))
print("Private banks:", len(private))

# calculating mean and standard deviation for both public and private banks
print("\nPUBLIC BANKS")
print("Mean:", public.mean())
print("Standard deviation:", public.std())

print("\nPRIVATE BANKS")
print("Mean:", private.mean())
print("Standard deviation:", private.std())

# Perform Welch's independent two-sample t-test
result = stats.ttest_ind(public, private, equal_var=False)

print("\nWELCH TWO-SAMPLE T-TEST")
print("T-statistic:", result.statistic)
print("P-value:", result.pvalue)
print("Degrees of freedom:", result.df)

# Calculate 95% confidence interval for difference in means

difference = public.mean() - private.mean()

standard_error = (
    public.var(ddof=1) / len(public)
    + private.var(ddof=1) / len(private)
) ** 0.5

t_critical = stats.t.ppf(0.975, result.df)

margin_of_error = t_critical * standard_error

lower_limit = difference - margin_of_error
upper_limit = difference + margin_of_error

print("\n95% CONFIDENCE INTERVAL")
print("Difference in means:", difference)
print("Lower limit:", lower_limit)
print("Upper limit:", upper_limit)

#conclusion based on p-value and confidence interval
alpha = 0.05

print("\nFINAL CONCLUSION")

if result.pvalue < alpha:
    print("Reject the null hypothesis.")
    print("There is a statistically significant difference between public and private banks.")
else:
    print("Fail to reject the null hypothesis.")
    print("There is insufficient evidence of a significant difference between public and private banks.")