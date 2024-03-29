from dash import dash_table
from dash import dcc
from dash import html
import dash_bootstrap_components as dbc
import flask
from ..common.dash_url_helper import create_component_kwargs


# sets app title #
title = "Fly Synapse Network Grapher"

# makes list of current url and page layout #
url_bar_and_content_div = html.Div(
    [dcc.Location(id="url", refresh=False), html.Div(id="page-layout")]
)

# defines function to set page layout #
def page_layout(state={}):
    """Create html div page layout.
    
    Keyword Arguments:
    state -- used to pass state of component values (dict of dicts, default {})
    """

    # defines layout of various app elements #
    layout = (
        html.Div(
            [
                html.Div(
                    # defines message text area for displaying instructions and feedback #
                    dbc.Textarea(
                        id="message_text",
                        value="Input up to 20 Root or Nucleus IDs separated by commas.\n"
                        "Lookup takes ~2-3 seconds per entry.",
                        disabled=True,
                        autoFocus=True,
                        rows=2,
                    ),
                    style={
                        "margin-left": "5px",
                        "margin-right": "5px",
                        "margin-top": "5px",
                        "margin-bottom": "5px",
                    },
                ),
                # html.Br(),
                # defines id input div #
                html.Div(
                    children=[
                        # defines input message #
                        dcc.Textarea(
                            id="input_message_text",
                            value="Root/Nucleus IDs:",
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
                                placeholder="Root/Nuc ID or Coords",
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
                # defines cleft score div#
                html.Div(
                    children=[
                        # defines cleft score message #
                        dcc.Textarea(
                            id="cleft_message_text",
                            value="Cleft score threshold for synapses (default 50):",
                            style={
                                "width": "355px",
                                "resize": "none",
                                "display": "inline-block",
                                "vertical-align": "top",
                            },
                            rows=1,
                            disabled=True,
                        ),
                        # defines input field for cleft score threshold #
                        dcc.Input(
                            **create_component_kwargs(
                                state,
                                id_inner="cleft_thresh_field",
                                type="number",
                                value=50,
                                style={
                                    "display": "inline-block",
                                    "width": "65px",
                                    "vertical-align": "top",
                                },
                            )
                        ),
                    ],
                    style={"margin-left": "5px", "margin-top": "5px",},
                ),
                # defines connection score div#
                html.Div(
                    children=[
                        # defines connection score message #
                        dcc.Textarea(
                            id="conn_message_text",
                            value="Minimum syns to show connection (default 1):",
                            style={
                                "width": "355px",
                                "resize": "none",
                                "display": "inline-block",
                                "vertical-align": "top",
                            },
                            rows=1,
                            disabled=True,
                        ),
                        # defines input field for connection score threshold #
                        dcc.Input(
                            **create_component_kwargs(
                                state,
                                id_inner="conn_thresh_field",
                                type="number",
                                value=1,
                                style={
                                    "display": "inline-block",
                                    "width": "65px",
                                    "vertical-align": "top",
                                },
                            )
                        ),
                    ],
                    style={"margin-left": "5px", "margin-top": "5px",},
                ),
                # defines timestamp div #
                html.Div(
                    children=[
                        # defines timestamp input message #
                        dcc.Textarea(
                            id="timestamp_message_text",
                            value="Timestamp as datetime or Unix UTC (default now):",
                            style={
                                "width": "420px",
                                "resize": "none",
                                "display": "block",
                                "vertical-align": "top",
                            },
                            rows=1,
                            disabled=True,
                        ),
                        # defines timestamp input field #
                        dcc.Input(
                            **create_component_kwargs(
                                state,
                                id_inner="timestamp_field",
                                type="text",
                                placeholder="yyyy-mm-dd hh:mm:ss",
                                style={
                                    "display": "block",
                                    "width": "420px",
                                    "vertical-align": "top",
                                },
                            )
                        ),
                    ],
                    style={"margin-left": "5px", "margin-top": "5px",},
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
                # defines submit button loader #
                html.Div(
                    dcc.Loading(id="submit_loader", type="default", children=""),
                    style={"width": "420px",},
                ),
                # defines div fornt key #
                html.Div(
                    id="key_div",
                    style={
                        "margin-left": "40px",
                        "margin-top": "3px",
                        "height": "35px",
                    },
                ),
                # defines div for post-submission content #
                html.Div(
                    id="post_submit_div",
                    style={
                        "width": "750px",
                        "height": "500px",
                        "border-style": "solid",
                        "border-width": "1px",
                        "border-color": "#eeeeee",
                        "margin-left": "5px",
                    },
                ),
            ],
        ),
    )

    return layout


def app_layout():
    """Return current layout."""
    # https://dash.plotly.com/urls "Dynamically Create a Layout for Multi-Page App Validation"
    if flask.has_request_context():  # for real
        return url_bar_and_content_div
    # validation only
    return html.Div([url_bar_and_content_div, *page_layout()])
