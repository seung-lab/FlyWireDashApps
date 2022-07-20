from dash import dash_table
from dash import dcc
from dash import html
import dash_bootstrap_components as dbc
import flask
import datetime
from .utils import getTime
from ..common.dash_url_helper import create_component_kwargs, State

title = "Fly Connectivity Viewer"

# sets id of url string and ??? #
url_bar_and_content_div = html.Div(
    [dcc.Location(id="url", refresh=False), html.Div(id="page-layout")]
)

# defines function to set page layout #
def page_layout(state={}):
    # defines layout of various app elements #
    layout = html.Div(
        [
            html.Div(
                dbc.Textarea(
                    id="message_text",
                    value=(
                        'Input root/nuc ID or coordinates and click "Submit" button.'
                        + " Only one entry at a time."
                        + " Large queries (>100k synapses) may take up to 2 minutes."
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
                        value="Root/nucleus ID or x,y,z coords:",
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
            # defines container for cleft score message and field #
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
            html.Div(
                children=[
                    # defines filter list input message #
                    dcc.Textarea(
                        id="filter_list_message_text",
                        value="List of root IDs to filter results (optional)",
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
                            id_inner="filter_list_field",
                            type="text",
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
                style={"width": "1000px",},
            ),
            html.Br(),
            # defines neurotransmitter plot display div #
            html.Div(
                id="graph_div",
                children=[],
                style={
                    "display": "inline-block",
                    "margin-top": "10px",
                    "margin-bottom": "10px",
                },
            ),
            html.Br(),
            # defines div for holding download summary button #
            html.Div(children=[], id="post_submit_download__summary"),
            # defines summary table #
            html.Div(
                dash_table.DataTable(
                    id="summary_table",
                    style_header={
                        "whiteSpace": "normal",
                        "height": "auto",
                        "textAlign": "center",
                    },
                ),
                style={
                    "margin-left": "5px",
                    "margin-right": "5px",
                    "margin-top": "5px",
                    "margin-bottom": "5px",
                },
            ),
            # defines div for holding upstream download button #
            html.Div(children=[], id="post_submit_download__upstream"),
            # defines incoming table #
            html.Div(
                dash_table.DataTable(
                    id="incoming_table", page_size=5, row_selectable="multi",
                ),
                style={"margin-left": "5px", "margin-right": "5px",},
            ),
            # defines div for holding downstream download button #
            html.Div(children=[], id="post_submit_download__downstream"),
            # defines outgoing table #
            html.Div(
                dash_table.DataTable(
                    id="outgoing_table", page_size=5, row_selectable="multi",
                ),
                style={"margin-left": "5px", "margin-right": "5px",},
            ),
            # defines div for holding post-submission download buttons #
            html.Div(children=[], id="post_submit_linkbuilder_buttons"),
        ]
    )

    return layout


def app_layout():
    # https://dash.plotly.com/urls "Dynamically Create a Layout for Multi-Page App Validation"
    if flask.has_request_context():  # for real
        return url_bar_and_content_div
    # validation only
    return html.Div([url_bar_and_content_div, *page_layout()])
