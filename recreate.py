import pandas as pd

sheet_dict = pd.read_excel("stock_template.xlsx", sheet_name=None, engine="openpyxl")

import os
if not os.path.exists("stock.xlsx"):
    print("stock.xlsx does not exist. Performing action.")
    with pd.ExcelWriter("stock.xlsx", engine="openpyxl") as writer:
        for sheet_name, df in sheet_dict.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            
else:
    print("stock.xlsx does exits, I will not delete it, as this could lead to a loss of valueable data")
