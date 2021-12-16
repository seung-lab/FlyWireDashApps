from caveclient import CAVEclient
import cloudvolume
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import json
from nglui.statebuilder import *
from annotationframeworkclient import FrameworkClient
import dash
from dash import Dash, dcc, html, Input, Output, State, dash_table


def buildLink(
    query_id, up_ids, down_ids, cleft_thresh, nucleus, cb=False,
):
    """Generate NG link.
    
    Keyword arguments:
    query_id -- single queried root id as list of int
    up_ids -- root ids of upstream partners as list of ints
    down_ids -- root ids of downstream partners as list of ints
    cleft_thresh -- cleft score threshold to drop synapses as float 
    nucleus -- x,y,z coordinates of query nucleus as list of ints
    cb -- boolean option to make colorblind-friendly (default False)
    """

    # checks for colorblind option, sets color #
    if cb:
        up_color = "#ffffff"  # white #
        query_color = "#999999"  # 40% grey #
        down_color = "#323232"  # 80% grey #
    else:
        up_color = "#00ffff"  # cyan #
        query_color = "#ff00ff"  # magenta #
        down_color = "#ffff00"  # yellow #

    # builds id and color lists #
    id_list = query_id + up_ids + down_ids
    up_cols = [up_color] * len(up_ids)
    down_cols = [down_color] * len(down_ids)
    color_list = [query_color] + up_cols + down_cols

    # sets Framework client using flywire production datastack #
    Fclient = FrameworkClient("flywire_fafb_production")

    # sets configuration for EM layer #
    img = ImageLayerConfig(Fclient.info.image_source())

    # sets configuration for segmentation layer #
    seg = SegmentationLayerConfig(
        name="seg",
        source=Fclient.info.segmentation_source(),
        fixed_ids=id_list,
        fixed_id_colors=color_list,
        view_kws={"alpha_3d": 0.8},
    )

    # sets CAVE client #
    Cclient = CAVEclient("flywire_fafb_production")

    # gets current materialization version #
    mat_vers = max(Cclient.materialize.get_versions())

    # generates synapse dfs using up- & downstream ids #
    up_df = Cclient.materialize.query_table(
        "synapses_nt_v1",
        filter_in_dict={"pre_pt_root_id": up_ids, "post_pt_root_id": query_id,},
        materialization_version=mat_vers,
    )
    down_df = Cclient.materialize.query_table(
        "synapses_nt_v1",
        filter_in_dict={"pre_pt_root_id": query_id, "post_pt_root_id": down_ids,},
        materialization_version=mat_vers,
    )

    # combines synapse dfs #
    syns_df = up_df.append(down_df, ignore_index=True,)

    # removes synapses below cleft threshold #
    syns_df = syns_df[syns_df["cleft_score"] >= cleft_thresh].reset_index(drop=True)

    # makes truncated df of pre & post coords #
    coords_df = pd.DataFrame(
        {
            "pre": [
                [x[0] / 4, x[1] / 4, x[2] / 40,] for x in syns_df["pre_pt_position"]
            ],
            "post": [
                [x[0] / 4, x[1] / 4, x[2] / 40,] for x in syns_df["post_pt_position"]
            ],
        }
    )

    # defines configuration for line annotations #
    lines = LineMapper(point_column_a="pre", point_column_b="post",)

    # defines configuration for annotation layer #
    anno = AnnotationLayerConfig(name="synapses", mapping_rules=lines,)

    # sets view to nucelus of query cell #
    # defaults to center of dataset if no input #
    if int(nucleus[0]) > 0:
        view_options = {
            "position": nucleus,
            "zoom_3d": 2000,
        }
    else:
        view_options = {
            "position": [119412, 62016, 3539,],
            "zoom_3d": 10000,
        }

    # defines 'sb' by passing in rules for img, seg, and anno layers #
    sb = StateBuilder([img, seg, anno,], view_kws=view_options,)

    # renders state as json and converts dumped json produced by #
    # render_state into non-dumped version using json.loads() #
    state_json = json.loads(sb.render_state(coords_df, return_as="json",))

    # feeds state_json into state uploader to set the value of 'new_id' #
    new_id = Fclient.state.upload_state_json(state_json)

    # defines url using builder, passing in the new_id and the ngl url #
    url = Fclient.state.build_neuroglancer_url(
        state_id=new_id, ngl_url="https://ngl.flywire.ai/",
    )

    return url


def checkValid(
    up_df, down_df, incoming_df, outgoing_df,
):
    """Check validity of constructed synapse number data.

    Keyword arguments:
    up_df -- dataframe of upstream partners
    down_df -- dataframe of downstream partners
    incoming_df -- dataframe of incoming synapses
    outgoing_df -- dataframe of outgoing synapses
    """

    # sets counter #
    counter = 0

    # validates upstream partners #
    for x in up_df.index:
        built_con = up_df.loc[
            x, "Connections",
        ]
        quer_con = str(
            list(incoming_df["pre_pt_root_id"].astype(str)).count(
                up_df.loc[x, "Upstream Partner ID"]
            )
        )

        # checks that constructed and queried results are the same #
        # NT checks not yet implemented #
        if built_con == quer_con:
            counter += 1
        else:
            failed = (
                counter
                + " items validated. Upstream data false for partner "
                + up_df.loc[x, "Upstream Partner ID",]
                + ". Built count = "
                + built_con
                + ". Query count = "
                + quer_con
            )
            return failed

    # validates downstream partners #
    for x in down_df.index:

        built_con = down_df.loc[
            x, "Connections",
        ]

        quer_con = str(
            list(outgoing_df["post_pt_root_id"].astype(str)).count(
                down_df.loc[x, "Downstream Partner ID",]
            )
        )

        if built_con == quer_con:
            counter += 1
        else:
            failed = (
                counter
                + " items validated. Downstream data false for partner "
                + down_df.loc[x, "Downstream Partner ID",]
                + ". Built count = "
                + built_con
                + ". Query count = "
                + quer_con
            )
            return failed

    return "All " + str(counter) + " items have been validated."


def coordConvert(coords):
    """Convert coordinates to 4,4,40 nm resolution.

    Keyword arguments:
    coords -- list of x,y,z coordinates as ints in 1,1,1 nm resolution
    """

    x = coords
    x[0] /= 4
    x[1] /= 4
    x[2] /= 40
    x = [int(str(i).strip()) for i in x]
    return x


def coordsToRoot(coords):
    """Convert coordinates in 4,4,40 nm resolution to root id.

    Keyword arguments:
    coords -- list of x,y,z coordinates as strings in 4,4,40 nm resolution
    """

    # converts coordinates to ints #
    coords = list(map(int, coords))

    # sets client #
    client = CAVEclient("flywire_fafb_production")

    # sets cloud volume #
    cv = cloudvolume.CloudVolume(
        "graphene://https://prod.flywire-daf.com/segmentation/1.0/fly_v31",
        use_https=True,
    )

    # determines resolution of volume #
    res = cv.resolution

    # converts coordinates using volume resolution #
    cv_xyz = [
        int(coords[0] / (res[0] / 4)),
        int(coords[1] / (res[1] / 4)),
        int(coords[2] / (res[2] / 40)),
    ]

    # sets point by passing converted coords to 'download_point' method #
    point = int(cv.download_point(cv_xyz, size=1,))

    # looks up sv's associated root id, converts to string #
    root_result = str(client.chunkedgraph.get_root_id(supervoxel_id=point))

    return root_result


def dfBuilder(input_list, cleft_thresh, validate):
    """Build dataframes for summary and partners.
    
    Keyword arguments:
    input_list -- list of int-format root or nucleus ids, or one x,y,z coordinate
    cleft_thresh -- cleft score threshold to drop synapses as float
    validate -- boolean option to validate synapse counts
    """

    # if coordinates detected, converts to root #
    if len(input_list) == 3:
        input_list = [coordsToRoot(input_list)]

    # uses root or nuc id to build nuc df #
    nuc_df = getNuc(input_list)

    # uses root id to build synapse dataframes #
    syn_sum_df, up_df, down_df, val_status = getSyn(
        [str(nuc_df.loc[0, "Root ID",])], cleft_thresh, validate,
    )

    # joins synapse summary to nucleus df to create summary df #
    sum_df = nuc_df.join(syn_sum_df.set_index("Root ID"), on="Root ID",)

    # returns output dataframes #
    return [sum_df, up_df, down_df, val_status]


def getNuc(id_list):
    """Build a dataframe of nucleus table data in string format.
    
    Keyword arguments:
    id_list -- root or nucleus id formatted as listed int
    """

    # sets client #
    client = CAVEclient("flywire_fafb_production")

    # gets current materialization version #
    mat_vers = max(client.materialize.get_versions())

    # pulls nucleus table results based on query type #
    if len(id_list[0]) == 7:
        nuc_df = client.materialize.query_table(
            "nuclei_v1",
            filter_in_dict={"id": id_list},
            materialization_version=mat_vers,
        )
    elif len(id_list[0]) == 18:
        nuc_df = client.materialize.query_table(
            "nuclei_v1",
            filter_in_dict={"pt_root_id": id_list},
            materialization_version=mat_vers,
        )

    # converts nucleus coordinates from n to 4x4x40 resolution #
    nuc_df["pt_position"] = [coordConvert(i) for i in nuc_df["pt_position"]]

    # creates output df using root, nuc id, and coords to keep aligned #
    out_df = pd.DataFrame(
        {
            "Root ID": list(nuc_df["pt_root_id"]),
            "Nucleus ID": list(nuc_df["id"]),
            "Nucleus Coordinates": list(nuc_df["pt_position"]),
        }
    )

    return out_df.astype(str)


def getSyn(
    root_id, cleft_thresh=0.0, validate=False,
):
    """Build a dataframe of synapse table data.
    
    Keyword arguments:
    root_id -- root id formatted as listed int
    cleft_thresh -- cleft score threshold to drop synapses as float (default 0.0)
    validate -- boolean option to validate synapse counts (default False)
    """

    # sets client #
    client = CAVEclient("flywire_fafb_production")

    # gets current materialization version #
    mat_vers = max(client.materialize.get_versions())

    # makes dfs of pre- (outgoing) and post- (incoming) synapses #
    outgoing_syn_df = client.materialize.query_table(
        "synapses_nt_v1",
        filter_in_dict={"pre_pt_root_id": root_id},
        materialization_version=mat_vers,
    )
    incoming_syn_df = client.materialize.query_table(
        "synapses_nt_v1",
        filter_in_dict={"post_pt_root_id": root_id},
        materialization_version=mat_vers,
    )

    # removes synapses below cleft threshold, 0-roots, and autapses #
    outgoing_syn_df = outgoing_syn_df[
        outgoing_syn_df["cleft_score"] >= cleft_thresh
    ].reset_index(drop=True)
    outgoing_syn_df = outgoing_syn_df[
        outgoing_syn_df["pre_pt_root_id"] != outgoing_syn_df["post_pt_root_id"]
    ].reset_index(drop=True)
    outgoing_syn_df = outgoing_syn_df[
        outgoing_syn_df["post_pt_root_id"] != 0
    ].reset_index(drop=True)
    incoming_syn_df = incoming_syn_df[
        incoming_syn_df["cleft_score"] >= cleft_thresh
    ].reset_index(drop=True)
    incoming_syn_df = incoming_syn_df[
        incoming_syn_df["pre_pt_root_id"] != incoming_syn_df["post_pt_root_id"]
    ].reset_index(drop=True)
    incoming_syn_df = incoming_syn_df[
        incoming_syn_df["post_pt_root_id"] != 0
    ].reset_index(drop=True)

    # calculates total synapses #
    in_count = len(incoming_syn_df)
    out_count = len(outgoing_syn_df)

    # gets lists of pre and post synaptic partners #
    downstream_partners = list(
        outgoing_syn_df.drop_duplicates(subset="post_pt_root_id")["post_pt_root_id"]
    )
    upstream_partners = list(
        incoming_syn_df.drop_duplicates(subset="pre_pt_root_id")["pre_pt_root_id"]
    )

    # calculates number of upstream and downstream partners #
    up_count = len(upstream_partners)
    down_count = len(downstream_partners)

    # builds output dataframes #
    summary_df = pd.DataFrame(
        {
            "Root ID": root_id,
            "Incoming": in_count,
            "Outgoing": out_count,
            "Upstream Partners": up_count,
            "Downstream Partners": down_count,
        }
    )
    up_df = pd.DataFrame({"Partner ID": upstream_partners})
    down_df = pd.DataFrame({"Partner ID": downstream_partners})

    # adds number of connections between input neuron and partners #
    up_df["Connections"] = [
        list(incoming_syn_df["pre_pt_root_id"]).count(x) for x in upstream_partners
    ]
    down_df["Connections"] = [
        list(outgoing_syn_df["post_pt_root_id"]).count(x) for x in downstream_partners
    ]

    # adds neurotransmitter averages for each partner #
    up_df = up_df.join(
        ntMeans(upstream_partners, incoming_syn_df, "pre_pt_root_id").set_index(
            "Partner ID"
        ),
        on="Partner ID",
    )
    down_df = down_df.join(
        ntMeans(downstream_partners, outgoing_syn_df, "post_pt_root_id").set_index(
            "Partner ID"
        ),
        on="Partner ID",
    )

    # renames partner id columns to up/downstream #
    up_df = up_df.rename(columns={"Partner ID": "Upstream Partner ID"})
    down_df = down_df.rename(columns={"Partner ID": "Downstream Partner ID"})

    # sorts by number of connetions #
    up_df = up_df.astype({"Connections": int}).sort_values(
        by="Connections", ascending=False,
    )
    down_df = down_df.astype({"Connections": int}).sort_values(
        by="Connections", ascending=False,
    )

    # converts all data to strings #
    summary_df = summary_df.astype(str)
    up_df = up_df.astype(str)
    down_df = down_df.astype(str)

    # runs data validation if input variable is set to True #
    if validate:
        val_out = checkValid(up_df, down_df, incoming_syn_df, outgoing_syn_df,)
        return [
            summary_df,
            up_df,
            down_df,
            val_out,
        ]
    else:
        return [
            summary_df,
            up_df,
            down_df,
            "Data not validated",
        ]


def makeViolin(
    root_id, cleft_thresh,
):
    """Build violin plots of up- and downstream neurotransmitter values.
        
        Keyword arguments:
        root_id -- root id formatted as int
        cleft_thresh -- cleft score threshold to drop synapses as float
        """

    # sets client #
    client = CAVEclient("flywire_fafb_production")

    # gets current materialization version #
    mat_vers = max(client.materialize.get_versions())

    # builds dfs using up and down ids, mat vers #
    pre_df = client.materialize.query_table(
        "synapses_nt_v1",
        filter_in_dict={"pre_pt_root_id": [root_id],},
        materialization_version=mat_vers,
    )
    post_df = client.materialize.query_table(
        "synapses_nt_v1",
        filter_in_dict={"post_pt_root_id": [root_id],},
        materialization_version=mat_vers,
    )

    # removes synapses below cleft threshold, 0-roots, and autapses #
    pre_df = pre_df[pre_df["cleft_score"] >= cleft_thresh].reset_index(drop=True)
    pre_df = pre_df[pre_df["pre_pt_root_id"] != pre_df["post_pt_root_id"]].reset_index(
        drop=True
    )
    pre_df = pre_df[pre_df["post_pt_root_id"] != 0].reset_index(drop=True)
    post_df = post_df[post_df["cleft_score"] >= cleft_thresh].reset_index(drop=True)
    post_df = post_df[
        post_df["pre_pt_root_id"] != post_df["post_pt_root_id"]
    ].reset_index(drop=True)
    post_df = post_df[post_df["post_pt_root_id"] != 0].reset_index(drop=True)

    # rounds data to 2 decimal places #
    pre_df = pre_df.round(2)
    post_df = post_df.round(2)

    # creates blank figures #
    pre_fig = go.Figure()
    post_fig = go.Figure()

    # adds line data #
    pre_fig.add_trace(go.Violin(y=list(pre_df["gaba"]), name="Gaba",))
    pre_fig.add_trace(go.Violin(y=list(pre_df["ach"]), name="Ach",))
    pre_fig.add_trace(go.Violin(y=list(pre_df["glut"]), name="Glut",))
    pre_fig.add_trace(go.Violin(y=list(pre_df["oct"]), name="Oct",))
    pre_fig.add_trace(go.Violin(y=list(pre_df["ser"]), name="Ser",))
    pre_fig.add_trace(go.Violin(y=list(pre_df["da"]), name="Da",))
    post_fig.add_trace(go.Violin(y=list(post_df["gaba"]), name="Gaba",))
    post_fig.add_trace(go.Violin(y=list(post_df["ach"]), name="Ach",))
    post_fig.add_trace(go.Violin(y=list(post_df["glut"]), name="Glut",))
    post_fig.add_trace(go.Violin(y=list(post_df["oct"]), name="Oct",))
    post_fig.add_trace(go.Violin(y=list(post_df["ser"]), name="Ser",))
    post_fig.add_trace(go.Violin(y=list(post_df["da"]), name="Da",))

    # hides points #
    pre_fig.update_traces(points=False)
    post_fig.update_traces(points=False)

    # fixes layout to minimize padding and fit both on one line #
    post_fig.update_layout(
        title="Incoming Synapse NT Averages",
        margin={"l": 5, "r": 5, "t": 25, "b": 5,},
        width=400,
        height=200,
    )
    pre_fig.update_layout(
        title="Outgoing Synapse NT Averages",
        margin={"l": 5, "r": 5, "t": 25, "b": 5,},
        width=400,
        height=200,
    )

    return [
        pre_fig,
        post_fig,
    ]


def ntMeans(
    ids, df, col_name,
):
    """Build dataframe of neurotransmitter means for each partner.

    Keyword arguments:
    ids -- list of up- or downstream partner root ids as ints
    df -- dataframe of all up- or downstream synapses for queried neuron
    col_name --  string specifying id lookup column as pre or post
    """

    # makes blank output dataframe #
    out_df = pd.DataFrame()

    # iterates through partner ids #
    for x in ids:

        # filters main df to only include entries for partner #
        partner_df = (df.loc[df[col_name] == x]).reset_index(drop=True)

        # creates row dataframe and fills with nt avgs#
        row_df = pd.DataFrame({"Partner ID": [x]})
        row_df["Gaba Avg"] = [round(partner_df["gaba"].mean(), 3,)]
        row_df["Ach Avg"] = [round(partner_df["ach"].mean(), 3,)]
        row_df["Glut Avg"] = [round(partner_df["glut"].mean(), 3,)]
        row_df["Oct Avg"] = [round(partner_df["oct"].mean(), 3,)]
        row_df["Ser Avg"] = [round(partner_df["ser"].mean(), 3,)]
        row_df["Da Avg"] = [round(partner_df["da"].mean(), 3,)]

        # adds row df to output df #
        out_df = out_df.append(row_df).reset_index(drop=True)

    return out_df


# DASH APP #

# defines blank app object #
app = dash.Dash(__name__)

# defines layout of various app elements #
app.layout = html.Div(
    [
        # defines text area for instructions and feedback#
        dcc.Textarea(
            id="message_text",
            value=(
                'Input root/nuc ID or coordinates and click "Submit" button.\n'
                + "Only one entry at a time.",
            ),
            style={"width": "250px", "resize": "none",},
            rows=3,
            disabled=True,
        ),
        # defines input field#
        html.Div(
            dcc.Input(
                id="input_field", type="text", placeholder="Root/Nuc ID or Coordinates",
            )
        ),
        html.Br(),
        # defines message explaining cleft score field #
        dcc.Textarea(
            id="cleft_message_text",
            value="Cleft score threshold for synapses:",
            style={"width": "260px", "resize": "none",},
            rows=1,
            disabled=True,
        ),
        # defines input field for cleft score threshold #
        html.Div(dcc.Input(id="cleft_thresh_field", type="number", value=50,)),
        html.Br(),
        # defines validation checkbox #
        html.Div(
            dcc.Checklist(
                id="val_check",
                options=[{"label": "Data Validation", "value": True,}],
                labelStyle={"display": "block"},
            )
        ),
        # defines submission button#
        html.Button(
            "Submit",
            id="submit_button",
            n_clicks=0,
            style={"margin-top": "15px", "margin-bottom": "15px",},
        ),
        html.Br(),
        # defines neurotransmitter plot display div #
        html.Div(id="graph_div", children=[], style={"display": "inline-block"},),
        html.Br(),
        # defines link generation button #
        html.Div(
            children=[
                html.Button(
                    "Clear Partner Selections",
                    id="clear_button",
                    n_clicks=0,
                    style={"margin-top": "15px", "margin-bottom": "15px"},
                ),
                html.Button(
                    "Generate NG Link Using Selected Partners",
                    id="link_button",
                    n_clicks=0,
                    style={
                        "margin-top": "15px",
                        "margin-bottom": "15px",
                        "margin-right": "15px",
                        "margin-left": "15px",
                    },
                ),
                dcc.Link(
                    href="",
                    id="ng_link",
                    style={"margin-top": "15px", "margin-bottom": "15px",},
                ),
            ],
            style={"display": "inline-block"},
        ),
        # defines summary table#
        html.Div(
            dash_table.DataTable(
                id="summary_table", fill_width=False, export_format="csv",
            )
        ),
        html.Br(),
        # defines incoming table#
        html.Div(
            dash_table.DataTable(
                id="incoming_table",
                export_format="csv",
                style_table={"height": "180px", "overflowY": "auto",},
                page_action="none",
                fixed_rows={"headers": True},
                style_cell={"width": 160},
            )
        ),
        html.Br(),
        # defines outgoing table#
        html.Div(
            dash_table.DataTable(
                id="outgoing_table",
                export_format="csv",
                style_table={"height": "180px", "overflowY": "auto"},
                page_action="none",
                fixed_rows={"headers": True},
                style_cell={"width": 160},
            )
        ),
    ]
)

# defines callback that generates main tables and violin plots #
@app.callback(
    Output("summary_table", "columns"),
    Output("summary_table", "data"),
    Output("graph_div", "children"),
    Output("incoming_table", "columns"),
    Output("incoming_table", "data"),
    Output("outgoing_table", "columns"),
    Output("outgoing_table", "data"),
    Output("message_text", "value"),
    Input("submit_button", "n_clicks"),
    State("input_field", "value"),
    State("cleft_thresh_field", "value"),
    State("val_check", "value"),
    prevent_initial_call=True,
)
def update_output(n_clicks, query_id, cleft_thresh, val_choice):
    """Create summary and partner tables with violin plots for queried root id.
    
    Keyword arguments:
    n_clicks -- tracks clicks for submit button
    query_id -- root id of queried neuron as int
    cleft_thresh -- float value of cleft score threshold
    val_choice -- boolean option to validate synapse counts
    """

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

        # sets data validation input #
        if val_choice:
            val_in = True
        else:
            val_in = False

        # sets dataframes by passing id/coords into dfBuilder function #
        sum_df, up_df, down_df, val_status = dfBuilder(query_id, cleft_thresh, val_in)

        # creates column lists based on dataframe columns #
        sum_column_list = [{"name": i, "id": i,} for i in sum_df.columns]
        up_column_list = [{"name": i, "id": i,} for i in up_df.columns]
        down_column_list = [{"name": i, "id": i,} for i in down_df.columns]

        # makes dictionaries from dataframes #
        sum_dict = sum_df.to_dict("records")
        up_dict = up_df.to_dict("records")
        down_dict = down_df.to_dict("records")

        # changes message to reflect validation status #
        message_output = val_status

        # sets nt figures using makeViolin #
        out_fig, in_fig = makeViolin(sum_df.loc[0, "Root ID"], cleft_thresh,)

        # builds list of figures to pass to children of graph_div #
        fig_list = [
            html.Div(
                dcc.Graph(id="incoming_figure", figure=in_fig,),
                style={"display": "inline-block"},
            ),
            html.Div(
                dcc.Graph(id="outgoing_figure", figure=out_fig,),
                style={"display": "inline-block",},
            ),
        ]

        # returns list of column names, data values, and message text#
        return [
            sum_column_list,
            sum_dict,
            fig_list,
            up_column_list,
            up_dict,
            down_column_list,
            down_dict,
            message_output,
        ]

    # returns error message if 1-item threshold is exceeded #
    else:
        return [
            0,
            0,
            0,
            0,
            0,
            0,
            "Please limit each query to one entry.",
        ]


# defines callback that generates neuroglancer link #
@app.callback(
    Output("ng_link", "href",),
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
        up_out = up_data[up_id["row"]["Upstream Partner ID"]]
    if down_id is None:
        down_out = 0
    else:
        down_out = down_data[down_id["row"]["Downstream Partner ID"]]

    nuc = query_data[0]["Nucleus Coordinates"][1:-1].split(",")

    out_url = buildLink([query_out], [up_out], [down_out], cleft_thresh, nuc)

    return out_url


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


if __name__ == "__main__":
    app.run_server()

