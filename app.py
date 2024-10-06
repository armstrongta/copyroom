# Run Statement below:
#  & c:\Users\18015\OneDrive\repo\copy_room_inventory\.conda\python.exe -m shiny run --port 58597 c:\Users\18015\OneDrive\repo\copy_room_inventory\app.py

# Hours Tanner has worked on this: 17. 11:30
from shiny import App, render, ui, reactive
import pandas as pd
from openpyxl import load_workbook
from datetime import datetime
from myfunctions import data_prep
#import faicons


excel_file = pd.ExcelFile("stock.xlsx")

df_inv = pd.read_excel(excel_file, sheet_name="inventory")
df_check_init = pd.read_excel(excel_file, sheet_name="checkouts")
person_dict = pd.read_excel(excel_file, sheet_name="person_dict")
dept_dict = pd.read_excel(excel_file, sheet_name="dept_dict")
df_copies = pd.read_excel(excel_file, sheet_name="copies_dict")

person_list = person_dict["full_name"].unique().tolist()

item_dict = df_inv.set_index("item_id")[["item_name", "price"]].to_dict(orient="index")
inverted_dict = df_inv.set_index("item_name")["item_id"].to_dict()
item_list = df_inv["item_name"].unique().tolist()

add_on_df = df_copies[df_copies["type"] == "add-on"]
add_on_dict = add_on_df.set_index("item_id")["classification"].to_dict()
single_df = df_copies[df_copies["type"] == "single"]
single_dict = single_df.set_index("item_id")["classification"].to_dict()
copies_price = df_copies[["item_id", "type", "price_per_sheet", "classification"]]

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
  


#-------------------------------------------------App UI Section-----------------------------------------------------------
app_ui = ui.page_navbar(
    ui.nav_panel("Copyroom Supplies",
        ui.page_fillable(
            ui.layout_columns(
                ui.card(
                    ui.input_selectize( "user", "What is your name?", person_list, selected = "Steve Rogers"),
                    ui.input_select("acct_select", "Select an Account", choices = acct_options),
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
    
    ui.nav_panel("Copies", 
        ui.output_ui("copies_ui"),
    ),
    ui.nav_panel("Report Generator", "Dates")
    
)

# -------------------------------------------------Server: Copyroom Supplies tab-----------------------------------
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
        
        if not add_df["item_name"].isin(inverted_dict.keys()).all():
            return "Error, you are not allowed to change the item_name. Please Delete the items selected, and try again"
        
        add_df["item_id"] = add_df["item_name"].apply(lambda x: inverted_dict.get(x))
        add_df["full_name"] = selected_user
        dept = person_dict.loc[person_dict["full_name"]==selected_user,"department"].values[0]
        add_df["acct"] = nested_dict[f"{dept}"][f"{selected_acct}"]
        add_df["cost"] = add_df.apply(lambda row: float(item_dict[row["item_id"]]["price"]) * row["quantity"], axis=1)
        
        df_check_2 = df_check()
        df_combined = pd.concat([add_df, df_check_2], ignore_index=True)
        df_combined["quantity"] = df_combined["quantity"].astype(int)
        df_combined = df_combined.astype(dtype_dict)
        
        df_combined['memo'] = df_combined['memo'].apply(lambda x: "" if x == "Optional" else x)
        df_combined = df_combined[[ 'item_id',  'date', 'full_name', 'acct', 'item_name', 'quantity', 'cost', 'memo']]
        with pd.ExcelWriter("stock.xlsx", mode = "a", engine="openpyxl", if_sheet_exists="replace",) as writer:
            # Now write only the 'checkouts' sheet
            df_combined.to_excel(writer, sheet_name="checkouts", index=False)
        
        ui.update_selectize("items", choices = item_list, selected=None)
        ui.update_selectize("user", selected="Steve Rogers")
        df_check.set(df_combined)
        return f"Thank you {selected_user}!"



# -------------------------------------------------UI: Copies tab-----------------------------------    
    @ render.ui
    def copies_ui():
        return ui.page_fillable(
            ui.layout_columns(
                ui.card(
                    ui.input_selectize( "user_copies", "Which Teacher?", person_list, selected = "Steve Rogers"),
                    ui.input_select("acct_select_copies", "Select an Account", choices = acct_options_copies), 
                    ui.input_checkbox_group("add_ons", "Desired Add-ons", add_on_dict),
                    ui.input_selectize("single", "Paper Type", single_dict)
                ),
                ui.card(
                    ui.output_data_frame("copies_calc"),
                    ui.input_numeric("sheets", "Pages (after copied)", 1, min=1), 
                    ui.input_numeric("copies", "Copies of each", 1, min=1),
                    ui.input_date("copy_date", "Date Needed", format = "mm/dd/yy")
                ),
                ui.card(
                    ui.output_text_verbatim("copies_sum"),
                    ui.output_ui("copy_memo_ui"),
                    ui.input_action_button("send_copies", "Submit", class_="btn-success"),
                    ui.output_text("sendoff_copies"), 
                    
                ),
            col_widths = (2,3,5), height = '600px'
            ),
        ),
    
    
    
# -------------------------------------------------Server: Copies tab-----------------------------------
    price_per = reactive.value(0.0)
    total = reactive.value(0.0)
    add_ons_list = reactive.value("")
    add_copy = reactive.value(pd.DataFrame(columns = ['item_id', 'classification']))

    @reactive.effect
    def update_acct_options_copies():
        selected_user = input.user_copies()

        dept = person_dict.loc[
            person_dict["full_name"] == selected_user, "department"
        ].values[0]
        acct_options_copies = list(nested_dict.get(dept, {}).keys())
        ui.update_select("acct_select_copies", choices=acct_options_copies)
        
    @render.data_frame
    def copies_calc():
        copies = pd.DataFrame(input.add_ons(), columns=["item_id"])
        copies_2 = pd.DataFrame([input.single()], columns=["item_id"])
        copies = pd.concat([copies, copies_2], ignore_index=True)
        copies["item_id"] = copies["item_id"].astype("int64")
        copies = copies.merge(copies_price, on="item_id", how="left")
        
        addon = copies[copies["type"]=="add-on"]
        addon = addon["classification"].tolist()
        add_ons_list.set(addon)
        
        add_copy_df = copies[["item_id", "classification", "type"]]
        add_copy.set(add_copy_df)
        
        copies = copies[["classification", "price_per_sheet"]]
        cost = copies["price_per_sheet"].sum()
        cost = round(cost,2)
        price_per.set(cost)
        return render.DataTable(copies, height = '200px')
    
    @render.text
    def copies_sum():
        per = price_per()
        total_here = input.sheets()*input.copies()*per
        total_here = round(total_here, 2)
        total.set(total_here)
        date = input.copy_date()
        date = date.strftime("%B %d, %Y")
        return f"For {input.copies()} Copies of {input.sheets()} Pages at ${per} = ${total_here}\nCharged to {input.user_copies()} on {date}"
    
    @render.ui
    def copy_memo_ui():
        addon_list = add_ons_list.get()
        memo_value = ""
        if addon_list != []:
            memo_value = ', '.join(add_ons_list.get())
        return ui.input_text_area( "copy_memo", "Notes: (Add-ons, Color, or Special Instructions)", value=memo_value, width="500px")
    
    @render.text()
    @reactive.event(input.send_copies)
    def sendoff_copies():
        selected_user = input.user_copies()
        if selected_user == "Steve Rogers":
            return "That can't be right, Did Captain America order copies again?!"
        
        selected_acct = input.acct_select_copies()
        
        add_df = add_copy()
        add_df = add_df.rename(columns = {"classification": "item_name"})
        add_df = add_df[add_df["type"]!="add-on"]
        add_df = add_df.drop(columns = "type")
        
        add_df["full_name"] = selected_user
        dept = person_dict.loc[person_dict["full_name"]==selected_user,"department"].values[0]
        add_df["acct"] = nested_dict[f"{dept}"][f"{selected_acct}"]
        
        add_df["quantity"] = input.sheets() * input.copies()
        add_df["cost"] = total.get()
        add_df["memo"] = input.copy_memo()
        date = input.copy_date()
        add_df["date"] = date.strftime("%m/%d/%y")
        
        df_check_2 = df_check()
        df_combined = pd.concat([add_df, df_check_2], ignore_index=True)
        df_combined["quantity"] = df_combined["quantity"].astype(int)
        df_combined = df_combined.astype(dtype_dict)
        
        df_combined = df_combined[[ 'item_id',  'date', 'full_name', 'acct', 'item_name', 'quantity', 'cost', 'memo']]
        with pd.ExcelWriter("stock.xlsx", mode = "a", engine="openpyxl", if_sheet_exists="replace",) as writer:
            # Now write only the 'checkouts' sheet
            df_combined.to_excel(writer, sheet_name="checkouts", index=False)
        
        ui.update_selectize("user_copies", selected="Steve Rogers")
        ui.update_checkbox_group("add_ons", selected = [])
        ui.update_selectize("single", selected = 1004)
        df_check.set(df_combined)
        return f"You're doing Great Karrie! I'm sure {selected_user} appreciates it :)"
    

app = App(app_ui, server)


#! Upload to github
# TODO Shiny io or Aws for a server

#* Teach how:
# to ctrl + F/add filters in excel for edits
# make app run in browser by default

#* What I need:
# Fill in your excel stock sheet. External monitor for everyone to use? Or a new laptop?

#* Questions
# Do people ever wonder the price? Would they like to know? (use patches to fill in price column with an effect)


#* What you'd like to see:
# add comments
# Add report download page, copies 1000+
# Data backed up somewhere
# Make sure that new pulls don't effect what is in stock file
# Fremont Theme