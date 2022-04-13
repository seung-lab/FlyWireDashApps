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
        Output("table", "columns"),
        Output("table", "data"),
        Output("message_text", "value"),
        Output("message_text", "rows"),
        Output("submit_loader", "children"),
        Output("graph_div", "children"),
        Output("post_submit_div", "children"),
        Input("submit_button", "n_clicks"),
        State("input_a", "value"),
        State("input_b", "value"),
        State("cleft_thresh_input", "value"),
        prevent_initial_call=True,
    )
    def update_output(n_clicks, id_a, id_b, cleft_thresh):
        """Update app based on input.
        
        Keyword arguments:
        n_clicks -- int number of times the submit button has been pressed
        id_a -- str format root or nuc id of input a
        id_b -- str format root or nuc id of input b
        cleft_thresh -- float value of cleft threshold field
        """

        # bad id handling #
        if (len(id_a) != 18 and len(id_a != 7)) or (len(id_b) != 18 and len(id_b != 7)):
            return [
                [],
                [],
                "One or both IDs are invalid. Please enter 18-digit root or 7-digit nucleus IDs only.",
                1,
                "",
                [],
                [],
            ]
        else:
            pass
        try:
            id_a = int(id_a)
            id_b = int(id_b)
        except:
            return [
                [],
                [],
                "One or both IDs are invalid. Please enter a single 18-digit root or 7-digit nucleus ID in each field.",
                1,
                "",
                [],
                [],
            ]

        # nuc id detection and conversion #
        if len(str(id_a)) == 7:
            id_a = nucToRoot(id_a, config)
        else:
            pass
        if len(str(id_b)) == 7:
            id_b = nucToRoot(id_b, config)
        else:
            pass

        # outdated id handling #
        if (
            checkFreshness(id_a, config) == False
            or checkFreshness(id_b, config) == False
        ):
            return [[], [], "One or both IDs are outdated.", 1, "", [], []]
        else:
            pass

        # makes nuc dfs #
        nuc_a_df = getNuc(id_a, config)
        nuc_b_df = getNuc(id_b, config)

        # multinucleate id handling #
        if len(nuc_a_df) > 1:
            a_df = pd.DataFrame(
                {
                    "Quality": ["Root ID A", "Nuc ID A", "Nuc Coords A"],
                    "Value": [id_a, "Multinucleate", "Multinucleate"],
                }
            )
        else:
            a_df = pd.DataFrame(
                {
                    "Quality": ["Root ID A", "Nuc ID A", "Nuc Coords A"],
                    "Value": [
                        id_a,
                        nuc_a_df.loc[0, "Nuc ID"],
                        nuc_a_df.loc[0, "Nucleus Coordinates"],
                    ],
                }
            )
        if len(nuc_b_df) > 1:
            b_df = pd.DataFrame(
                {
                    "Quality": ["Root ID B", "Nuc ID B", "Nuc Coords B"],
                    "Value": [id_b, "Multinucleate", "Multinucleate"],
                }
            )
        else:
            b_df = pd.DataFrame(
                {
                    "Quality": ["Root ID B", "Nuc ID B", "Nuc Coords B"],
                    "Value": [
                        id_b,
                        nuc_b_df.loc[0, "Nuc ID"],
                        nuc_b_df.loc[0, "Nucleus Coordinates"],
                    ],
                }
            )

        # concatenates a and b info into one df
        full_df = pd.concat([a_df, b_df], ignore_index=True)

        # gets synapse data for a to b and b to a
        a_to_b_df, a_to_b_message = getSyn(
            pre_root=id_a,
            post_root=id_b,
            cleft_thresh=cleft_thresh,
            datastack_name=config.get("datastack", None),
            server_address=config.get("server_address", None),
        )
        b_to_a_df, b_to_a_message = getSyn(
            pre_root=id_b,
            post_root=id_a,
            cleft_thresh=cleft_thresh,
            datastack_name=config.get("datastack", None),
            server_address=config.get("server_address", None),
        )

        message = "A>B: " + a_to_b_message + "\n" + "B>A: " + b_to_a_message

        # makes df of syn data to add to full df #
        syn_df = pd.DataFrame(
            {
                "Quality": ["Syns A>B", "Syns B>A"],
                "Value": [len(a_to_b_df), len(b_to_a_df)],
            }
        )

        # concatenates syn info onto full df #
        full_df = pd.concat([full_df, syn_df], ignore_index=True)

        # assigns table column and data values from full df #
        table_columns = [{"name": i, "id": i,} for i in full_df.columns]
        table_data = full_df.to_dict("records")

        # makes violin and pie charts #
        a_to_b_violin = makePartnerViolin(
            id_a, id_b, cleft_thresh, "A>B Synapse NT Scores", config,
        )
        b_to_a_violin = makePartnerViolin(
            id_b, id_a, cleft_thresh, "B>A Synapse NT Scores", config
        )
        a_to_b_pie = makePartnerPie(
            id_a, id_b, cleft_thresh, "A>B Synapse Neuropils", config
        )
        b_to_a_pie = makePartnerPie(
            id_b, id_a, cleft_thresh, "B>A Synapse Neuropils", config
        )

        # builds list of figures to pass to children of graph_div #
        graph_div = [
            html.Div(
                dcc.Graph(id="a_to_b_violin", figure=a_to_b_violin,),
                style={"display": "inline-block"},
            ),
            html.Div(
                dcc.Graph(id="b_to_a_violin", figure=b_to_a_violin,),
                style={"display": "inline-block",},
            ),
            html.Div(
                dcc.Graph(id="a_to_b_pie", figure=a_to_b_pie,),
                style={"display": "inline-block",},
            ),
            html.Div(
                dcc.Graph(id="b_to_a_pie", figure=b_to_a_pie,),
                style={"display": "inline-block",},
            ),
        ]

        post_submit_div = [
            # defines link generation button #
            dbc.Button(
                "Generate NG Link Using Selected Partners",
                id="link_button",
                n_clicks=0,
                target="tab",
                style={
                    "margin-top": "5px",
                    "margin-right": "5px",
                    "margin-left": "5px",
                    "margin-bottom": "5px",
                    "width": "400px",
                    "display": "inline-block",
                    "vertical-align": "top",
                },
            ),
        ]

        return [
            table_columns,
            table_data,
            message,
            7,
            "",
            graph_div,
            post_submit_div,
        ]

    # defines callback that generates neuroglancer link #
    @app.callback(
        Output("link_button", "href",),
        Input("submit_button", "n_clicks"),
        State("input_a", "value"),
        State("input_b", "value"),
        State("cleft_thresh_input", "value"),
        State("table", "data",),
    )
    def makeLink(n_clicks, id_a, id_b, cleft_thresh, table_data):
        """Create neuroglancer link using selected partners.

        Keyword arguments:
        n_clicks -- unused dummy for trigger
        id_a -- ??? format root id of input a
        id_b -- ??? format root id of input b
        cleft_thresh -- float value of cleft threshold field
        table_data -- dataframe of summary table data
        """

        table_df = pd.DataFrame(table_data)

        # makes list of nucleus coord strings #
        nuc = [table_df.loc[2, "Value"], table_df.loc[5, "Value"]]

        out_url = buildPartnerLink(id_a, id_b, cleft_thresh, nuc, config=config)

        return out_url

    pass


# runs program #
if __name__ == "__main__":
    app.run_server()
