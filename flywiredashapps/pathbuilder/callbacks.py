# Connectivity App #
from dash import dcc, html, Input, Output, State, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from nglui.statebuilder import *
import time
from .utils import *


def register_callbacks(app, config=None):
    # defines callback that generates chain on submit button press #
    @app.callback(
        Output("message_text", "value"),
        Input("submit_button", "n_clicks"),
        State({"type": "url_helper", "id_inner": "input_field"}, "value"),
        State({"type": "url_helper", "id_inner": "thresh_field"}, "value"),
    )
    def update_output(n_clicks, id, thresh):
        """Create summary and partner tables with violin plots for queried root id.

        Keyword arguments:
        n_clicks -- tracks clicks for submit button
        query_id -- str-format root id of queried neuron
        thresh -- float value of synapse number threshold
        """

        # sets start time #
        start_time = time.time()

        chain = buildChain(id, thresh, config={})

        # sets end time #
        total_time = time.time() - start_time

        return "Chain built in " + str(total_time) + " seconds: " + str(chain)

    pass


# runs program #
if __name__ == "__main__":
    app.run_server()

