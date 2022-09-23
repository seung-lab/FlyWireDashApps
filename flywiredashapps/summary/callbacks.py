import time
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, no_update
from itertools import compress
from dash.exceptions import PreventUpdate
from .utils import *


def register_callbacks(app, config=None):
    """Set up callbacks to be passed to app.

    Keyword Arguments:
    app -- the app itself
    config -- dictionary of config settings (dict, default None)
    """

    # defines callback that generates main table #
    @app.callback(
        Output("post_submit_div", "children"),
        Output("table", "columns"),
        Output("table", "data"),
        Output("table", "tooltip_data"),
        Output("message_text", "value"),
        Output("message_text", "rows"),
        Output("submit_loader", "children"),
        Input("submit_button", "n_clicks"),
        State({"type": "url_helper", "id_inner": "input_field"}, "value",),
    )
    def update_output(n_clicks, id_list):
        """Update app based on input.
        
        Keyword arguments:
        n_clicks -- unused trigger that tracks number of times the submit button has been pressed
        id_list -- list of roots, nucs, and/or coords for input (str)
        """

        # prevents firing if no ids are submitted #
        if id_list == None:
            raise PreventUpdate

        # records start time #
        start_time = time.time()

        # removes quotes from input #
        try:
            id_list = str(id_list).replace('"', "")
        except:
            pass
        try:
            id_list = str(id_list).replace("'", "")
        except:
            pass

        # defines div containing post-submission content #
        post_div = [
            html.Div(
                [
                    # defines summary download button #
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
                    # defines NG link button loader #
                    html.Div(
                        dcc.Loading(id="link_loader", type="default", children=""),
                        style={
                            "margin-right": "5px",
                            "margin-left": "5px",
                            "width": "1000px",
                        },
                    ),
                    # defines NG link generation button #
                    dbc.Button(
                        "Generate NG Link Using Selected Root IDs",
                        id="link_button",
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
                    # defines Connectivity App link button loader #
                    html.Div(
                        dcc.Loading(
                            id="connectivity_link_loader", type="default", children="",
                        ),
                        style={
                            "margin-right": "5px",
                            "margin-left": "5px",
                            "width": "1000px",
                        },
                    ),
                    # defines Connectivity App link generation button #
                    dbc.Button(
                        "Select Neuron to Port to Connectivity App",
                        id="connectivity_link_button",
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
                        "Clear Selections",
                        id="clear_button",
                        n_clicks=0,
                        color="danger",
                        style={
                            "width": "420px",
                            "margin-right": "5px",
                            "margin-left": "5px",
                            "margin-top": "5px",
                            "margin-bottom": "25px",
                            "vertical-align": "top",
                        },
                    ),
                ]
            ),
            # defines summary downloader #
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
                no_update,
                "Please limit each query to a maximum of 20 items.",
                1,
                "",
            ]
        else:
            # removes duplicates #
            root_set = set(root_list)
            output_df = rootListToDataFrame(list(root_set), config)

            # creates column list based on dataframe columns #
            column_list = [{"name": i, "id": i} for i in output_df.columns]

            # converts df to dict #
            data_dict = output_df.to_dict("records")

            # logs end time and calculates run time #
            end_time = time.time()
            elapsed_time = str(round(end_time - start_time))

            # builds message using time information #
            message_text = "Query completed in " + elapsed_time + " seconds."
            mess_rows = 1

            # adds message if any duplicates were removed #
            dupes = len(root_list) - len(root_set)
            if dupes == 1:
                message_text = (
                    message_text + " " + str(dupes) + " duplicate entry removed."
                )
                mess_rows = 2
            if dupes > 1:
                message_text = (
                    message_text + " " + str(dupes) + " duplicate entries removed."
                )
                mess_rows = 2

            # creates list of dicts for each row in data_dicts #
            # each dict has a single id-key pair of the column name paired with another dict #
            # each of these dicts is {"value" : string value of that row, "type": "markdown"} #
            # this allows for markdown syntax to make the ids in the table into refeeder links #
            tooltip_data = [
                {
                    column: {"value": str(value), "type": "markdown"}
                    for column, value in row.items()
                }
                for row in data_dict
            ]

            return [
                post_div,
                column_list,
                data_dict,
                tooltip_data,
                message_text,
                mess_rows,
                "",
            ]

    # defines callback to download summary table as csv on button press #
    @app.callback(
        Output("summary_download", "data"),
        Input("summary_download_button", "n_clicks"),
        State("table", "data"),
        prevent_initial_call=True,
    )
    def downloadSummary(n_clicks, table_data):
        """Download table as csv file.

        Keyword Arguments:
        n_clicks -- unused trigger that counts how many times the download button has been pressed
        table_data -- table data
        """
        # convert table data to dataframe #
        summary_df = pd.DataFrame(table_data)

        # converts nucleus coord strings to actual list while preserving non-list strings #
        replacement_col = []
        for x in summary_df["Nucleus Coordinates"]:
            if "[" in x:
                replacement_col.append([int(y.strip()) for y in x[1:-1].split(",")])
            else:
                replacement_col.append(x)

        summary_df["Nucleus Coordinates"] = replacement_col

        # convert dataframe to csv and send to user #
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
        rows -- selected upstream row indices (list)
        table_data -- summary table data (dataframe)
        cb -- colorblind option (bool, default False)
        """

        # generates root list using table data and selected rows #
        root_list = [table_data[x]["Root ID"] for x in rows]

        # removes bad IDs #
        bad_mask = [table_data[x]["Nuc ID"] != "BAD ID" for x in rows]
        root_list = list(compress(root_list, bad_mask))

        # handles situations where all ids are removed by bad_mask #
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
        n_clicks -- unused trigger that tracks clicks for clear button
        """
        return [
            None,
            [],
        ]

    # defines callback that generates connectivity app link  #
    @app.callback(
        Output("connectivity_link_button", "href",),
        Output("connectivity_link_button", "children",),
        Output("connectivity_link_loader", "children",),
        Input("table", "selected_rows",),
        State("table", "data",),
        prevent_initial_call=True,
    )
    def makeConnLink(rows, table_data):
        """Create connectivity app link using selected IDs.

        Keyword arguments:
        rows -- selected upstream row indices (list)
        table_data -- summary table data
        """

        # generates root list using table data and selected rows #
        root_list = [table_data[x]["Root ID"] for x in rows]
        bad_list = [table_data[x]["Current"] for x in rows]

        # handles errors #
        if len(root_list) == 0:
            return ["", "Select Neuron to Port to Connectivity App", ""]
        if len(root_list) > 1:
            return ["", "Select Only 1 Neuron to Port to Connectivity App", ""]
        elif bad_list[0] == "BAD ID" or bad_list[0] == False:
            return ["", "Select Current, Valid Neuron to Port to Connectivity App", ""]

        # builds url using portUrl function #
        out_url = portUrl(str(root_list[0]), "connectivity", config)

        # returns url string, alters button text, sends empty string for loader #
        return [out_url, "Send selected neuron to Connectivity App", ""]

    # defines callback that generates partner app link  #
    @app.callback(
        Output("partner_link_button", "href",),
        Output("partner_link_button", "children",),
        Output("partner_link_loader", "children",),
        Input("table", "selected_rows",),
        State("table", "data",),
        prevent_initial_call=True,
    )
    def makePartLink(rows, table_data):
        """Create partner app link using selected IDs.

        Keyword arguments:
        rows -- selected upstream row indices (list)
        table_data -- summary table data
        """

        # generates root list using table data and selected rows #
        root_list = [table_data[x]["Root ID"] for x in rows]
        bad_list = [table_data[x]["Current"] for x in rows]

        # handles errors #
        if len(root_list) == 0:
            return ["", "Select 2 neurons to port to Partner App", ""]
        if len(root_list) != 2:
            return ["", "Select exactly 2 neurons to send to Partner App", ""]
        elif "BAD ID" in bad_list or False in bad_list:
            return ["", "Select only current, valid neurons to send to Partner App", ""]

        # builds url using portUrl function #
        out_url = portUrl(str(root_list)[1:-1], "partner", config)

        # returns url string, alters button text, sends empty string for loader #
        return [out_url, "Send selected neurons to Partner App", ""]

    pass


# runs program #
if __name__ == "__main__":
    app.run_server()
