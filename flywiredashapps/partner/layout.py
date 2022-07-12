from dash import dash_table
from dash import dcc
from dash import html
import dash_bootstrap_components as dbc
import flask
from ..common.dash_url_helper import create_component_kwargs, State
from .utils import getTime

title = "Fly Partner Checker"

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
                        'Input two root/nuc IDs to see shared synapses or coordinates and click "Submit" button.'
                        + " Large queries (>100k synapses) may take up to 2 mins."
                    ),
                    disabled=True,
                    rows=3,
                    style={"resize": "none",},
                ),
                style={
                    "margin-left": "5px",
                    "margin-right": "5px",
                    "margin-top": "5px",
                    "margin-bottom": "5px",
                    "width": "400px",
                },
            ),
            # puts all input fields into dedicated div #
            html.Div(
                [
                    html.Div(
                        children=[
                            # defines input A message #
                            dcc.Textarea(
                                id="input_a_text",
                                value="Root or Nucleus ID A",
                                style={
                                    "width": "200px",
                                    "resize": "none",
                                    "vertical-align": "top",
                                    "textAlign": "center",
                                },
                                rows=1,
                                disabled=True,
                            ),
                            # defines input A field #
                            dcc.Input(
                                **create_component_kwargs(
                                    state,
                                    id_inner="input_a",
                                    type="text",
                                    placeholder="Root/Nuc ID A",
                                    style={"width": "200px", "vertical-align": "top",},
                                ),
                            ),
                        ],
                        style={"margin-left": "5px", "display": "inline-block",},
                    ),
                    html.Br(),
                    html.Div(
                        children=[
                            # defines input B message #
                            dcc.Textarea(
                                id="input_b_text",
                                value="Root or Nucleus ID B",
                                style={
                                    "width": "200px",
                                    "resize": "none",
                                    "vertical-align": "top",
                                    "textAlign": "center",
                                },
                                rows=1,
                                disabled=True,
                            ),
                            # defines input B field #
                            dcc.Input(
                                **create_component_kwargs(
                                    state,
                                    id_inner="input_b",
                                    type="text",
                                    placeholder="Root/Nuc ID B",
                                    style={"width": "200px", "vertical-align": "top",},
                                ),
                            ),
                        ],
                        style={"margin-left": "5px", "display": "inline-block",},
                    ),
                    html.Br(),
                    html.Div(
                        children=[
                            # defines cleft score threshold message #
                            dcc.Textarea(
                                id="cleft_thresh_text",
                                value="Cleft Score Threshold",
                                style={
                                    "width": "200px",
                                    "resize": "none",
                                    "vertical-align": "top",
                                    "textAlign": "center",
                                },
                                rows=1,
                                disabled=True,
                            ),
                            # defines cleft score threshold input field #
                            dcc.Input(
                                **create_component_kwargs(
                                    state,
                                    id_inner="cleft_thresh_input",
                                    type="number",
                                    value=50,
                                    style={"width": "200px", "vertical-align": "top",},
                                ),
                            ),
                        ],
                        style={"margin-left": "5px", "display": "inline-block",},
                    ),
                    html.Div(
                        children=[
                            # defines timestamp input message #
                            dcc.Textarea(
                                id="timestamp_message_text",
                                value="Timestamp as datetime or Unix UTC (default now):",
                                style={
                                    "width": "400px",
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
                                        "width": "400px",
                                        "vertical-align": "top",
                                    },
                                )
                            ),
                        ],
                        style={"margin-left": "5px", "margin-top": "5px",},
                    ),
                ]
            ),
            # defines sumbission button #
            dbc.Button(
                children=["Submit",],
                id="submit_button",
                style={
                    "display": "inline-block",
                    "width": "400px",
                    "margin-left": "5px",
                    "margin-right": "5px",
                    "margin-top": "5px",
                    "margin-bottom": "5px",
                },
            ),
            # defines submit button loader #
            html.Div(
                dcc.Loading(id="submit_loader", type="default", children=""),
                style={"width": "400px",},
            ),
            # defines table #
            html.Div(
                dash_table.DataTable(
                    id="table", style_data={"whiteSpace": "normal", "height": "auto",},
                ),
                style={
                    "margin-left": "5px",
                    "margin-right": "5px",
                    "margin-top": "5px",
                    "margin-bottom": "5px",
                    "width": "400px",
                },
            ),
            # defines div for download button
            html.Div(children=[], id="download_div",),
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
            # defines div for post-submission elements #
            html.Div(children=[], id="post_submit_div",),
        ],
    )

    return layout


def app_layout():
    # https://dash.plotly.com/urls "Dynamically Create a Layout for Multi-Page App Validation"
    if flask.has_request_context():  # for real
        return url_bar_and_content_div
    # validation only
    return html.Div([url_bar_and_content_div, *page_layout()])
