import pandas as pd

sheet_dict = pd.read_excel("stock_template.xlsx", sheet_name=None, engine="openpyxl")

with pd.ExcelWriter("stock.xlsx", engine="openpyxl") as writer:
    for sheet_name, df in sheet_dict.items():
        df.to_excel(writer, sheet_name=sheet_name, index=False)
