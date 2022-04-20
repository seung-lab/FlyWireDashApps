from dash import dash_table
from dash import dcc
from dash import html
import dash_bootstrap_components as dbc
import flask
from ..common.dash_url_helper import create_component_kwargs, State

title = "Fly Dummy"

# sets id of url string and ??? #
url_bar_and_content_div = html.Div(
    [dcc.Location(id="url", refresh=False), html.Div(id="page-layout")]
)

# defines function to set page layout #
def page_layout(state={}):
    # print("!!!!!!!!!!!!!!!!!!!!STATE:", state)
    # # sets value of elements from url using state #
    # try:
    #     message_value = state["message"]["value"]
    # except:
    #     message_value = "Default message."

    # defines layout of various app elements #
    layout = html.Div(
        [
            dcc.Textarea(
                id="message",
                value=("Default message."),
                disabled=True,
                rows=1,
                style={"resize": "none", "width": "400px",},
            ),
            html.Br(),
            dcc.Input(
                **create_component_kwargs(
                    state,
                    id_inner="input_field",
                    type="text",
                    placeholder="text here",
                    style={"width": "400px",},
                )
            ),
            html.Br(),
            dbc.Button(
                id="submit_button", children=["Submit",], style={"width": "400px",},
            ),
        ],
    )

    return layout


def app_layout():
    # https://dash.plotly.com/urls "Dynamically Create a Layout for Multi-Page App Validation"
    if flask.has_request_context():  # for real
        return url_bar_and_content_div
    # validation only
    return html.Div([url_bar_and_content_div, *page_layout()])
