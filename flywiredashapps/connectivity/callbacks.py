# Connectivity App #
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
        Output("post_submit_download__summary", "children"),
        Output("post_submit_download__upstream", "children"),
        Output("post_submit_download__downstream", "children"),
        Output("post_submit_linkbuilder_buttons", "children"),
        Output("summary_table", "columns"),
        Output("summary_table", "data"),
        Output("incoming_table", "columns"),
        Output("incoming_table", "data"),
        Output("outgoing_table", "columns"),
        Output("outgoing_table", "data"),
        Output("graph_div", "children"),
        Output("message_text", "value"),
        Output("message_text", "rows"),
        Output("submit_loader", "children"),
        Input("submit_button", "n_clicks"),
        State({"type": "url_helper", "id_inner": "input_field"}, "value"),
        State({"type": "url_helper", "id_inner": "cleft_thresh_field"}, "value"),
        State({"type": "url_helper", "id_inner": "timestamp_field"}, "value"),
        State({"type": "url_helper", "id_inner": "filter_list_field"}, "value"),
    )
    def update_output(n_clicks, query_id, cleft_thresh, timestamp, filter_list):
        """Create summary and partner tables with violin plots for queried root id.

        Keyword arguments:
        n_clicks -- tracks clicks for submit button
        query_id -- root id of queried neuron as int
        cleft_thresh -- float value of cleft score threshold
        timestamp -- str format utc timestamp as datetime or unix
        filter_list -- str list of root ids to filter results by
        """

        # if filter list exists, converts to tuple of ints #
        if filter_list != None and filter_list != []:
            filter_list = filter_list.strip("[")
            filter_list = filter_list.strip("]")
            filter_list = filter_list.split(",")
            filter_list = [int(x.strip(" ")) for x in filter_list]
            # sorts list and converts to a tuple for hashability #
            filter_list.sort()
            filter_list = tuple(filter_list)
        elif filter_list == []:
            filter_list = None
        else:
            pass

        # sets start time #
        start_time = time.time()

        # handles blank id submission #
        if query_id == None:
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
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                "Please enter timestamp in datetime format YYYY-MM-DD HH:MM:SS, e.g. 2022-07-11 13:25:46 or unix UTC, e.g. 1642407000",
                2,
                "",
            ]
        else:
            pass

        # handles outdated timestamps from before 2022 Jan 17 #
        if datetimeToUnix(timestamp) < 1642407000:
            return [
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                "Timestamp out of current date range, must be newer than 2022-01-17.",
                1,
                "",
            ]
        else:
            pass

        # removes quotes from input string #
        try:
            query_id = str(query_id).replace('"', "")
        except:
            pass
        try:
            query_id = str(query_id).replace("'", "")
        except:
            pass

        # splits 'ids' string into list #
        query_id = str(query_id).split(",")

        # strips spaces and brackets from id_list entries and converts to integers #
        query_id = [str(x.strip(" ")) for x in query_id]
        query_id = [str(x.strip("[")) for x in query_id]
        query_id = [int(str(x.strip("]"))) for x in query_id]

        # handles multiple id sumbission #
        if (len(query_id) != 1 and len(query_id) != 3) or (
            len(query_id) == 3 and len(str(query_id[0])) == len(str(query_id[2]))
        ):
            return [
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                "Please limit each query to one neuron.",
                1,
                "",
            ]
        else:
            pass

        # handles bad IDs if idConvert fails #

        # converts id input to root id #
        root_id = idConvert(query_id, config=config, timestamp=timestamp)

        # sets failure message if idConvert fails
        if root_id == 0:
            message = "Entry must be 18-digit root id, 7-digit nucleus id, or x,y,z coordinates in 4x4x40nm resolution."
        elif root_id == "invalid nuc id":
            message = "Nucleus ID is invalid, please check it and try again."
        elif root_id == "invalid root id":
            message = "Root ID is invalid, please check it and try again."

        # returns specific error message if idConvert fails #
        if len(str(root_id)) != 18:
            return [
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                message,
                1,
                "",
            ]

        # FRESHNESS CHECKER TEMPORARILY DISABLED #
        # handles bad return from freshness checker #
        try:
            fresh = checkFreshness(root_id, config=config, timestamp=timestamp)
        except:
            return [
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                "Entry must be 18-digit root id, 7-digit nucleus id, or x,y,z coordinates in 16x16x40nm resolution.",
                1,
                "",
            ]

        # handles outdated ids #
        if fresh == False:
            return [
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                "Root ID is outdated or not valid at the given timestamp, please refresh the segment or use x,y,z coordinates in 16x16x40nm resolution.",
                1,
                "",
            ]
        else:
            pass

        # handles 0 ids if they somehow make it through all previous filters #
        if root_id == 0:
            return [
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                "Entry must be 18-digit root id, 7-digit nucleus id, or x,y,z coordinates in 4x4x40nm resolution.",
                1,
                "",
            ]
        else:
            pass

        # builds dataframes and graphs #
        sum_list = makeSummaryDataFrame(
            root_id,
            cleft_thresh,
            config=config,
            timestamp=timestamp,
            filter_list=filter_list,
        )
        sum_df = sum_list[0]

        # clunky but necessary handling for bad ids that make it through all previous filters #
        final_check = sum_df.loc[0].values.flatten().tolist()[1:]
        if final_check == ["n/a", "n/a", "0", "0", "0", "0"]:
            return [
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                "Bad ID or no-synapse orphan. Please check and try again.",
                1,
                "",
            ]
        else:
            pass

        # creates partner dataframes, violin plots, and pie charts #
        up_df = makePartnerDataFrame(
            root_id,
            cleft_thresh,
            upstream=True,
            config=config,
            timestamp=timestamp,
            filter_list=filter_list,
        )
        down_df = makePartnerDataFrame(
            root_id,
            cleft_thresh,
            upstream=False,
            config=config,
            timestamp=timestamp,
            filter_list=filter_list,
        )
        up_violin = makeViolin(
            root_id,
            cleft_thresh,
            incoming=True,
            config=config,
            timestamp=timestamp,
            filter_list=filter_list,
        )
        down_violin = makeViolin(
            root_id,
            cleft_thresh,
            incoming=False,
            config=config,
            timestamp=timestamp,
            filter_list=filter_list,
        )
        up_pie = makePie(
            root_id,
            cleft_thresh,
            incoming=True,
            config=config,
            timestamp=timestamp,
            filter_list=filter_list,
        )
        down_pie = makePie(
            root_id,
            cleft_thresh,
            incoming=False,
            config=config,
            timestamp=timestamp,
            filter_list=filter_list,
        )

        # assigns df values to 'cols' and 'data' for passing to dash table #
        sum_cols = [{"name": i, "id": i,} for i in sum_df.columns]
        up_cols = [{"name": i, "id": i,} for i in up_df.columns]
        down_cols = [{"name": i, "id": i,} for i in down_df.columns]
        sum_data = sum_df.to_dict("records")
        up_data = up_df.to_dict("records")
        down_data = down_df.to_dict("records")

        # changes root id column to markdown format so they can be made links #
        up_cols[0]["presentation"] = "markdown"
        down_cols[0]["presentation"] = "markdown"

        # builds list of figures to pass to children of graph_div using violin and pie charts #
        figs = [
            html.Div(
                dcc.Graph(id="incoming_figure", figure=up_violin,),
                style={"display": "inline-block"},
            ),
            html.Div(
                dcc.Graph(id="outgoing_figure", figure=down_violin,),
                style={"display": "inline-block",},
            ),
            html.Div(
                dcc.Graph(id="in_pie_chart", figure=up_pie,),
                style={"display": "inline-block",},
            ),
            html.Div(
                dcc.Graph(id="out_pie_chart", figure=down_pie,),
                style={"display": "inline-block",},
            ),
        ]

        # creates layout for linkbuilder buttons that appear only after an initial query #
        post_div_linkbuttons = [
            html.Div(
                [
                    # defines link generation button #
                    dbc.Button(
                        "Generate NG Link Using Selected Partners",
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
                    # defines link button loader #
                    html.Div(
                        dcc.Loading(id="link_loader", type="default", children=""),
                        style={
                            "margin-right": "5px",
                            "margin-left": "5px",
                            "width": "1000px",
                        },
                    ),
                    # # defines all-synapse link generation button # 
                    # TEMPORARILY DISABLED DUE TO JSON CUTOFF #
                    # dbc.Button(
                    #     "Generate NG Link with All Synapses",
                    #     id="allsyn_link_button",
                    #     n_clicks=0,
                    #     target="tab",
                    #     style={
                    #         "margin-top": "5px",
                    #         "margin-right": "5px",
                    #         "margin-left": "5px",
                    #         "margin-bottom": "5px",
                    #         "width": "420px",
                    #         "display": "inline-block",
                    #         "vertical-align": "top",
                    #     },
                    # ),
                    # # defines all-synapse link button loader #
                    # html.Div(
                    #     dcc.Loading(
                    #         id="allsyn_link_loader", type="default", children="",
                    #     ),
                    #     style={
                    #         "margin-right": "5px",
                    #         "margin-left": "5px",
                    #         "width": "1000px",
                    #     },
                    # ),
                    # defines Summary App link button loader #
                    html.Div(
                        dcc.Loading(
                            id="summary_link_loader", type="default", children="",
                        ),
                        style={
                            "margin-right": "5px",
                            "margin-left": "5px",
                            "width": "1000px",
                        },
                    ),
                    # defines Summary App link generation button #
                    dbc.Button(
                        "Select Neuron to Port to Summary App",
                        id="summary_link_button",
                        n_clicks=0,
                        target="_blank",
                        style={
                            "margin-top": "5px",
                            "margin-right": "5px",
                            "margin-left": "5px",
                            "margin-bottom": "5px",
                            "width": "420px",
                            "vertical-align": "top",
                        },
                    ),
                    # # defines Graph App link button loader #
                    # COMMENTED OUT UNTIL DEPLOYED FOR TESTING #
                    # html.Div(
                    #     dcc.Loading(
                    #         id="graph_link_loader", type="default", children="",
                    #     ),
                    #     style={
                    #         "margin-right": "5px",
                    #         "margin-left": "5px",
                    #         "width": "1000px",
                    #     },
                    # ),
                    # # defines Graph App link generation button #
                    # COMMENTED OUT UNTIL DEPLOYED FOR TESTING #
                    # dbc.Button(
                    #     "Select Neuron to Port to Graph App",
                    #     id="graph_link_button",
                    #     n_clicks=0,
                    #     target="_blank",
                    #     style={
                    #         "margin-top": "5px",
                    #         "margin-right": "5px",
                    #         "margin-left": "5px",
                    #         "margin-bottom": "5px",
                    #         "width": "420px",
                    #         "vertical-align": "top",
                    #     },
                    # ),
                    # defines Partner App link button loader #
                    html.Div(
                        dcc.Loading(
                            id="partner_link_loader", type="default", children="",
                        ),
                        style={
                            "margin-right": "5px",
                            "margin-left": "5px",
                            "width": "1000px",
                        },
                    ),
                    # defines Partner App link generation button #
                    dbc.Button(
                        "Select 2 Neurons to Port to Partner App",
                        id="partner_link_button",
                        n_clicks=0,
                        target="_blank",
                        style={
                            "margin-top": "5px",
                            "margin-right": "5px",
                            "margin-left": "5px",
                            "margin-bottom": "5px",
                            "width": "420px",
                            "vertical-align": "top",
                        },
                    ),
                    html.Br(),
                    # defines button to clear table selections #
                    dbc.Button(
                        "Clear Partner Selections",
                        id="clear_button",
                        n_clicks=0,
                        color="danger",
                        style={
                            "width": "420px",
                            "margin-right": "5px",
                            "margin-left": "5px",
                            "margin-top": "5px",
                            "margin-bottom": "25px",
                            "display": "inline-block",
                            "vertical-align": "top",
                        },
                    ),
                ],
            ),
        ]

        # creates layout for summary downloader #
        post_sum = [
            # defines summary downloader #
            html.Div(
                [
                    dbc.Button(
                        "Download Summary Table as CSV File",
                        id="summary_download_button",
                        color="success",
                        style={
                            "width": "420px",
                            "margin-right": "5px",
                            "margin-left": "5px",
                            "margin-top": "5px",
                            "margin-bottom": "5px",
                        },
                    ),
                ]
            ),
            dcc.Download(id="summary_download"),
        ]
        # creates layout for upstream downloader #
        post_up = [
            # defines upstream downloader #
            html.Div(
                [
                    dbc.Button(
                        "Download Upstream Partner Table as CSV File",
                        id="upstream_download_button",
                        color="success",
                        style={
                            "width": "420px",
                            "margin-right": "5px",
                            "margin-left": "5px",
                            "margin-top": "5px",
                            "margin-bottom": "5px",
                        },
                    ),
                ]
            ),
            dcc.Download(id="upstream_download"),
        ]
        # creates layout for downstream downloader #
        post_down = [
            # defines downstream downloader #
            html.Div(
                [
                    dbc.Button(
                        "Download Downstream Partner Table as CSV File",
                        id="downstream_download_button",
                        color="success",
                        style={
                            "width": "420px",
                            "margin-right": "5px",
                            "margin-left": "5px",
                            "margin-top": "5px",
                            "margin-bottom": "5px",
                        },
                    ),
                ]
            ),
            dcc.Download(id="downstream_download"),
        ]

        # sets end time #
        end_time = time.time()

        # calculates elapsed time #
        elapsed_time = str(round(end_time - start_time))

        # creates string containing time information #
        message_text = (
            "Connectivity query completed in "
            + elapsed_time
            + " seconds. \n"
            + sum_list[1]
        )

        # sets text area rows based on length of message #
        message_rows = message_text.count("\n")

        return [
            post_sum,
            post_up,
            post_down,
            post_div_linkbuttons,
            sum_cols,
            sum_data,
            up_cols,
            up_data,
            down_cols,
            down_data,
            figs,
            message_text,
            message_rows,
            "",
        ]

    # defines callback that generates neuroglancer link #
    @app.callback(
        Output("link_button", "href",),
        Output("link_loader", "children",),
        Input("incoming_table", "selected_rows",),
        Input("outgoing_table", "selected_rows",),
        State("summary_table", "data",),
        State("incoming_table", "data",),
        State("outgoing_table", "data",),
        State({"type": "url_helper", "id_inner": "cleft_thresh_field"}, "value",),
        State({"type": "url_helper", "id_inner": "timestamp_field"}, "value"),
        prevent_initial_call=True,
    )
    def makeLink(
        up_rows, down_rows, query_data, up_data, down_data, cleft_thresh, timestamp
    ):
        """Create neuroglancer link using selected partners.

        Keyword arguments:
        up_rows -- selected upstream row indices (list)
        down_rows -- selected downstream row indices (list)
        query_data -- summary table data (dataframe)
        up_data -- incoming table data (dataframe)
        down_data -- outgoing table data (dataframe)
        cleft_thresh -- value of cleft threshold field (float)
        timestamp -- utc timestamp as datetime or unix (str)
        """

        # sets timestamp to current time if no input or converts string input to datetime #
        if timestamp == None:
            timestamp = getTime()
        else:
            timestamp = strToDatetime(timestamp)

        # gets id of queried neuron from table #
        query_out = [query_data[0]["Root ID"]]

        # checks if partners are selected, gets their ids if so #
        # markdown has to be converted back to int #
        if up_rows == [] or up_rows == None:
            up_out = [0]
        else:
            up_out = markdownToInt([up_data[x]["Upstream Partner ID"] for x in up_rows])
        if down_rows == [] or down_rows == None:
            down_out = [0]
        else:
            down_out = markdownToInt(
                [down_data[x]["Downstream Partner ID"] for x in down_rows]
            )

        # makes list of nucleus coordinates for query neuron #
        nuc = query_data[0]["Nucleus Coordinates"][1:-1].split(",")

        # builds url #
        out_url = buildLink(
            query_out,
            up_out,
            down_out,
            cleft_thresh,
            nuc,
            config=config,
            timestamp=timestamp,
        )

        return [out_url, ""]

    # defines callback that clears table selections #
    @app.callback(
        Output("incoming_table", "active_cell",),
        Output("outgoing_table", "active_cell",),
        Output("incoming_table", "selected_cells",),
        Output("outgoing_table", "selected_cells",),
        Output("incoming_table", "selected_rows",),
        Output("outgoing_table", "selected_rows",),
        Input("clear_button", "n_clicks",),
        prevent_initial_call=True,
    )
    def clearSelected(n_clicks):
        """Clear table selections.

        Keyword arguments:
        n_clicks -- unused trigger that tracks clicks for clear button
        """

        return [
            None,
            None,
            [],
            [],
            [],
            [],
        ]

    # defines callback to download summary table as csv on button press #
    @app.callback(
        Output("summary_download", "data"),
        Input("summary_download_button", "n_clicks"),
        State("summary_table", "data"),
        prevent_initial_call=True,
    )
    def downloadSummary(n_clicks, table_data):
        """Download summary table as csv file.

        Keyword arguments:
        n_clicks -- unused trigger that tracks clicks for download button
        table_data -- data from summary table
        """

        root_id = str(table_data[0]["Root ID"])
        out_name = root_id + "_summary_table.csv"

        summary_df = pd.DataFrame(table_data)
        if "[" in summary_df.loc[0, "Nucleus Coordinates"][0]:
            summary_df.loc[0, "Nucleus Coordinates"] = [
                int(x.strip())
                for x in summary_df.loc[0, "Nucleus Coordinates"][1:-1].split(",")
            ]
        return dcc.send_data_frame(summary_df.to_csv, out_name)

    # defines callback to download upstream table as csv on button press #
    @app.callback(
        Output("upstream_download", "data"),
        Input("upstream_download_button", "n_clicks"),
        State("incoming_table", "data"),
        State("summary_table", "data"),
        prevent_initial_call=True,
    )
    def downloadUpstream(n_clicks, table_data, summary_data):
        """Download upstream table as csv file.

        Keyword arguments:
        n_clicks -- unused trigger that tracks clicks for download button
        table_data -- data from upstream table
        summary_data -- data from summary table
        """

        root_id = str(summary_data[0]["Root ID"])
        out_name = root_id + "_upstream_partner_table.csv"

        # converts table data to dataframe #
        upstream_df = pd.DataFrame(table_data)

        # converts markdown back into int root id #
        upstream_df["Upstream Partner ID"] = [
            x[1:19] for x in upstream_df["Upstream Partner ID"]
        ]

        return dcc.send_data_frame(upstream_df.to_csv, out_name)

    # defines callback to download downstream table as csv on button press #
    @app.callback(
        Output("downstream_download", "data"),
        Input("downstream_download_button", "n_clicks"),
        State("outgoing_table", "data"),
        State("summary_table", "data"),
        prevent_initial_call=True,
    )
    def downloadDownstream(n_clicks, table_data, summary_data):
        """Download downstream table as csv file.

        Keyword arguments:
        n_clicks -- unused trigger that tracks clicks for download button
        table_data -- data from downstream table
        summary_data -- data from summary table
        """

        root_id = str(summary_data[0]["Root ID"])
        out_name = root_id + "_downstream_partner_table.csv"

        # converts table data to dataframe #
        downstream_df = pd.DataFrame(table_data)

        # converts markdown back into normal root id #
        downstream_df["Downstream Partner ID"] = [
            x[1:19] for x in downstream_df["Downstream Partner ID"]
        ]

        return dcc.send_data_frame(downstream_df.to_csv, out_name)

    # defines callback that generates partner app link  #
    @app.callback(
        Output("partner_link_button", "href",),
        Output("partner_link_button", "children",),
        Output("partner_link_loader", "children",),
        Input("incoming_table", "selected_rows",),
        Input("outgoing_table", "selected_rows",),
        State("summary_table", "data",),
        State("incoming_table", "data",),
        State("outgoing_table", "data",),
        State({"type": "url_helper", "id_inner": "timestamp_field"}, "value"),
        State({"type": "url_helper", "id_inner": "cleft_thresh_field"}, "value"),
        prevent_initial_call=True,
    )
    def makePartLink(
        in_rows, out_rows, sum_data, in_data, out_data, timestamp, cleft_thresh
    ):
        """Create partner app link using selected IDs.

        Keyword arguments:
        in_rows -- selected incoming row indices (list)
        out_rows -- selected outgoing row indices (list)
        sum_data -- summary table data (dataframe)
        in_data -- incoming table data (dataframe)
        out_data -- outgoing table data (dataframe)
        timestamp -- utc timestamp as datetime or unix (str)
        cleft_thresh -- value of cleft threshold field (float)
        """

        # sets timestamp to current time if no input or converts string input to datetime #
        if timestamp == None:
            timestamp = getTime()
        else:
            timestamp = strToDatetime(timestamp)

        # generates root list using table data and selected rows #
        # has to convert markdown back to int format #
        in_list = markdownToInt([in_data[x]["Upstream Partner ID"] for x in in_rows])
        out_list = markdownToInt(
            [out_data[x]["Downstream Partner ID"] for x in out_rows]
        )
        sum_list = [sum_data[0]["Root ID"]]
        full_list = in_list + out_list

        # handles errors #
        if len(full_list) == 0:
            return ["", "Select 1-2 neurons to port to Partner App", ""]
        elif len(full_list) == 1:
            full_list += sum_list
        elif len(full_list) == 2:
            pass
        elif len(full_list) > 2:
            return ["", "Select only 1-2 neurons to port to Partner App", ""]

        # builds url using portUrl function #
        out_url = portUrl(
            str(full_list)[1:-1],
            "partner",
            str(cleft_thresh),
            config,
            timestamp=timestamp,
        )

        # returns url string, alters button text, sends empty string for loader #
        return [out_url, "Send selected neurons to Partner App", ""]

    # # defines callback that generates graph app link  #
    # COMMENTED OUT UNTIL DEPLOYED FOR TESTING #
    # @app.callback(
    #     Output("graph_link_button", "href",),
    #     Output("graph_link_button", "children",),
    #     Output("graph_link_loader", "children",),
    #     Input("incoming_table", "selected_rows",),
    #     Input("outgoing_table", "selected_rows",),
    #     State("summary_table", "data",),
    #     State("incoming_table", "data",),
    #     State("outgoing_table", "data",),
    #     State({"type": "url_helper", "id_inner": "timestamp_field"}, "value"),
    #     State({"type": "url_helper", "id_inner": "cleft_thresh_field"}, "value"),
    #     prevent_initial_call=True,
    # )
    # def makeGraphLink(
    #     in_rows, out_rows, sum_data, in_data, out_data, timestamp, cleft_thresh
    # ):
    #     """Create graph app link using selected IDs.
        
    #     Keyword arguments:
    #     in_rows -- selected incoming row indices (list)
    #     out_rows -- selected outgoing row indices (list)
    #     sum_data -- summary table data (dataframe)
    #     in_data -- incoming table data (dataframe)
    #     out_data -- outgoing table data (dataframe)
    #     timestamp -- utc timestamp as datetime or unix (str)
    #     cleft_thresh -- value of cleft threshold field (float)
    #     """

    #     # sets timestamp to current time if no input or converts string input to datetime #
    #     if timestamp == None:
    #         timestamp = getTime()
    #     else:
    #         timestamp = strToDatetime(timestamp)

    #     # generates root list using table data and selected rows #
    #     # has to convert markdown back to int format #
    #     in_list = markdownToInt([in_data[x]["Upstream Partner ID"] for x in in_rows])
    #     out_list = markdownToInt(
    #         [out_data[x]["Downstream Partner ID"] for x in out_rows]
    #     )
    #     sum_list = [sum_data[0]["Root ID"]]
    #     full_list = sum_list + in_list + out_list

    #     # handles errors #
    #     if len(full_list) > 20:
    #         return ["", "Select 20 or fewer neurons to port to Graph App", ""]

    #     # builds url using portUrl function #
    #     out_url = portUrl(
    #         str(full_list)[1:-1],
    #         "graph",
    #         str(cleft_thresh),
    #         config,
    #         timestamp=timestamp,
    #     )

    #     # returns url string, alters button text, sends empty string for loader #
    #     return [out_url, "Send selected neurons to Graph App", ""]

    # defines callback that generates summary app link  #
    @app.callback(
        Output("summary_link_button", "href",),
        Output("summary_link_button", "children",),
        Output("summary_link_loader", "children",),
        Input("incoming_table", "selected_rows",),
        Input("outgoing_table", "selected_rows",),
        State("summary_table", "data",),
        State("incoming_table", "data",),
        State("outgoing_table", "data",),
        State({"type": "url_helper", "id_inner": "timestamp_field"}, "value"),
        State({"type": "url_helper", "id_inner": "cleft_thresh_field"}, "value"),
        prevent_initial_call=True,
    )
    def makeSumLink(
        in_rows, out_rows, sum_data, in_data, out_data, timestamp, cleft_thresh
    ):
        """Create summary app link using selected IDs.
        
        Keyword arguments:
        in_rows -- selected incoming row indices (list)
        out_rows -- selected outgoing row indices (list)
        sum_data -- summary table data (dataframe)
        in_data -- incoming table data (dataframe)
        out_data -- outgoing table data (dataframe)
        timestamp -- utc timestamp as datetime or unix (str)
        cleft_thresh -- value of cleft threshold field (float)
        """

        # sets timestamp to current time if no input or converts string input to datetime #
        if timestamp == None:
            timestamp = getTime()
        else:
            timestamp = strToDatetime(timestamp)

        # generates root list using table data and selected rows #
        # has to convert markdown back to int format #
        in_list = markdownToInt([in_data[x]["Upstream Partner ID"] for x in in_rows])
        out_list = markdownToInt(
            [out_data[x]["Downstream Partner ID"] for x in out_rows]
        )
        sum_list = [sum_data[0]["Root ID"]]
        full_list = sum_list + in_list + out_list

        # handles errors #
        if len(full_list) > 20:
            return ["", "Select 20 or fewer neurons to port to Summary App", ""]

        # builds url using portUrl function #
        out_url = portUrl(
            str(full_list)[1:-1],
            "summary",
            str(cleft_thresh),
            config,
            timestamp=timestamp,
        )

        # returns url string, alters button text, sends empty string for loader #
        return [out_url, "Send selected neurons to Summary App", ""]

    # # defines callback that generates allsyn neuroglancer link # 
    # TEMPORARILY DISABLED DUE TO JSON CUTOFF ISSUE #
    # @app.callback(
    #     Output("allsyn_link_button", "href",),
    #     Output("allsyn_link_loader", "children",),
    #     Input("submit_button", "n_clicks"),
    #     State("summary_table", "data",),
    #     State({"type": "url_helper", "id_inner": "cleft_thresh_field"}, "value",),
    #     State({"type": "url_helper", "id_inner": "timestamp_field"}, "value",),
    #     State({"type": "url_helper", "id_inner": "filter_list_field"}, "value"),
    # )
    # def makeAllsynLink(n_clicks, query_data, cleft_thresh, timestamp, filter_list):
    #     """Create link with all synapses on queried neuron.

    #     Keyword arguments:
    #     n_clicks -- unused trigger that tracks number of times submit button is pressed
    #     query_data -- summary table data (dataframe)
    #     cleft_thresh -- value of cleft threshold field (float)
    #     timestamp -- utc timestamp as datetime or unix (str)
    #     filter_list -- list of root ids to filter results by (str)
    #     """

    #     # if filter list exists, converts to tuple of ints #
    #     if filter_list != None and filter_list != []:
    #         filter_list = filter_list.strip("[")
    #         filter_list = filter_list.strip("]")
    #         filter_list = filter_list.split(",")
    #         filter_list = [int(x.strip(" ")) for x in filter_list]
    #         # sorts list and converts to a tuple for hashability #
    #         filter_list.sort()
    #         filter_list = tuple(filter_list)
    #     elif filter_list == []:
    #         filter_list = None
    #     else:
    #         pass

    #     # gets id of queried neuron from table #
    #     query_out = [query_data[0]["Root ID"]]

    #     # sets nucleus coordinates #
    #     nuc = query_data[0]["Nucleus Coordinates"][1:-1].split(",")

    #     # builds url #
    #     out_url = buildAllsynLink(
    #         query_out,
    #         cleft_thresh,
    #         nuc,
    #         config=config,
    #         timestamp=timestamp,
    #         filter_list=filter_list,
    #     )

    #     return [out_url, ""]

    pass


# runs program #
if __name__ == "__main__":
    app.run_server()
