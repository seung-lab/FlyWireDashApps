from dash import dcc, html, Input, Output, State, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from nglui.statebuilder import *
import time
from .utils import *


def register_callbacks(app, config=None):
    """Set up callbacks to be passed to app.

    Keyword Arguments:
    app -- the app itself
    config -- dictionary of config settings (dict, default None)
    """

    # defines callback that generates main tables and violin plots #
    @app.callback(
        Input("submit_button", "n_clicks"),
        State({"type": "url_helper", "id_inner": "input_field"}, "value"),
        State({"type": "url_helper", "id_inner": "cleft_thresh_field"}, "value"),
        State({"type": "url_helper", "id_inner": "timestamp_field"}, "value"),
    )
    def update_output(n_clicks, id_list, cleft_thresh, timestamp):
        """Create network graph for queried ids.

        Keyword arguments:
        n_clicks -- unused trigger that tracks clicks for submit button
        id_list -- root ids of queried neurons (str)
        cleft_thresh -- value of cleft score threshold (float)
        timestamp -- utc timestamp as datetime or unix (str)
        """

        # prevents firing if no ids are submitted #
        if id_list == None:
            raise PreventUpdate

        # records start time #
        start_time = time.time()

        id_list, removed_list = inputToRootList(id_list)

