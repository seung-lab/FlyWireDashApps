import time
import dash
import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, Input, Output, State, dash_table
import urllib.parse
from itertools import compress
from dash.exceptions import PreventUpdate
from .utils import *
import pandas as pd


def register_callbacks(app, config=None):
    @app.callback(
        Output("message", "value"),
        Input("submit_button", "n_clicks"),
        State({"type": "url_helper", "id_inner": "input_field"}, "value"),
    )
    def input_to_message(n_clicks, input_text):
        return input_text

    pass


# runs program #
if __name__ == "__main__":
    app.run_server()
