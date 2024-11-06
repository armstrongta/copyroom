# Run Statement below:
#  & c:\Users\18015\OneDrive\repo\copy_room_inventory\.conda\python.exe -m shiny run --port 58597 c:\Users\18015\OneDrive\repo\copy_room_inventory\app.py

# Hours Tanner has worked on this: 35  8:30- 
from shiny import App, render, ui, reactive
import pandas as pd
from openpyxl import load_workbook
from datetime import datetime
from dateutil.relativedelta import relativedelta
from myfunctions import supplies_send, copies_send, rep_down
from pathlib import Path
from htmltools import css
#import faicons
here = Path(__file__).parent

#* From here to dtype_dict is a dataload, copied in explore.ipynb, app.py, myfunctions.py
# Note: I would have create a data_prep function, but here would have been 20 returned values
excel_file = pd.ExcelFile("stock.xlsx")

# The Excel Sheets loaded in
df_inv = pd.read_excel(excel_file, sheet_name="inventory")
df_check_init = pd.read_excel(excel_file, sheet_name="checkouts")
person_dict = pd.read_excel(excel_file, sheet_name="person_dict")
dept_dict = pd.read_excel(excel_file, sheet_name="dept_dict")
df_copies = pd.read_excel(excel_file, sheet_name="copies_dict")
# Grab details specific to the school:
df_school = pd.read_excel(excel_file, sheet_name="school")
school_name = df_school["School Name"].iloc[0]
background_link = df_school["background_link"].iloc[0]
buffer_amount = df_school["buffer_amount"].iloc[0]
copy_person = df_school["users_name"].iloc[0]

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



#-------------------------------------------------Copyroom Supplies UI Section-----------------------------------------------------------
app_ui = ui.page_navbar(
    ui.nav_panel(
        "Copyroom Supplies",
        ui.page_fillable(
            ui.layout_columns(
                ui.card(
                    ui.input_selectize(
                        "user",
                        "Type in your LAST name",
                        sorted(person_list),
                        selected="Steve Rogers",
                    ),
                    ui.input_selectize(
                        "acct_select", "Select an Account", choices=acct_options
                    ),
                    ui.input_selectize(
                        "items",
                        "Select the Item(s) you are taking:",
                        item_list,
                        multiple=True,
                    ),
                    min_height="575px",
                ),
                ui.card(
                    ui.tags.p(
                        "Double Click the box to adjust quantity or memo",
                        style="color: red; font-weight: bold;",
                    ),
                    ui.output_data_frame("checkout_df"),
                    ui.input_action_button("send", "Submit", class_="btn-success"),
                    ui.output_text("sendoff"),
                    fill=False,
                ),
                col_widths=(4, 5),
            ),
            style=css(
                background_image=f"url({background_link})",
                background_repeat="no-repeat",
                background_size="cover",
                background_position=f"center {buffer_amount}px",
            ),
        ),
    ),
    ui.nav_panel(
        "Copies",
        ui.output_ui("copies_ui"),
    ),
    ui.nav_panel("Report Generator", ui.output_ui("report_ui")),
    title=ui.tags.div(
        ui.tags.div(
            "Copyroom App", style="margin-right: 10px;"
        ),  # Text div with spacing
        ui.output_image("logo", inline=True),  # Image output inline
        style="display: flex; align-items: center;",
    ),
    theme=here / "assets/my_theme.css",
)


def server(input, output, session):
    @render.image
    def logo():
        img = {"src" : here / "assets/school_logo.jpeg", "width": "40px", "height": "30px"}
        return img
    
    
    
# -------------------------------------------------Server: Copyroom Supplies-----------------------------------
    df_check = reactive.value(df_check_init)
    
    @reactive.effect
    def update_acct_options():
        selected_user = input.user()   
        print(f"selected: {selected_user}")
        try:
            dept = person_dict.loc[person_dict["full_name"]==selected_user,"department"].values[0]
            acct_options = list(nested_dict.get(dept, {}).keys())
            acct_options = sorted(acct_options)
            ui.update_select("acct_select", choices = acct_options)
        except:
            print("Couldn't find person or dept")


    @render.data_frame
    def checkout_df():
        items = input.items()
        item_prices = []
        for item in items:
            item_price = df_inv.loc[df_inv["item_name"] == item, "price"].iloc[0]
            item_prices.append(item_price)
            
        checkout = pd.DataFrame(list(zip(items, item_prices)), columns=["item_name", "Price per Item"])
        checkout["quantity"] = 1
        checkout["memo"] = "Optional"
        
        return render.DataGrid(checkout, editable=True,)
    
    @render.text()
    @reactive.event(input.send)
    def sendoff():
        selected_user = input.user()
        selected_acct = input.acct_select()
        add_df = checkout_df.data_view()
        add_df = add_df.drop(columns = ["Price per Item"])
        df_check_2 = df_check()
        
        if selected_user == "Steve Rogers":
            return "That can't be right, is it really you Captain America?"
        if not add_df["item_name"].isin(inverted_dict.keys()).all():
            return "Error, you are not allowed to change the item_name. Please Delete the items selected, and try again. If your item is not listed, please leave a note for Karrie"
        
        
        df_combined = supplies_send(add_df, df_check_2, selected_user, selected_acct)
        
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
                    ui.input_selectize( "user_copies", "Which Teacher?", sorted(person_list), selected = "Steve Rogers"),
                    ui.input_selectize("acct_select_copies", "Select an Account", choices = sorted(acct_options_copies)), 
                    ui.input_checkbox_group("add_ons", "Desired Add-ons", add_on_dict),
                    ui.input_selectize("single", "Paper Type", single_dict)
                ),
                ui.card(
                    ui.output_data_frame("copies_calc"),
                    ui.input_numeric("sheets", "Pages (after copied)", 1, min=1), 
                    ui.input_numeric("copies", "Copies of each", 1, min=1),
                    ui.input_date("copy_date", "Date Needed", format = "mm/dd/yy"),
                    fill = False,
                ),
                ui.card(
                    ui.output_text_verbatim("copies_sum"),
                    ui.output_ui("copy_memo_ui"),
                    ui.input_action_button("send_copies", "Submit", class_="btn-success"),
                    ui.output_text("sendoff_copies"), 
                    fill = False,
                    
                ),
            col_widths = (2,3,5), height = '575px'
            ),
        ),
    
    
    
# -------------------------------------------------Server: Copies tab-----------------------------------
    price_per = reactive.value(0.0)
    total = reactive.value(0.0)
    add_ons_list = reactive.value("")
    add_copy = reactive.value(pd.DataFrame(columns = ['item_id', 'classification']))

    @reactive.effect
    def update_acct_options_copies():
        try:
            selected_user = input.user_copies()

            dept = person_dict.loc[
                person_dict["full_name"] == selected_user, "department"
            ].values[0]
            acct_options_copies = list(nested_dict.get(dept, {}).keys())
            ui.update_select("acct_select_copies", choices=acct_options_copies)
        except:
            print("Couldn't find the person")
        
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
        selected_acct = input.acct_select_copies()
        add_df = add_copy()
        df_check_2 = df_check()
        total_2 = total.get()
        date = input.copy_date()
        memo = input.copy_memo()
        sheets = input.sheets()
        copies = input.copies()
        
        if selected_user == "Steve Rogers":
            return "That can't be right, Did Captain America order copies again?!"
        
        
        
        df_combined = copies_send(add_df, df_check_2, total_2, sheets, copies, date, memo, selected_user, selected_acct)
        
        ui.update_selectize("user_copies", selected="Steve Rogers")
        ui.update_checkbox_group("add_ons", selected = [])
        ui.update_selectize("single", selected = 1004)
        df_check.set(df_combined)
        return f"You're doing Great {copy_person}! I'm sure {selected_user} appreciates it :)"
    

# -------------------------------------------------Server: Report tab----------------------------------- 
    today = datetime.today()

    first_day_prev_month = (today.replace(day=1) - relativedelta(months=1)).strftime("%Y-%m-%d")
    last_day_prev_month = (today.replace(day=1) - relativedelta(days=1)).strftime("%Y-%m-%d")
    
    @render.ui
    def report_ui():
        return ui.page_fillable(
            ui.layout_columns(
                ui.card((ui.input_date_range("daterange", "Date range", start=first_day_prev_month, end = last_day_prev_month, format = 'mm-dd-yyyy'),),
                        ui.input_action_button("report_create", "Download Report", class_ = "btn-info"),
                        ui.output_text("report_done"),
                ),
                col_widths = (3)
            ),
        )


# -------------------------------------------------UI: Report tab-----------------------------------
    @render.text()
    @reactive.event(input.report_create)
    def report_done():
        start = str(input.daterange()[0])
        end = str(input.daterange()[1])
        df_check_2 = df_check()
        
        finish = rep_down(df_check_2, start, end)
        return f"Report Downloaded. {finish}"
        



app = App(app_ui, server)


# TODO Shiny io or Aws for a server
"""
Why if refresh the page the checkouts disappear. 

Staples only add on per copy. 

Put every function in try except brackets. Return the errors

Tab for editting checkout data:
    delete rows, edit rows, sorting and filtering



#* What you'd like to see:
# add comments to this code.
# Add in automated emails/ start tracking inventory.
"""