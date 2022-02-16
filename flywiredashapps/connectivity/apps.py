# Connectivity App #
from dash import Dash, dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
from nglui.statebuilder import *
import time
from utils import *

# defines blank app object and uses stylesheet for bootstrap themes #
app = Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])

# defines layout of various app elements #
app.layout = html.Div(
    [
        # defines text area for instructions and feedback#
        dbc.Textarea(
            id="message_text",
            value=(
                'Input root/nuc ID or coordinates and click "Submit" button.'
                + " Only one entry at a time."
                + " Large queries (>100k synapses) may take up to 2 minutes."
            ),
            disabled=True,
            rows=1,
            style={
                # "width": "420px",
                "resize": "none",
            },
        ),
        html.Br(),
        # defines container for input message and field #
        html.Div(
            children=[
                # defines input message #
                dcc.Textarea(
                    id="input_message_text",
                    value="Root/nucleus ID or x,y,z coords:",
                    style={
                        "width": "230px",
                        "resize": "none",
                        "display": "inline-block",
                        "vertical-align": "top",
                    },
                    rows=1,
                    disabled=True,
                ),
                # defines input field #
                dcc.Input(
                    id="input_field",
                    type="text",
                    placeholder="Root/Nuc ID or Coords",
                    style={
                        "width": "190px",
                        "display": "inline-block",
                        "vertical-align": "top",
                    },
                ),
            ],
            style={"margin-left": "5px",},
        ),
        # defines container for cleft score message and field #
        html.Div(
            children=[
                # defines cleft score message #
                dcc.Textarea(
                    id="cleft_message_text",
                    value="Cleft score threshold for synapses (default 50):",
                    style={
                        "width": "355px",
                        "resize": "none",
                        "display": "inline-block",
                        "vertical-align": "top",
                    },
                    rows=1,
                    disabled=True,
                ),
                # defines input field for cleft score threshold #
                dcc.Input(
                    id="cleft_thresh_field",
                    type="number",
                    value=50,
                    style={
                        "display": "inline-block",
                        "width": "65px",
                        "vertical-align": "top",
                    },
                ),
            ],
            style={"margin-left": "5px", "margin-top": "5px",},
        ),
        # defines sumbission button #
        dbc.Button(
            children=["Submit",],
            id="submit_button",
            n_clicks=0,
            style={
                "display": "inline-block",
                "width": "420px",
                "margin-left": "5px",
                "margin-top": "5px",
                "margin-bottom": "5px",
            },
        ),
        # defines submit button loader #
        html.Div(
            dcc.Loading(id="submit_loader", type="default", children=""),
            style={"width": "1000px",},
        ),
        html.Br(),
        # defines neurotransmitter plot display div #
        html.Div(
            id="graph_div",
            children=[],
            style={
                "display": "inline-block",
                "margin-top": "10px",
                "margin-bottom": "10px",
            },
        ),
        html.Br(),
        # defines summary table #
        html.Div(
            dash_table.DataTable(
                id="summary_table",
                style_header={
                    "whiteSpace": "normal",
                    "height": "auto",
                    "textAlign": "center",
                },
            )
        ),
        html.Br(),
        # defines incoming table #
        html.Div(dash_table.DataTable(id="incoming_table", page_size=5,)),
        html.Br(),
        # defines outgoing table #
        html.Div(dash_table.DataTable(id="outgoing_table", page_size=5)),
        html.Br(),
        # defines div for holding post-submission buttons #
        html.Div(children=[], id="post_submit_div"),
    ]
)

# defines callback that generates main tables and violin plots #
@app.callback(
    Output("post_submit_div", "children"),
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
    val_choice -- boolean option to validate synapse counts
    """

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
        # defines upstream downloader #
        html.Div(
            [
                dbc.Button(
                    "Download Upstream Partner Table as CSV File",
                    id="upstream_download_button",
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
        # defines downstream downloader #
        html.Div(
            [
                dbc.Button(
                    "Download Downstream Partner Table as CSV File",
                    id="downstream_download_button",
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
                "margin-top": "25px",
                "margin-bottom": "5px",
            },
        ),
        # defines link generation button #
        html.Div(
            children=[
                dbc.Button(
                    "Generate NG Link Using Selected Partners",
                    id="link_button",
                    n_clicks=0,
                    style={
                        "margin-top": "5px",
                        "margin-right": "5px",
                        "margin-left": "5px",
                        "margin-bottom": "5px",
                        "width": "420px",
                    },
                ),
                dcc.Link(
                    href="",
                    id="ng_link",
                    style={"margin-top": "15px", "margin-bottom": "15px",},
                ),
            ],
        ),
        # defines link button loader #
        html.Div(
            dcc.Loading(id="link_loader", type="default", children=""),
            style={"margin-right": "5px", "margin-left": "5px", "width": "1000px",},
        ),
    ]

    start_time = time.time()

    # splits 'ids' string into list #
    query_id = str(query_id).split(",")

    # strips spaces from id_list entries and converts to integers #
    query_id = [str(x.strip(" ")) for x in query_id]

    # builds output if 1-item threshold isn't exceeded #
    if (
        len(query_id) == 1
        or len(query_id) == 3
        and len(query_id[0]) != len(query_id[2])
    ):

        # converts id input to root id #
        root_id = idConvert(query_id)

        # builds dataframes and graphs #
        sum_list = makeSummaryDataFrame(root_id, cleft_thresh)
        sum_df = sum_list[0]
        up_df = makePartnerDataFrame(root_id, cleft_thresh, upstream=True)
        down_df = makePartnerDataFrame(root_id, cleft_thresh, upstream=False)
        up_violin = makeViolin(root_id, cleft_thresh, incoming=True)
        down_violin = makeViolin(root_id, cleft_thresh, incoming=False)
        up_pie = makePie(root_id, cleft_thresh, incoming=True)
        down_pie = makePie(root_id, cleft_thresh, incoming=False)

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
            # html.Br(),
            html.Div(
                dcc.Graph(id="in_pie_chart", figure=up_pie,),
                style={"display": "inline-block",},
            ),
            html.Div(
                dcc.Graph(id="out_pie_chart", figure=down_pie,),
                style={"display": "inline-block",},
            ),
        ]

        end_time = time.time()
        elapsed_time = str(round(end_time - start_time))

        # relays time information #
        message_text = (
            "Connectivity query completed in "
            + elapsed_time
            + " seconds. \n"
            + sum_list[1]
        )

        message_rows = message_text.count("\n")

        return [
            post_div,
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
            "",
            0,
            0,
            0,
            0,
            0,
            0,
            "",
            "Please limit each query to one entry.",
            "",
        ]


# defines callback that generates neuroglancer link #
@app.callback(
    Output("ng_link", "href",),
    Output("link_loader", "children",),
    Input("link_button", "n_clicks",),
    State("incoming_table", "active_cell",),
    State("outgoing_table", "active_cell",),
    State("summary_table", "data",),
    State("incoming_table", "data",),
    State("outgoing_table", "data",),
    State("cleft_thresh_field", "value",),
    prevent_initial_call=True,
)
def makeLink(n_clicks, up_id, down_id, query_data, up_data, down_data, cleft_thresh):
    """Create neuroglancer link using selected partners.
    
    Keyword arguments:
    n_clicks -- tracks clicks for create button
    up_id -- root id of upstream partner as int
    down_id -- root id of downstream partner as int
    query_data -- dataframe of summary table data
    up_data -- dataframe of incoming table data
    down_data -- dataframe of outgoing table data
    cleft_thresh -- float value of cleft threshold field
    """

    query_out = query_data[0]["Root ID"]

    if up_id is None:
        up_out = 0
    else:
        up_out = up_data[up_id["row"]]["Upstream Partner ID"]
    if down_id is None:
        down_out = 0
    else:
        down_out = down_data[down_id["row"]]["Downstream Partner ID"]

    nuc = query_data[0]["Nucleus Coordinates"][1:-1].split(",")

    out_url = buildLink([query_out], [up_out], [down_out], cleft_thresh, nuc)

    return [out_url, ""]


# defines callback that clears table selections #
@app.callback(
    Output("incoming_table", "active_cell",),
    Output("outgoing_table", "active_cell",),
    Output("incoming_table", "selected_cells",),
    Output("outgoing_table", "selected_cells",),
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
    ]


# defines callback to download summary table as csv on button press #
@app.callback(
    Output("summary_download", "data"),
    Input("summary_download_button", "n_clicks"),
    State("summary_table", "data"),
    prevent_initial_call=True,
)
def downloadSummary(n_clicks, table_data):
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

    downstream_df = pd.DataFrame(table_data)
    downstream_df.head()
    return dcc.send_data_frame(downstream_df.to_csv, "downstream_table.csv")


# runs program, may be able to choose server by using port= argument? #
if __name__ == "__main__":
    app.run_server()
