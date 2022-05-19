import time
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, no_update
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
        State({"type": "url_helper", "id_inner": "input_field"}, "value",),
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
                    no_update,
                    no_update,
                    no_update,
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
        table_data -- dataframe of summary table data
        cb -- bool to determine colorblind option (default False)
        """

        # generates root list using table data and selected rows #
        root_list = [table_data[x]["Root ID"] for x in rows]

        # removes bad IDs #
        bad_mask = [table_data[x]["Nuc ID"] != "BAD ID" for x in rows]
        print(bad_mask)
        root_list = list(compress(root_list, bad_mask))

        if root_list == []:
            return ["", ""]

        # generates nuc list the same way #
        nuc_list = [table_data[x]["Nucleus Coordinates"] for x in rows]

        # creates a list of bools to weed out bad ids and cells without nuclei #
        bool_filter = [
            x != "n/a" and x != "BAD ID" and x != "Multiple Nuc Returns"
            for x in nuc_list
        ]

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

    # defines callback that clears table selections #
    @app.callback(
        Output("table", "active_cell",),
        Output("table", "selected_rows",),
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
            [],
        ]

    # # defines callback that throws error message if link button is clicked with no selections #
    # @app.callback(
    #     Output("message_text", "value",),
    #     Input("link_button", "n_clicks"),
    #     State("table", "selected_rows",),
    #     prevent_initial_call=True,
    # )
    # def noSelError(n_clicks, rows):
    #     """Throw error message if link button is clicked with no selections.

    #     Keyword arguments:
    #     n_clicks -- number of times link button has been pressed
    #     rows -- list of selected upstream row indices
    #     """

    #     if rows == []:
    #         return "No rows selected, please select one or more rows from the table using their checkboxes."
    #     else:
    #         return no_update

    pass


# runs program #
if __name__ == "__main__":
    app.run_server()
