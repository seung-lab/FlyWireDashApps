from dash import dash_table
from dash import dcc
from dash import html
import dash_bootstrap_components as dbc
import flask
from ..common.dash_url_helper import create_component_kwargs, State

title = "Fly Neuron Summary"

# sets id of url string and ??? #
url_bar_and_content_div = html.Div(
    [dcc.Location(id="url", refresh=False), html.Div(id="page-layout")]
)

# defines function to set page layout #
def page_layout(state={}):
    # defines layout of various app elements (submission field, checkboxes, button, output table) #
    layout = html.Div(
        [
            # defines text area to relay messages #
            dbc.Textarea(
                id="message_text",
                value="Input Root IDs, Nuc IDs, or coords in 4,4,40nm\n"
                "ID queries are limited to 20 entries.\n"
                "Coordinate lookups must be done one at a time.\n"
                "Lookup takes ~2-3 seconds per entry.",
                style={
                    "width": "420px",
                    "resize": "none",
                    "margin-right": "5px",
                    "margin-left": "5px",
                    "margin-top": "5px",
                    "margin-bottom": "5px",
                },
                rows=4,
                disabled=True,
            ),
            # defines input field for ids #
            html.Div(
                [
                    dbc.Input(
                        **create_component_kwargs(
                            state,
                            id_inner="input_field",
                            type="text",
                            placeholder="Root/Nuc ID or Coords",
                            style={
                                "width": "185px",
                                "display": "inline-block",
                                "vertical-align": "top",
                                "margin-right": "5px",
                                "margin-left": "5px",
                                "margin-top": "5px",
                                "margin-bottom": "5px",
                            },
                        ),
                    ),
                    # defines submission button #
                    dbc.Button(
                        "Submit",
                        id="submit_button",
                        n_clicks=0,
                        style={
                            "width": "225px",
                            "display": "inline-block",
                            "vertical-align": "top",
                            "margin-right": "5px",
                            "margin-left": "5px",
                            "margin-top": "5px",
                            "margin-bottom": "5px",
                        },
                    ),
                ]
            ),
            # defines submit button loader #
            html.Div(
                dcc.Loading(id="submit_loader", type="default", children=""),
                style={"width": "1000px",},
            ),
            html.Br(),
            # defines output table #
            html.Div(
                dash_table.DataTable(
                    id="table",
                    style_header={
                        "whiteSpace": "normal",
                        # "height": "auto",
                        "textAlign": "center",
                    },
                    style_cell={
                        "overflow": "hidden",
                        "textOverflow": "ellipsis",
                        "maxWidth": "200px",
                        "minWidth": "105px",
                    },
                    row_selectable="multi",
                    fill_width=False,
                    tooltip_data=[],
                    tooltip_duration=None,
                ),
                style={"margin-left": "5px", "margin-right": "5px"},
            ),
            html.Div(children=[], id="post_submit_div"),
        ]
    )

    return layout


def app_layout():
    # https://dash.plotly.com/urls "Dynamically Create a Layout for Multi-Page App Validation"
    if flask.has_request_context():  # for real
        return url_bar_and_content_div
    # validation only
    return html.Div([url_bar_and_content_div, *page_layout()])
