# Connectivity App #
from dash import Dash, dcc, html, Input, Output, State, dash_table
from dash.exceptions import PreventUpdate
from caveclient import chunkedgraph
import dash_bootstrap_components as dbc
from nglui.statebuilder import *
import time
import urllib.parse
from .utils import *


def register_callbacks(app, config=None):
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
        State("input_field", "value"),
        State("cleft_thresh_field", "value"),
        prevent_initial_call=True,
    )
    def update_output(n_clicks, query_id, cleft_thresh):
        """Create summary and partner tables with violin plots for queried root id.

        Keyword arguments:
        n_clicks -- tracks clicks for submit button
        query_id -- root id of queried neuron as int
        cleft_thresh -- float value of cleft score threshold
        """
        if query_id != None:
            post_div_linkbuttons = [
                html.Div(
                    [
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
                        # defines button to clear table selections #
                        dbc.Button(
                            "Clear Partner Selections",
                            id="clear_button",
                            n_clicks=0,
                            color="danger",
                            style={
                                "width": "400px",
                                "margin-right": "5px",
                                "margin-left": "5px",
                                "margin-top": "5px",
                                "margin-bottom": "25px",
                                "display": "inline-block",
                                "vertical-align": "top",
                            },
                        ),
                        # unused colorblind option checkbox #
                        # dbc.Checklist(
                        #     options=[{"label": "Colorblind", "value": True},],
                        #     value=[False],
                        #     id="cb_input",
                        # ),
                        # defines link button loader #
                        html.Div(
                            dcc.Loading(id="link_loader", type="default", children=""),
                            style={
                                "margin-right": "5px",
                                "margin-left": "5px",
                                "width": "1000px",
                            },
                        ),
                    ],
                ),
            ]

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

            # sets start time #
            start_time = time.time()

            # splits 'ids' string into list #
            query_id = str(query_id).split(",")

            # strips spaces and brackets from id_list entries and converts to integers #
            query_id = [str(x.strip(" ")) for x in query_id]
            query_id = [str(x.strip("[")) for x in query_id]
            query_id = [int(str(x.strip("]"))) for x in query_id]

            # builds output if 1-item threshold isn't exceeded #
            if (
                len(query_id) == 1
                or len(query_id) == 3
                and len(str(query_id[0])) != len(str(query_id[2]))
            ):

                # converts id input to root id #
                root_id = idConvert(query_id, config=config)

                # throws error if root id is outdated #
                if checkFreshness(root_id, config=config) == False:
                    return [
                        [],
                        [],
                        [],
                        [],
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        [],
                        "Root ID is outdated, please refresh the segment or use x,y,z coordinates in 4x4x40nm resolution.",
                        1,
                        "",
                    ]

                # should handle cases with bad ids, currently circumvented #
                if root_id == 0:
                    return [
                        [],
                        [],
                        [],
                        [],
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        [],
                        "Entry must be 18-digit root id, 7-digit nucleus id, or x,y,z coordinates in 4x4x40nm resolution.",
                        1,
                        "",
                    ]

                # builds dataframes and graphs #
                sum_list = makeSummaryDataFrame(root_id, cleft_thresh, config=config)
                sum_df = sum_list[0]
                up_df = makePartnerDataFrame(
                    root_id, cleft_thresh, upstream=True, config=config
                )
                down_df = makePartnerDataFrame(
                    root_id, cleft_thresh, upstream=False, config=config
                )
                up_violin = makeViolin(
                    root_id, cleft_thresh, incoming=True, config=config
                )
                down_violin = makeViolin(
                    root_id, cleft_thresh, incoming=False, config=config
                )
                up_pie = makePie(root_id, cleft_thresh, incoming=True, config=config)
                down_pie = makePie(root_id, cleft_thresh, incoming=False, config=config)

                # assigns df values to 'cols' and 'data' for passing to dash table #
                sum_cols = [{"name": i, "id": i,} for i in sum_df.columns]
                up_cols = [{"name": i, "id": i,} for i in up_df.columns]
                down_cols = [{"name": i, "id": i,} for i in down_df.columns]
                sum_data = sum_df.to_dict("records")
                up_data = up_df.to_dict("records")
                down_data = down_df.to_dict("records")

                # builds list of figures to pass to children of graph_div #
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

                # sets end time #
                end_time = time.time()
                # calculates elapsed time #
                elapsed_time = str(round(end_time - start_time))

                # relays time information #
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

            # returns error message if 1-item threshold is exceeded #
            else:
                return [
                    [],
                    [],
                    [],
                    [],
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    [],
                    "Please limit each query to one entry.",
                    1,
                    "",
                ]
        else:
            raise PreventUpdate

    # defines callback that generates neuroglancer link #
    @app.callback(
        Output("link_button", "href",),
        Output("link_loader", "children",),
        Input("incoming_table", "selected_rows",),
        Input("outgoing_table", "selected_rows",),
        State("summary_table", "data",),
        State("incoming_table", "data",),
        State("outgoing_table", "data",),
        State("cleft_thresh_field", "value",),
        prevent_initial_call=True,
    )
    def makeLink(up_rows, down_rows, query_data, up_data, down_data, cleft_thresh):
        """Create neuroglancer link using selected partners.

        Keyword arguments:
        up_rows -- list of selected upstream row indices
        down_rows -- list of selected downstream row indices
        query_data -- dataframe of summary table data
        up_data -- dataframe of incoming table data
        down_data -- dataframe of outgoing table data
        cleft_thresh -- float value of cleft threshold field
        cb -- bool to determine colorblind option
        """

        query_out = [query_data[0]["Root ID"]]

        if up_rows == [] or up_rows == None:
            up_out = [0]
        else:
            up_out = [up_data[up_rows[x]]["Upstream Partner ID"] for x in up_rows]
        if down_rows == [] or down_rows == None:
            down_out = [0]
        else:
            down_out = [
                down_data[down_rows[x]]["Downstream Partner ID"] for x in down_rows
            ]

        nuc = query_data[0]["Nucleus Coordinates"][1:-1].split(",")

        out_url = buildLink(
            query_out, up_out, down_out, cleft_thresh, nuc, config=config
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
        n_clicks -- tracks clicks for clear button
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
        n_clicks -- tracks clicks for download button
        table_data -- data from summary table
        """
        summary_df = pd.DataFrame(table_data)
        return dcc.send_data_frame(summary_df.to_csv, "summary_table.csv")

    # defines callback to download upstream table as csv on button press #
    @app.callback(
        Output("upstream_download", "data"),
        Input("upstream_download_button", "n_clicks"),
        State("incoming_table", "data"),
        prevent_initial_call=True,
    )
    def downloadUpstream(n_clicks, table_data):
        """Download upstream table as csv file.

        Keyword arguments:
        n_clicks -- tracks clicks for download button
        table_data -- data from upstream table
        """
        upstream_df = pd.DataFrame(table_data)
        return dcc.send_data_frame(upstream_df.to_csv, "upstream_table.csv")

    # defines callback to download downstream table as csv on button press #
    @app.callback(
        Output("downstream_download", "data"),
        Input("downstream_download_button", "n_clicks"),
        State("outgoing_table", "data"),
        prevent_initial_call=True,
    )
    def downloadDownstream(n_clicks, table_data):
        """Download downstream table as csv file.

        Keyword arguments:
        n_clicks -- tracks clicks for download button
        table_data -- data from downstream table
        """
        downstream_df = pd.DataFrame(table_data)
        downstream_df.head()
        return dcc.send_data_frame(downstream_df.to_csv, "downstream_table.csv")

    # defines callback to check for url parameters on pageload and feed into app #
    @app.callback(
        Output("input_field", "value"),
        Output("cleft_thresh_field", "value"),
        Output("submit_button", "n_clicks"),
        Input("url", "href"),
        State("input_field", "value"),
    )
    def url_check(url_search, tempinput):
        """Check url for params, feed into app if found.

        Keyword arguments:
        url_search -- url as string
        """

        # parses url queries #
        parsed = urllib.parse.urlparse(url_search)
        # parses parsed into dictionary #
        parsed_dict = urllib.parse.parse_qs(parsed.query)

        # sets button press output to default 0 #
        bp = 0

        # tries to assign root and thresh values using query #
        # increases button press to 1 if either found #
        try:
            root_query = parsed_dict["root_id"][0]
            bp = 1
        except:
            root_query = None
        try:
            thresh_query = int(parsed_dict["cleft_thresh"][0])
            bp = 1
        except:
            thresh_query = 50

        return [root_query, thresh_query, bp]

    # defines callback to feed input root id into url query parameter #
    @app.callback(
        Output("url", "href"),
        Input("submit_button", "n_clicks"),
        State("input_field", "value"),
        State("cleft_thresh_field", "value"),
        State("url", "href"),
        prevent_initial_call=True,
    )
    def inputToSearch(n_clicks, root_id, cleft_thresh, url_href):
        """Convert root id into url string.

        Keyword Arguments:
        n_clicks -- used to trigger on submission
        root_id -- root id (can be anything)
        cleft_thresh -- cleft score threshold as int
        url_href -- the entire url as a string
        """

        # splits query params off core address if present #
        if "?" in url_href:
            core_address, query_dummy = url_href.split("?")
        else:
            core_address = url_href

        core_with_query = (
            core_address
            + "?root_id="
            + str(root_id)
            + "&cleft_thresh="
            + str(cleft_thresh)
        )

        # returns core address if no input given, otherwise, adds input as query #
        if root_id != None:
            return core_with_query
        else:
            return core_address

    pass


# runs program, may be able to choose server by using port= argument? #
if __name__ == "__main__":
    app.run_server()
