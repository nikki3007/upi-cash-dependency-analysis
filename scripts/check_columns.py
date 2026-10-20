import pandas as pd

files = [
    "raw_rbi/2019/APR 2019.XLSX",
    "raw_rbi/2023/APR.XLSX"
]

for file in files:
    df = pd.read_excel(file, header=None)

    print("\nFILE:", file)
    print(df.iloc[:15, :].to_string(index=True, header=True))

    bank_col = df.iloc[:, 2].astype(str).str.upper()
    hdfc = df[bank_col.str.contains("HDFC BANK", na=False)]

    print("\nHDFC ROW:")
    print(hdfc.to_string(index=True, header=True))