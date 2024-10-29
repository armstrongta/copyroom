from pathlib import Path

from shiny import ui

my_theme = (
    ui.Theme("flatly")
    .add_defaults(
        info="#765576"
        # primary = "#as8745s", secondary = ,success = ,info = ,warning= ,danger= ,
    )
    .add_rules(
        """
            .card.bslib-card.bslib-mb-spacing.html-fill-container {
                background-color: #ecdfdc;
                color: #375a7f;
                }
            .navbar.navbar-expand-md.navbar-default {
                background-color: #375a7f !important;
            }
            """
    )
)

with open(Path(__file__).parent / "css/my_theme.css", "w") as f:
    f.write(my_theme.to_css())


