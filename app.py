# Run Statement below:
#  & c:\Users\18015\OneDrive\repo\copy_room_inventory\.conda\python.exe -m shiny run --port 58597 c:\Users\18015\OneDrive\repo\copy_room_inventory\app.py

# Hours Tanner has worked on this: 14
from shiny import App, render, ui, reactive
import pandas as pd
from openpyxl import load_workbook
from datetime import datetime
#import faicons


excel_file = pd.ExcelFile("stock_template.xlsx")

df_inv = pd.read_excel(excel_file, sheet_name="inventory")
df_check_init = pd.read_excel(excel_file, sheet_name="checkouts")
person_dict = pd.read_excel(excel_file, sheet_name="person_dict")
dept_dict = pd.read_excel(excel_file, sheet_name="dept_dict")

person_list = person_dict["full_name"].unique().tolist()

item_dict = df_inv.set_index("item_id")["item_name"].to_dict()
inverted_dict = {v: k for k, v in item_dict.items()}
item_list = df_inv["item_name"].unique().tolist()

nested_dict = {}
for _, row in dept_dict.iterrows():
    dept = row["department"]
    account = row["account"]
    number = row["number"]

    if dept not in nested_dict:
        nested_dict[dept] = {}  # Initialize dictionary for the department

    nested_dict[dept][account] = number

acct_options = [] 
  
dtype_dict = { "item_name": "object", "quantity": "int64", "memo": "object", "date": "object", "item_id": "int64", "full_name": "object",}
  

app_ui = ui.page_navbar(
    ui.nav_panel("Copyroom Supplies",
        ui.page_fillable(
            ui.layout_columns(
                ui.card(
                    ui.input_selectize( "user", "What is your name?", person_list, selected = "Steve Rogers"),
                    ui.input_select("acct_select", "Select an Account", choices = acct_options), #Choose default dept
                    ui.input_selectize( "items", "Select the Item(s) you are taking:", item_list, multiple=True), min_height = 600
                ),
                ui.card(
                    ui.tags.p("Double Click to adjust quantity or memo", style="color: green; font-weight: bold;"),
                    ui.output_data_frame("checkout_df"),
                    ui.input_action_button("send", "Submit", class_="btn-success"),
                    ui.output_text("sendoff"), 
                ),
            col_widths = (4,5)
            ),
        ),
    ),
    
    ui.nav_panel("Add dept/person", "hey"),
    ui.nav_panel("Copies", "How Many?!")
    
)

def server(input, output, session):
    df_check = reactive.value(df_check_init)
    
    @reactive.effect
    def update_acct_options():
        selected_user = input.user()   

        dept = person_dict.loc[person_dict["full_name"]==selected_user,"department"].values[0]
        acct_options = list(nested_dict.get(dept, {}).keys())
        ui.update_select("acct_select", choices = acct_options)

    @render.data_frame
    def checkout_df():
        checkout = pd.DataFrame(input.items(), columns=["item_name"])
        checkout["quantity"] = 1
        checkout["memo"] = "Optional"
        
        return render.DataGrid(checkout, editable=True,)
    
    @render.text()
    @reactive.event(input.send)
    def sendoff():

        selected_user = input.user()
        if selected_user == "Steve Rogers":
            return "That can't be right, is it really you Captain America?"
        
        selected_acct = input.acct_select()
        
        add_df = checkout_df.data_view()
        add_df["date"] = datetime.now().strftime("%m/%d/%y %I:%M %p")
        add_df["item_id"] = add_df["item_name"].apply(lambda x: inverted_dict.get(x))
        add_df["full_name"] = selected_user
        dept = person_dict.loc[person_dict["full_name"]==selected_user,"department"].values[0]
        add_df["acct"] = nested_dict[f"{dept}"][f"{selected_acct}"]
        
        df_check_2 = df_check()
        df_combined = pd.concat([add_df, df_check_2], ignore_index=True)
        df_combined["quantity"] = df_combined["quantity"].astype(int)
        df_combined = df_combined.astype(dtype_dict)
        
        df_combined['memo'] = df_combined['memo'].apply(lambda x: "" if x == "Optional" else x)
        df_combined = df_combined[[ 'item_id',  'date', 'full_name', 'acct', 'item_name', 'quantity',  'memo']]
        with pd.ExcelWriter("stock_template.xlsx", mode = "a", engine="openpyxl", if_sheet_exists="replace",) as writer:
            # Now write only the 'checkouts' sheet
            df_combined.to_excel(writer, sheet_name="checkouts", index=False)
        
        ui.update_selectize("items", choices = item_list, selected=None)
        df_check.set(df_combined)
        return f"Thank you {selected_user}!"


app = App(app_ui, server)


#! Upload to github
# TODO Shiny io or Aws for a server

# Best just to open the Excel file and use Ctrl+f for all edits?
# (name editor tab, inventory update/insert)
# enter/edit account information. add new teacher/department, enter copies tab.
#Future edit costs tab, edit checkouts tab




#* Questions:
# Automatic Ordering? Using link, send an email to order more


#* What I need:
# Fill in your excel stock sheet. External monitor for everyone to use? Or a new laptop?


#* What you'd like to see: