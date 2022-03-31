import time
import dash
import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, Input, Output, State, dash_table
import urllib.parse
from itertools import compress
from dash.exceptions import PreventUpdate
from .utils import *


def register_callbacks(app, config=None):
    @app.callback(
        Output("post_submit_div", "children"),
        Output("table", "columns"),
        Output("table", "data"),
        Output("message_text", "value"),
        Output("message_text", "rows"),
        Output("submit_loader", "children"),
        Input("submit_button", "n_clicks"),
        State("input_field", "value"),
        prevent_initial_call=True,
    )
    def update_output(n_clicks, id_list):
        if id_list != None:
            start_time = time.time()

            post_div = [
                # defines summary downloader #
                html.Div(
                    [
                        dbc.Button(
                            "Download Summary Table as CSV File",
                            id="summary_download_button",
                            style={
                                "width": "420px",
                                "margin-right": "5px",
                                "margin-left": "5px",
                                "margin-top": "5px",
                                "margin-bottom": "5px",
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
                        # defines link generation button #
                        dbc.Button(
                            "Generate NG Link Using Selected Root IDs",
                            id="link_button",
                            n_clicks=0,
                            target="tab",
                            style={
                                "margin-top": "5px",
                                "margin-right": "5px",
                                "margin-left": "5px",
                                "margin-bottom": "5px",
                                "width": "400px",
                                # "display": "inline-block",
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
                                # "display": "inline-block",
                                "vertical-align": "top",
                            },
                        ),
                    ]
                ),
                dcc.Download(id="summary_download"),
            ]

            # generates root list from input list #
            root_list = inputToRootList(id_list, config)

            # enforces 20-item limit on input
            if len(root_list) > 20:
                return [
                    0,
                    0,
                    0,
                    "Please limit each query to a maximum of 20 items.",
                    1,
                    "",
                ]
            else:

                output_df = rootListToDataFrame(root_list, config)

                # creates column list based on dataframe columns #
                column_list = [{"name": i, "id": i} for i in output_df.columns]

                data_dict = output_df.to_dict("records")

                end_time = time.time()
                elapsed_time = str(round(end_time - start_time))

                # relays time information #
                message_text = "Query completed in " + elapsed_time + " seconds."

                return [post_div, column_list, data_dict, message_text, 1, ""]

        # handles no url input #
        else:
            raise PreventUpdate

    # defines callback to download summary table as csv on button press #
    @app.callback(
        Output("summary_download", "data"),
        Input("summary_download_button", "n_clicks"),
        State("table", "data"),
        prevent_initial_call=True,
    )
    def downloadSummary(n_clicks, table_data):
        summary_df = pd.DataFrame(table_data)
        return dcc.send_data_frame(summary_df.to_csv, "summary_table.csv")

    # defines callback to feed input root id into url query parameter #
    @app.callback(
        Output("url", "href"),
        Input("submit_button", "n_clicks"),
        State("input_field", "value"),
        State("url", "href"),
        prevent_initial_call=True,
    )
    def inputToSearch(n_clicks, root_ids, url_href):
        """Convert input into url string.

        Keyword Arguments:
        n_clicks -- used to trigger on submission
        root_id -- root id (can be anything)
        url_href -- the entire url as a string
        """

        # splits query params off core address if present #
        if "?" in url_href:
            core_address, query_dummy = url_href.split("?")
        else:
            core_address = url_href

        core_with_query = core_address + "?root_ids=" + str(root_ids)

        # returns core address if no input given, otherwise, adds input as query #
        if root_ids != None:
            return core_with_query
        else:
            return core_address

    # defines callback to check for url parameters on pageload and feed into app #
    @app.callback(
        Output("input_field", "value"),
        Output("submit_button", "n_clicks"),
        Input("url", "href"),
        State("submit_button", "n_clicks"),
    )
    def url_check(url_search, n_clicks):
        """Check url for params, feed into app if found.

        Keyword arguments:
        url_search -- url as string
        """
        if n_clicks == 0:
            # parses url queries #
            parsed = urllib.parse.urlparse(url_search)
            # parses parsed into dictionary #
            parsed_dict = urllib.parse.parse_qs(parsed.query)

            # sets button press output to default 0 #
            bp = 0

            # tries to assign roots using query #
            try:
                root_query = parsed_dict["root_ids"][0]
                # increases button press to 1 to submit if found #
                bp = 1
            except:
                root_query = None

            return [root_query, bp]
        else:
            raise PreventUpdate

        # defines callback that generates neuroglancer link #

    @app.callback(
        Output("link_button", "href",),
        Output("link_loader", "children",),
        Input("table", "selected_rows",),
        State("table", "data",),
        prevent_initial_call=True,
    )
    def makeLink(rows, table_data, cb=False):
        """Create neuroglancer link using selected IDs.

        Keyword arguments:
        rows -- list of selected upstream row indices
        data -- dataframe of summary table data
        cb -- bool to determine colorblind option (default False)
        """

        # generates root list using table data and selected rows #
        root_list = [int(table_data[rows[x]]["Root ID"]) for x in rows]

        # generates nuc list the same way #
        nuc_list = [table_data[rows[x]]["Nucleus Coordinates"] for x in rows]

        # creates a list of bools to weed out bad ids and cells without nuclei #
        bool_filter = [x != "n/a" and x != "BAD ID" for x in nuc_list]

        # applies the filter to the nuc list #
        nuc_list = list(compress(nuc_list, bool_filter))

        # converts the nuc list to a dict #
        # while also converting the coordinate strings to lists of ints #
        nuc_dict = {
            "pt_position": [
                [int(y.strip(" []")) for y in x.split(",")] for x in nuc_list
            ]
        }

        # builds url using buildSummaryLink function #
        out_url = buildSummaryLink(root_list, nuc_dict, cb=cb, config=config)

        # returns url string and empty string for loader #
        return [out_url, ""]

    pass


# runs program #
if __name__ == "__main__":
    app.run_server()
