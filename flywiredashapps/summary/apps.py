import time
import dash
from dash import dcc, html, Input, Output, State, dash_table
from utils import *

app = dash.Dash(__name__)

# defines layout of various app elements (submission field, checkboxes, button, output table) #
app.layout = html.Div(
    [
        # defines text area to relay messages #
        dcc.Textarea(
            id="message_text",
            value="Input Root IDs, Nuc IDs, or coords in 4,4,40nm\n"
            "ID queries are limited to 20 entries, coordinate lookups must be done one at a time.\n"
            "Lookup takes ~2-3 seconds per entry.",
            style={"width": "650px", "resize": "none"},
            rows=3,
            disabled=True,
        ),
        # defines input field for ids #
        html.Div(dcc.Input(id="input_field", type="text", placeholder="ID Number",)),
        html.Br(),
        # defines submission button #
        html.Button("Submit", id="submit_button", n_clicks=0,),
        html.Br(),
        # defines output table #
        html.Div(
            dash_table.DataTable(
                id="table",
                export_format="csv",
                style_header={
                    "whiteSpace": "normal",
                    "height": "auto",
                    "textAlign": "center",
                },
            )
        ),
    ]
)


@app.callback(
    Output("table", "columns"),
    Output("table", "data"),
    Output("message_text", "value"),
    Input("submit_button", "n_clicks"),
    State("input_field", "value"),
    prevent_initial_call=True,
)
def update_output(n_clicks, id_list):
    start_time = time.time()
    root_list = inputToRootList(id_list)
    if len(root_list) > 20:
        return [0, 0, "Please limit each query to a maximum of 20 items."]
    else:
        output_df = rootListToDataFrame(root_list)
        # creates column list based on dataframe columns #
        column_list = [{"name": i, "id": i} for i in output_df.columns]
        data_dict = output_df.to_dict("records")

        end_time = time.time()
        elapsed_time = str(round(end_time - start_time))

        # relays time information #
        message_text = "Query completed in " + elapsed_time + " seconds."

        return [column_list, data_dict, message_text]


if __name__ == "__main__":
    app.run_server()
