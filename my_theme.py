from pathlib import Path

from shiny import ui
import pandas as pd

excel_file = pd.ExcelFile("stock.xlsx")
df_school = pd.read_excel(excel_file, sheet_name="school")
school_name = df_school["School Name"].iloc[0]

if school_name == "Fremont":
    my_theme = (
        ui.Theme("flatly")
        .add_defaults(
            success="#293d00",
            info="#3d000a",
            # primary = "#as8745s", secondary = ,,info = ,warning= ,danger= ,
        )
        .add_rules(
            """
                .card.bslib-card.bslib-mb-spacing.html-fill-container {
                    background-color: #e0dfd2;
                    color: #375a7f;
                    }
                .navbar.navbar-expand-md.navbar-default {
                    background-color: #375a7f !important;
                }
                """
        )
    )
    
# elif school_name == "Weber":

with open(Path(__file__).parent / "assets/my_theme.css", "w") as f:
    f.write(my_theme.to_css())


