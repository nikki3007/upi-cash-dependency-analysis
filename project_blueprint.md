# Project Blueprint: UPI Growth vs. ATM Withdrawals (2019 vs. 2023)
*Methodology Update: Percentage Change & Dual Hypothesis Testing*

This document outlines the workflow for analyzing the substitution effect between digital payments (UPI) and cash withdrawals (ATM), comparing Public vs. Private sector banks.

## Part 1: The Data Engineer's Role

The Data Engineer is responsible for extracting, cleaning, and transforming the raw RBI and NPCI data. To eliminate the "size effect" (where giant banks mathematically overshadow small banks), the core metric is the **Percentage Change** in average monthly volumes.

### Key Tasks:
1. **Temporal Filtering:** Isolate the data strictly for the 12 months of 2019 and the 12 months of 2023.
2. **Metric Aggregation:** Calculate the "Average Monthly Volume" (number of transactions) and "Average Monthly Value" (amount in Rupees) for both years.
3. **Categorization:** Manually map the raw RBI bank names to a new categorical variable (`Bank_Type`): "Public" or "Private".
4. **Percentage Change Calculation:** Compute the standardized shift for each bank using this formula:
   `%_Change = ((Avg_Monthly_2023 - Avg_Monthly_2019) / Avg_Monthly_2019) * 100`

### Target Data Schemas

**Table A: Bank-Level Analysis Table (For T-Tests)**
This table provides the standardized arrays fed directly into the statistical tests.

| Bank_Name | Bank_Type | Avg_Vol_2019 | Avg_Vol_2023 | Vol_Pct_Change | Avg_Val_2019 | Avg_Val_2023 | Val_Pct_Change |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| State Bank of India | Public | 15000 | 12000 | **-20.0%** | 50M | 45M | **-10.0%** |
| HDFC Bank | Private | 12000 | 6000 | **-50.0%** | 40M | 30M | **-25.0%** |
| Punjab National Bank | Public | 10000 | 8500 | **-15.0%** | 30M | 28M | **-6.6%** |

**Table B: Macro Time-Series Table (For Visuals & Correlation)**
Used to plot the inverse relationship between national UPI growth and ATM decline over time.

| Month_Year | National_UPI_Volume | Total_Public_ATM_Vol | Total_Private_ATM_Vol |
| :--- | :--- | :--- | :--- |
| Jan-2019 | [NPCI Data] | [Sum of Public] | [Sum of Private] |
| Feb-2019 | [NPCI Data] | [Sum of Public] | [Sum of Private] |
| ... | ... | ... | ... |

---

## Part 2: The Statistician's Role

The Statistician uses Table A to prove the statistical significance of the sector gap. To satisfy syllabus constraints while delivering a highly rigorous analysis, the statistician will execute two different testing frameworks.

### Method 1: The One-Sample "National Anchor" Test (Syllabus Compliant)
**Goal:** To prove that Public and Private banks behaved fundamentally differently by comparing each to the overall industry average.

* **Step 1: Calculate the Anchor:** Find the mean `Vol_Pct_Change` across *all* banks combined. Let's assume this National Average is $-30\%$.
* **Step 2: Test Private Banks against the Anchor:**
  * **$H_0$:** $\mu_{private} = -30$ (Private banks match the national average).
  * **$H_1$:** $\mu_{private} \neq -30$ (Private banks differ significantly from the national average).
* **Step 3: Test Public Banks against the Anchor:**
  * **$H_0$:** $\mu_{public} = -30$ (Public banks match the national average).
  * **$H_1$:** $\mu_{public} \neq -30$ (Public banks differ significantly from the national average).
* **Conclusion Strategy:** If private banks test significantly *below* the anchor and public banks test significantly *above* it, you have mathematically justified the sector gap using only the one-sample method taught in class.

### Method 2: Welch's Two-Sample Independent T-Test (Advanced / Bonus)
**Goal:** To directly compare the two sectors against each other to calculate the exact probability that the gap between them is real.

* **Data Used:** The `Vol_Pct_Change` column, split into Array 1 (Public) and Array 2 (Private).
* **Hypotheses:**
  * **$H_0$:** $\mu_{public} = \mu_{private}$ (The mean percentage drop is identical across both sectors).
  * **$H_1$:** $\mu_{public} \neq \mu_{private}$ (There is a statistically significant difference in how the two sectors' customers reduced cash usage).
* **Formula:**
  $$t = \frac{\bar{X}_1 - \bar{X}_2}{\sqrt{\frac{s_1^2}{n_1} + \frac{s_2^2}{n_2}}}$$
* **Conclusion Strategy:** This provides the undeniable, direct proof of your core research question. Presenting this alongside Method 1 demonstrates a mastery of the syllabus and independent advanced analytical capability.

### Visual Validation (EDA)
Regardless of the test used, the Statistician must generate a side-by-side **Box Plot** of the `Vol_Pct_Change` for Public vs. Private banks. If the "boxes" (interquartile ranges) do not heavily overlap, it provides immediate visual confirmation of the calculated p-values.