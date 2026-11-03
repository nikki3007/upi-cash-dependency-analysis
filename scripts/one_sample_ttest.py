
import pandas as pd
from scipy import stats

# Step 1: Load the cleaned dataset
df = pd.read_csv("data/cleaned/tableA_bankwise_2019_vs_2023.csv")

# Step 2: Clean column names and convert columns
df.columns = df.columns.str.strip()

df["Bank_Type"] = df["Bank_Type"].astype(str).str.strip()

# this coverts strings to numbers for calculating mean and standard deviation
df["Vol_Pct_Change"] = pd.to_numeric(
    df["Vol_Pct_Change"].astype(str).str.strip(),
    errors="coerce"
)



# Step 3: Separate public and private sector data
public_data = df[df["Bank_Type"] == "Public"]["Vol_Pct_Change"].dropna()
private_data = df[df["Bank_Type"] == "Private"]["Vol_Pct_Change"].dropna()

# Step 4: Calculate the public sector mean
public_mean = public_data.mean()

# Step 5: Perform the one-sample t-test
t_stat, p_value = stats.ttest_1samp(
    private_data,
    popmean=public_mean
)

# Step 6: Calculate degrees of freedom
dfree = len(private_data) - 1

# Step 7: Display results
print("ONE-SAMPLE T-TEST")
print("-------------------------")

print("Public sector mean:", public_mean)
print("Private sector mean:", private_data.mean())

print("Number of public banks:", len(public_data))
print("Number of private banks:", len(private_data))

print("Reference value:", public_mean)
print("T-statistic:", t_stat)
print("Degrees of freedom:", dfree)
print("P-value:", p_value)

# Step 8: Conclusion
alpha = 0.05

if p_value < alpha:
    print("Reject the null hypothesis.")
    print("Private sector mean is significantly different from the public sector sample mean.")
else:
    print("Fail to reject the null hypothesis.")
    print("Insufficient evidence that the private sector mean differs from the public sector sample mean.")
