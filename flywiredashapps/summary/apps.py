import time
import dash
import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, Input, Output, State, dash_table
from utils import *

app = Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])

# defines layout of various app elements (submission field, checkboxes, button, output table) #
app.layout = html.Div(
    [
        # defines text area to relay messages #
        dbc.Textarea(
            id="message_text",
            value="Input Root IDs, Nuc IDs, or coords in 4,4,40nm\n"
            "ID queries are limited to 20 entries.\n"
            "Coordinate lookups must be done one at a time.\n"
            "Lookup takes ~2-3 seconds per entry.",
            style={
                "width": "420px",
                "resize": "none",
                "margin-right": "5px",
                "margin-left": "5px",
                "margin-top": "5px",
                "margin-bottom": "5px",
            },
            rows=4,
            disabled=True,
        ),
        # defines input field for ids #
        html.Div(
            [
                dbc.Input(
                    id="input_field",
                    type="text",
                    placeholder="Root/Nuc ID or Coords",
                    style={
                        "width": "185px",
                        "display": "inline-block",
                        "vertical-align": "top",
                        "margin-right": "5px",
                        "margin-left": "5px",
                        "margin-top": "5px",
                        "margin-bottom": "5px",
                    },
                ),
                # defines submission button #
                dbc.Button(
                    "Submit",
                    id="submit_button",
                    n_clicks=0,
                    style={
                        "width": "225px",
                        "display": "inline-block",
                        "vertical-align": "top",
                        "margin-right": "5px",
                        "margin-left": "5px",
                        "margin-top": "5px",
                        "margin-bottom": "5px",
                    },
                ),
            ]
        ),
        html.Br(),
        # defines output table #
        html.Div(
            dash_table.DataTable(
                id="table",
                style_header={
                    "whiteSpace": "normal",
                    "height": "auto",
                    "textAlign": "center",
                },
            ),
            style={"margin-left": "5px", "margin-right": "5px"},
        ),
        html.Div(children=[], id="post_submit_div"),
    ]
)


@app.callback(
    Output("post_submit_div", "children"),
    Output("table", "columns"),
    Output("table", "data"),
    Output("message_text", "value"),
    Output("message_text", "rows"),
    Input("submit_button", "n_clicks"),
    State("input_field", "value"),
    prevent_initial_call=True,
)
def update_output(n_clicks, id_list):

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
            ]
        ),
        dcc.Download(id="summary_download"),
    ]

    root_list = inputToRootList(id_list)
    if len(root_list) > 20:
        return [0, 0, 0, "Please limit each query to a maximum of 20 items.", 1]
    else:
        output_df = rootListToDataFrame(root_list)
        # creates column list based on dataframe columns #
        column_list = [{"name": i, "id": i} for i in output_df.columns]
        data_dict = output_df.to_dict("records")

        end_time = time.time()
        elapsed_time = str(round(end_time - start_time))

        # relays time information #
        message_text = "Query completed in " + elapsed_time + " seconds."

        return [post_div, column_list, data_dict, message_text, 1]


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


if __name__ == "__main__":
    app.run_server()
