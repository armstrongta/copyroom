import pandas as pd
import glob
import os
from openpyxl import load_workbook
from datetime import datetime

excel_file = pd.ExcelFile("stock.xlsx")

# The Excel Sheets loaded in
df_inv = pd.read_excel(excel_file, sheet_name="inventory")
df_check_init = pd.read_excel(excel_file, sheet_name="checkouts")
person_dict = pd.read_excel(excel_file, sheet_name="person_dict")
dept_dict = pd.read_excel(excel_file, sheet_name="dept_dict")
df_copies = pd.read_excel(excel_file, sheet_name="copies_dict")

person_list = person_dict["full_name"].unique().tolist()

item_dict = df_inv.set_index("item_id")[["item_name", "price"]].to_dict(orient="index")
inverted_dict = df_inv.set_index("item_name")["item_id"].to_dict()
item_list = df_inv["item_name"].unique().tolist()

# Info Needed for the Copies Tab
add_on_df = df_copies[df_copies["type"] == "add-on"]
add_on_dict = add_on_df.set_index("item_id")["classification"].to_dict()
single_df = df_copies[df_copies["type"] == "single"]
single_dict = single_df.set_index("item_id")["classification"].to_dict()
copies_price = df_copies[["item_id", "type", "price_per_sheet", "classification"]]

# Creating the Dict to tie accounts to People
nested_dict = {}
for _, row in dept_dict.iterrows():
    dept = row["department"]
    account = row["account"]
    number = row["number"]

    if dept not in nested_dict:
        nested_dict[dept] = {}  # Initialize dictionary for the department

    nested_dict[dept][account] = number

acct_options = [] 
acct_options_copies = []
  
dtype_dict = { "item_name": "object", "quantity": "int64", "cost": "float64","memo": "object", "date": "object", "item_id": "int64", "full_name": "object",}
  
  
def supplies_send(add_df, df_check_2, selected_user, selected_acct):
    add_df["date"] = datetime.now().strftime("%m/%d/%y %I:%M %p")
    
    add_df["item_id"] = add_df["item_name"].apply(lambda x: inverted_dict.get(x))
    add_df["full_name"] = selected_user
    dept = person_dict.loc[person_dict["full_name"]==selected_user,"department"].values[0]
    add_df["acct"] = nested_dict[f"{dept}"][f"{selected_acct}"]
    add_df["quantity"] = add_df["quantity"].astype(int)
    add_df["cost"] = add_df.apply(lambda row: float(item_dict[row["item_id"]]["price"]) * row["quantity"], axis=1)
    
    df_combined = pd.concat([add_df, df_check_2], ignore_index=True)
    df_combined["quantity"] = df_combined["quantity"].astype(int)
    df_combined = df_combined.astype(dtype_dict)
    
    df_combined['memo'] = df_combined['memo'].apply(lambda x: "" if x == "Optional" else x)
    df_combined = df_combined[[ 'item_id',  'date', 'full_name', 'acct', 'item_name', 'quantity', 'cost', 'memo']]
    with pd.ExcelWriter("stock.xlsx", mode = "a", engine="openpyxl", if_sheet_exists="replace",) as writer:
        # Now write only the 'checkouts' sheet
        df_combined.to_excel(writer, sheet_name="checkouts", index=False)
    return df_combined

def copies_send(add_df, df_check_2, total, sheets, copies, date, memo, selected_user, selected_acct):
    add_df = add_df.rename(columns = {"classification": "item_name"})
    add_df = add_df[add_df["type"]!="add-on"]
    add_df = add_df.drop(columns = "type")
    
    add_df["full_name"] = selected_user
    dept = person_dict.loc[person_dict["full_name"]==selected_user,"department"].values[0]
    add_df["acct"] = nested_dict[f"{dept}"][f"{selected_acct}"]
    
    add_df["quantity"] = sheets * copies
    add_df["cost"] = total
    add_df["memo"] = memo
    add_df["date"] = date.strftime("%m/%d/%y")
    
    df_combined = pd.concat([add_df, df_check_2], ignore_index=True)
    df_combined["quantity"] = df_combined["quantity"].astype(int)
    df_combined = df_combined.astype(dtype_dict)
    
    df_combined = df_combined[[ 'item_id',  'date', 'full_name', 'acct', 'item_name', 'quantity', 'cost', 'memo']]
    with pd.ExcelWriter("stock.xlsx", mode = "a", engine="openpyxl", if_sheet_exists="replace",) as writer:
        # Now write only the 'checkouts' sheet
        df_combined.to_excel(writer, sheet_name="checkouts", index=False)
        
    return df_combined




# Define the date parsing function to handle both formats
def parse_date(date_str):
    try:
        date_str = str(date_str)
        # Try parsing with the format "MM/DD/YY"
        return datetime.strptime(date_str, "%m/%d/%y")
    except ValueError:
        try:
            # Try parsing with the format "MM/DD/YY HH:MM AM/PM"
            return datetime.strptime(date_str, "%m/%d/%y %I:%M %p")
        except ValueError:
            # If neither format works, return NaT
            return pd.NaT
            
def rep_down(df_check_2, start, end):
    try:
        # Apply the custom parsing function to the 'date' column
        df_check_2["date"] = df_check_2["date"].apply(parse_date)

        # Define the start and end date for filtering
        start_date = datetime.strptime(start, "%Y-%m-%d")
        end_date = datetime.strptime(f"{end} 23:59:59", "%Y-%m-%d %H:%M:%S")

        # Filter the DataFrame for rows where 'date' is within the specified range
        filtered_df = df_check_2[(df_check_2["date"] >= start_date) & (df_check_2["date"] <= end_date)]
        print(df_check_2.info())
        report_df = filtered_df.groupby("acct", as_index = False)["cost"].sum()
        report_df["cost"] = report_df["cost"].round(2)
        
        # Format the start and end dates for the filename
        start_str = datetime.strptime(start, "%Y-%m-%d").strftime("%m-%d")
        end_str = datetime.strptime(end, "%Y-%m-%d").strftime("%m-%d")
        filename = f"{start_str}_to_{end_str}_financial_report.xlsx"

        
        # Delete any existing files that end with "report.xlsx"
        for file in glob.glob("*report.xlsx"):
            os.remove(file)
        # Save report_df to an Excel file with the formatted filename
        report_df.to_excel(filename, index=False)
        return ""
    except Exception as e:
        return f"Errored {(e)}"
    
    