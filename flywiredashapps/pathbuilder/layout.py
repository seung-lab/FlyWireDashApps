from dash import dash_table
from dash import dcc
from dash import html
import dash_bootstrap_components as dbc
import flask
from ..common.dash_url_helper import create_component_kwargs, State

title = "Fly Synaptic Pathway Builder"

# sets id of url string and ??? #
url_bar_and_content_div = html.Div(
    [dcc.Location(id="url", refresh=False), html.Div(id="page-layout")]
)

# defines function to set page layout #
def page_layout(state={}):
    # defines layout of various app elements #
    layout = (
        html.Div(
            [
                html.Div(
                    dbc.Textarea(
                        id="message_text",
                        value=(
                            'Input root ID and click "Submit" button.'
                            + " Only one entry at a time."
                            + " Large queries may take several minutes."
                        ),
                        disabled=True,
                        autoFocus=True,
                    ),
                    style={
                        "margin-left": "5px",
                        "margin-right": "5px",
                        "margin-top": "5px",
                        "margin-bottom": "5px",
                    },
                ),
                html.Br(),
                # defines container for input message and field #
                html.Div(
                    children=[
                        # defines input message #
                        dcc.Textarea(
                            id="input_message_text",
                            value="Root ID:",
                            style={
                                "width": "242px",
                                "resize": "none",
                                "display": "inline-block",
                                "vertical-align": "top",
                            },
                            rows=1,
                            disabled=True,
                        ),
                        # defines input field #
                        dcc.Input(
                            **create_component_kwargs(
                                state,
                                id_inner="input_field",
                                type="text",
                                placeholder="Root ID",
                                style={
                                    "width": "178px",
                                    "display": "inline-block",
                                    "vertical-align": "top",
                                },
                            )
                        ),
                    ],
                    style={"margin-left": "5px",},
                ),
                # defines container for synapse threshold message and field #
                html.Div(
                    children=[
                        # defines synapse threshold message #
                        dcc.Textarea(
                            id="thresh_message_text",
                            value="Minimum number of synapses (default 10):",
                            style={
                                "width": "355px",
                                "resize": "none",
                                "display": "inline-block",
                                "vertical-align": "top",
                            },
                            rows=1,
                            disabled=True,
                        ),
                        # defines input field for synapse threshold #
                        dcc.Input(
                            **create_component_kwargs(
                                state,
                                id_inner="thresh_field",
                                type="number",
                                value=10,
                                style={
                                    "display": "inline-block",
                                    "width": "65px",
                                    "vertical-align": "top",
                                },
                            )
                        ),
                        # defines sumbission button #
                        dbc.Button(
                            id="submit_button",
                            children=["Submit",],
                            style={
                                "display": "inline-block",
                                "width": "420px",
                                "margin-left": "5px",
                                "margin-right": "5px",
                                "margin-top": "5px",
                                "margin-bottom": "5px",
                            },
                        ),
                    ],
                    style={"margin-left": "5px", "margin-top": "5px",},
                ),
            ],
        ),
    )

    return layout


def app_layout():
    # https://dash.plotly.com/urls "Dynamically Create a Layout for Multi-Page App Validation"
    if flask.has_request_context():  # for real
        return url_bar_and_content_div
    # validation only
    return html.Div([url_bar_and_content_div, *page_layout()])
