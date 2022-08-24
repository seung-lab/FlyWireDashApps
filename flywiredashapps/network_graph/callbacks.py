from dash import dcc, html, Input, Output, State, no_update
import dash_bootstrap_components as dbc
import dash_cytoscape as cyto
from dash.exceptions import PreventUpdate
from nglui.statebuilder import *
import time
from .utils import *

cyto.load_extra_layouts()


def register_callbacks(app, config=None):
    """Set up callbacks to be passed to app.

    Keyword Arguments:
    app -- the app itself
    config -- dictionary of config settings (dict, default None)
    """

    # defines callback that generates main tables and violin plots #
    @app.callback(
        Output("post_submit_div", "children"),
        Input("submit_button", "n_clicks"),
        State({"type": "url_helper", "id_inner": "input_field"}, "value"),
        State({"type": "url_helper", "id_inner": "cleft_thresh_field"}, "value"),
        State({"type": "url_helper", "id_inner": "conn_thresh_field"}, "value"),
        State({"type": "url_helper", "id_inner": "timestamp_field"}, "value"),
    )
    def update_output(n_clicks, id_list, cleft_thresh, conn_thresh, timestamp):
        """Create network graph for queried ids.

        Keyword arguments:
        n_clicks -- unused trigger that tracks clicks for submit button
        id_list -- root ids of queried neurons (str)
        cleft_thresh -- value of cleft score threshold (float)
        conn_thresh -- minimum synapses to show connection (float)
        timestamp -- utc timestamp as datetime or unix (str)
        """

        # prevents firing if no ids are submitted #
        if id_list == None:
            raise PreventUpdate

        # records start time #
        start_time = time.time()

        # converts string input to list of string ids, removes bad ids into separate list #
        id_list, removed_list = inputToRootList(id_list, config, timestamp)

        # gets connectivity data for id list and info about removed synapses #
        raw_connectivity_dict, filter_message = getSynDoD(
            id_list, cleft_thresh, config, timestamp
        )

        # converts raw dict-of-dicts format into list of graph elements that can be read by cytoscape #
        graph_readable_elements = dictToElements(raw_connectivity_dict, conn_thresh)

        # sets elements of post_submit_div to show graph #
        post_submit = [
            cyto.Cytoscape(
                # sets the plot id #
                id="cytoscape",
                # sets initial positions of nodes using templates #
                layout={"name": "circle"},
                # layout={"name": "dagre"}, MAYBE?
                # styles plot width and height #
                style={"width": "1000px", "height": "500px",},
                # sets elements using input data #
                elements=graph_readable_elements,
                # styles graph #
                stylesheet=[
                    # styles nodes #
                    {"selector": "node", "style": {"label": "data(label)"}},
                    # styles edges #
                    {
                        "selector": "edge",
                        "style": {
                            "curve-style": "bezier",
                            "label": "data(weight)",
                            "target-arrow-shape": "triangle",
                        },
                    },
                    {"selector": "[weight < 10]", "style": {"width": "1px",},},
                    {"selector": "[weight >= 10]", "style": {"width": "3px",},},
                    {"selector": "[weight >= 20]", "style": {"width": "5px",},},
                    {"selector": "[weight >= 100]", "style": {"width": "10px",},},
                    # sets color of edge to nt value #
                    {
                        "selector": "[nt = 'gaba']",
                        "style": {
                            "line-color": "#636dfa",
                            "target-arrow-color": "#636dfa",
                        },
                    },
                    {
                        "selector": "[nt = 'ach']",
                        "style": {
                            "line-color": "#ef553b",
                            "target-arrow-color": "#ef553b",
                        },
                    },
                    {
                        "selector": "[nt = 'glut']",
                        "style": {
                            "line-color": "#00cc96",
                            "target-arrow-color": "#00cc96",
                        },
                    },
                    {
                        "selector": "[nt = 'oct']",
                        "style": {
                            "line-color": "#ab63fa",
                            "target-arrow-color": "#ab63fa",
                        },
                    },
                    {
                        "selector": "[nt = 'ser']",
                        "style": {
                            "line-color": "#ffa15a",
                            "target-arrow-color": "#ffa15a",
                        },
                    },
                    {
                        "selector": "[nt = 'da']",
                        "style": {
                            "line-color": "#19d3f3",
                            "target-arrow-color": "#19d3f3",
                        },
                    },
                ],
            ),
        ]

        # calculates total time #
        total_time = time.time() - start_time

        return post_submit

