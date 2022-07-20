import time
import dash
import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, Input, Output, State, dash_table, no_update
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
        Output("download_div", "children"),
        Input("submit_button", "n_clicks"),
        State({"type": "url_helper", "id_inner": "input_a"}, "value",),
        State({"type": "url_helper", "id_inner": "input_b"}, "value",),
        State({"type": "url_helper", "id_inner": "cleft_thresh_input"}, "value",),
        State({"type": "url_helper", "id_inner": "timestamp_field"}, "value"),
    )
    def update_output(n_clicks, id_a, id_b, cleft_thresh, timestamp=None):
        """Update app based on input.
        
        Keyword arguments:
        n_clicks -- int number of times the submit button has been pressed
        id_a -- str format root or nuc id of input a
        id_b -- str format root or nuc id of input b
        cleft_thresh -- float value of cleft threshold field
        timestamp -- string format datetime or unix utc timestamp
        """

        # avoids premature submission #
        if id_a == None or id_b == None:
            raise PreventUpdate
        else:
            pass

        # sets timestamp to current time if no input or converts string input to datetime #
        if timestamp == None or timestamp == "":
            timestamp = getTime()
        else:
            timestamp = strToDatetime(timestamp)

        # handles bad input (which results in a None output from strToDatetime) #
        if timestamp == None:
            return [
                no_update,
                no_update,
                "Please enter timestamp in datetime format YYYY-MM-DD HH:MM:SS, e.g. 2022-07-11 13:25:46 or unix UTC, e.g. 1642407000",
                2,
                "",
                no_update,
                no_update,
                no_update,
            ]
        else:
            pass

        # handles outdated timestamps from before 2022 Jan 17 #
        if datetimeToUnix(timestamp) < 1642407000:
            return [
                no_update,
                no_update,
                "Timestamp out of current date range, must be newer than 2022-01-17.",
                1,
                "",
                no_update,
                no_update,
                no_update,
            ]
        else:
            pass

        # removes quotes from input strings #
        try:
            id_a = str(id_a).replace('"', "")
        except:
            pass
        try:
            id_a = str(id_a).replace("'", "")
        except:
            pass
        try:
            id_b = str(id_b).replace('"', "")
        except:
            pass
        try:
            id_b = str(id_b).replace("'", "")
        except:
            pass

        # bad id handling #
        if (len(id_a) != 18 and len(id_a) != 7) or (len(id_b) != 18 and len(id_b) != 7):
            return [
                no_update,
                no_update,
                "One or both IDs are invalid. Please enter 18-digit root or 7-digit nucleus IDs only.",
                1,
                "",
                no_update,
                no_update,
                no_update,
            ]
        else:
            pass
        try:
            id_a = int(id_a)
            id_b = int(id_b)
        except:
            return [
                no_update,
                no_update,
                "One or both IDs are invalid. Please enter a single 18-digit root or 7-digit nucleus ID in each field.",
                1,
                "",
                no_update,
                no_update,
                no_update,
            ]

        # nuc id detection and conversion #
        if len(str(id_a)) == 7:
            id_a = nucToRoot(id_a, config, timestamp=timestamp)
        else:
            pass
        if len(str(id_b)) == 7:
            id_b = nucToRoot(id_b, config, timestamp=timestamp)
        else:
            pass

        # bad id handling TEMPORARILY DISABLED #
        # try:
        #     if (
        #         checkFreshness(id_a, config, timestamp) == False
        #         or checkFreshness(id_b, config, timestamp) == False
        #     ):
        #         return [
        #             no_update,
        #             no_update,
        #             "One or both IDs are bad.",
        #             1,
        #             "",
        #             no_update,
        #             no_update,
        #             no_update,
        #         ]
        #     else:
        #         pass
        # except:
        #     return [
        #         no_update,
        #         no_update,
        #         "One or both IDs are bad.",
        #         1,
        #         "",
        #         no_update,
        #         no_update,
        #         no_update,
        #     ]

        if id_a == id_b:
            return [
                no_update,
                no_update,
                "Both IDs are from the same neuron, please submit 2 different neurons.",
                2,
                "",
                no_update,
                no_update,
                no_update,
            ]
        else:
            pass

        # makes nuc dfs #
        nuc_a_df = getNuc(id_a, config, timestamp)
        nuc_b_df = getNuc(id_b, config, timestamp)

        # handles cells without nuclei
        try:
            nuc_id_a = nuc_a_df.loc[0, "Nuc ID"]
            nuc_loc_a = nuc_a_df.loc[0 : (len(nuc_a_df) - 1), "Nucleus Coordinates"]
        except:
            nuc_id_a = "No Nucleus"
            nuc_loc_a = "No Nucleus"
        try:
            nuc_id_b = nuc_b_df.loc[0, "Nuc ID"]
            nuc_loc_b = nuc_b_df.loc[0 : (len(nuc_b_df) - 1), "Nucleus Coordinates"]
        except:
            nuc_id_b = "No Nucleus"
            nuc_loc_b = "No Nucleus"

        # assigns nuc values to respective dtaframes #
        a_df = pd.DataFrame(
            {
                "Quality": ["Root ID A", "Nuc ID A", "Nuc Coords A"],
                "Value": [str(id_a), nuc_id_a, nuc_loc_a,],
            }
        )
        b_df = pd.DataFrame(
            {
                "Quality": ["Root ID B", "Nuc ID B", "Nuc Coords B"],
                "Value": [str(id_b), nuc_id_b, nuc_loc_b,],
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
            timestamp=timestamp,
        )
        b_to_a_df, b_to_a_message = getSyn(
            pre_root=id_b,
            post_root=id_a,
            cleft_thresh=cleft_thresh,
            datastack_name=config.get("datastack", None),
            server_address=config.get("server_address", None),
            timestamp=timestamp,
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
            id_a,
            id_b,
            cleft_thresh,
            "A>B Synapse NT Scores",
            config,
            timestamp=timestamp,
        )
        b_to_a_violin = makePartnerViolin(
            id_b,
            id_a,
            cleft_thresh,
            "B>A Synapse NT Scores",
            config,
            timestamp=timestamp,
        )
        a_to_b_pie = makePartnerPie(
            id_a,
            id_b,
            cleft_thresh,
            "A>B Synapse Neuropils",
            config,
            timestamp=timestamp,
        )
        b_to_a_pie = makePartnerPie(
            id_b,
            id_a,
            cleft_thresh,
            "B>A Synapse Neuropils",
            config,
            timestamp=timestamp,
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
            # defines NG link generation button #
            dbc.Button(
                "Generate NG Link Using Partners",
                id="link_button",
                n_clicks=0,
                target="_blank",
                style={
                    "margin-top": "5px",
                    "margin-right": "5px",
                    "margin-left": "5px",
                    "margin-bottom": "5px",
                    "width": "420px",
                    "display": "inline-block",
                    "vertical-align": "top",
                },
            ),
            # defines conn_A link generation button #
            dbc.Button(
                "Port Neuron A to Connectivity App",
                id="connectivity_link_button_A",
                n_clicks=0,
                target="_blank",
                style={
                    "margin-top": "5px",
                    "margin-right": "5px",
                    "margin-left": "5px",
                    "margin-bottom": "5px",
                    "width": "420px",
                    "display": "inline-block",
                    "vertical-align": "top",
                },
            ),
            # defines conn_B link generation button #
            dbc.Button(
                "Port Neuron B to Connectivity App",
                id="connectivity_link_button_B",
                n_clicks=0,
                target="_blank",
                style={
                    "margin-top": "5px",
                    "margin-right": "5px",
                    "margin-left": "5px",
                    "margin-bottom": "5px",
                    "width": "420px",
                    "display": "inline-block",
                    "vertical-align": "top",
                },
            ),
            # defines summary link generation button #
            dbc.Button(
                "Port Neurons to Summary App",
                id="summary_link_button",
                n_clicks=0,
                target="_blank",
                style={
                    "margin-top": "5px",
                    "margin-right": "5px",
                    "margin-left": "5px",
                    "margin-bottom": "5px",
                    "width": "420px",
                    "display": "inline-block",
                    "vertical-align": "top",
                },
            ),
        ]

        download_button_div = (
            dbc.Button(
                "Download Partner Table as CSV File",
                id="partner_download_button",
                style={
                    "width": "400px",
                    "margin-right": "5px",
                    "margin-left": "5px",
                    "margin-top": "5px",
                    "margin-bottom": "5px",
                },
            ),
            dcc.Download(id="partner_download"),
        )

        return [
            table_columns,
            table_data,
            message,
            7,
            "",
            graph_div,
            post_submit_div,
            download_button_div,
        ]

    # defines callback that generates neuroglancer link #
    @app.callback(
        Output("link_button", "href",),
        Input("submit_button", "n_clicks"),
        State({"type": "url_helper", "id_inner": "input_a"}, "value",),
        State({"type": "url_helper", "id_inner": "input_b"}, "value",),
        State({"type": "url_helper", "id_inner": "cleft_thresh_input"}, "value",),
        State("table", "data",),
        State({"type": "url_helper", "id_inner": "timestamp_field"}, "value"),
    )
    def makeLink(n_clicks, id_a, id_b, cleft_thresh, table_data, timestamp=None):
        """Create neuroglancer link using selected partners.
        Keyword arguments:
        n_clicks -- unused dummy for trigger
        id_a -- ??? format root id of input a
        id_b -- ??? format root id of input b
        cleft_thresh -- float value of cleft threshold field
        table_data -- dataframe of summary table data
        timestamp -- string format datetime or unix utc timestamp
        """

        table_df = pd.DataFrame(table_data)

        # sets timestamp to current time if no input or converts string input to datetime #
        if timestamp == None:
            timestamp = getTime()
        else:
            timestamp = strToDatetime(timestamp)

        # makes list of nucleus coord strings #
        raw_nuc = [table_df.loc[2, "Value"], table_df.loc[5, "Value"]]

        # convoluted, but allows for multinucleate handling #
        nuc = []

        for value in raw_nuc:
            if type(value) == list:
                for nuc_loc in value:
                    nuc.append(str(nuc_loc))
            else:
                nuc.append(value)

        out_url = buildPartnerLink(
            id_a, id_b, cleft_thresh, nuc, config=config, timestamp=timestamp
        )

        return out_url

    # defines callback to download summary table as csv on button press #
    @app.callback(
        Output("partner_download", "data"),
        Input("partner_download_button", "n_clicks"),
        State("table", "data"),
        prevent_initial_call=True,
    )
    def downloadSummary(n_clicks, table_data):
        summary_df = pd.DataFrame(table_data)
        return dcc.send_data_frame(summary_df.to_csv, "partner_table.csv")

    # defines callback that generates connectivity app link  #
    @app.callback(
        Output("connectivity_link_button_A", "href",),
        Output("connectivity_link_button_B", "href",),
        Output("summary_link_button", "href",),
        Input("post_submit_div", "children"),
        State("table", "data",),
        State({"type": "url_helper", "id_inner": "timestamp_field"}, "value"),
        State({"type": "url_helper", "id_inner": "cleft_thresh_input"}, "value"),
    )
    def makeOutLinks(n_clicks, table_data, timestamp=None, cleft_thresh=50):
        """Create outbound app links using selected IDs.
        Keyword arguments:
        n_clicks -- unused dummy for trigger
        rows -- list of selected upstream row indices
        table_data -- dataframe of summary table data
        timestamp -- string format datetime or unix utc timestamp
        cleft_thresh -- cleft score threshold for synapses 
        """

        root_A, root_B = [table_data[0]["Value"], table_data[3]["Value"]]

        # sets timestamp to current time if no input or converts string input to datetime #
        if timestamp == None:
            timestamp = getTime()
        else:
            timestamp = strToDatetime(timestamp)

        both_roots = root_A + "," + root_B

        # builds url using portUrl function #
        con_url_A = portUrl(
            root_A,
            "connectivity",
            str(cleft_thresh),
            config=config,
            timestamp=timestamp,
        )
        con_url_B = portUrl(
            root_B,
            "connectivity",
            str(cleft_thresh),
            config=config,
            timestamp=timestamp,
        )
        sum_url = portUrl(
            both_roots,
            "summary",
            str(cleft_thresh),
            config=config,
            timestamp=timestamp,
        )

        # returns url string, alters button text, sends empty string for loader #
        return [con_url_A, con_url_B, sum_url]

    pass


# runs program #
if __name__ == "__main__":
    app.run_server()
