# Module for reused functions

from caveclient import CAVEclient
import cloudvolume
from functools import lru_cache
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import json
from nglui.statebuilder import *
from annotationframeworkclient import FrameworkClient


def buildLink(
    query_id, up_id, down_id, cleft_thresh, nucleus, cb=False,
):
    """Generate NG link.

    Keyword arguments:
    query_id -- single queried root id as list of int
    up_id -- root ids of upstream partners as list of ints
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
    id_list = query_id + up_id + down_id
    up_cols = [up_color] * len(up_id)
    down_cols = [down_color] * len(down_id)
    color_list = [query_color] + up_cols + down_cols

    # sets Framework client using flywire production datastack #
    client = FrameworkClient("flywire_fafb_production")

    # sets configuration for EM layer #
    img = ImageLayerConfig(client.info.image_source())

    # sets configuration for segmentation layer #
    seg = SegmentationLayerConfig(
        name="seg",
        source=client.info.segmentation_source(),
        fixed_ids=id_list,
        fixed_id_colors=color_list,
        view_kws={"alpha_3d": 0.8},
    )

    # creates dataframe to use for link building and handles single-partner chocies #
    if up_id[0] != 0 and down_id[0] != 0:
        up_df = getSyn(up_id[0], query_id[0], cleft_thresh)[0]
        down_df = getSyn(query_id[0], down_id[0], cleft_thresh)[0]
        syns_df = up_df.append(down_df, ignore_index=True,)
    elif up_id[0] == 0 and down_id[0] != 0:
        syns_df = getSyn(query_id[0], down_id[0], cleft_thresh)[0]
    elif up_id[0] != 0 and down_id[0] == 0:
        syns_df = getSyn(up_id[0], query_id[0], cleft_thresh)[0]
    else:
        return "At least one partner ID must be selected to create a NG link."

    # makes truncated df of pre & post coords #
    coords_df = pd.DataFrame(
        {
            "pre": [nmToNG(x) for x in syns_df["pre_pt_position"]],
            "post": [nmToNG(x) for x in syns_df["post_pt_position"]],
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
    new_id = client.state.upload_state_json(state_json)

    # defines url using builder, passing in the new_id and the ngl url #
    url = client.state.build_neuroglancer_url(
        state_id=new_id, ngl_url="https://ngl.flywire.ai/",
    )

    return url


def coordsToRoot(coords):
    """Convert coordinates in 4,4,40 nm resolution to root id.

    Keyword arguments:
    coords -- list of x,y,z coordinates in 4,4,40 nm resolution
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


def getNuc(root_id):
    """Build a dataframe of nucleus table data in string format.

    Keyword arguments:
    root_id -- root or nucleus id formatted as listed str
    """

    # sets client #
    client = CAVEclient("flywire_fafb_production")

    # gets current materialization version #
    mat_vers = max(client.materialize.get_versions())

    # queries nucleus table using root id #
    nuc_df = client.materialize.query_table(
        "nuclei_v1",
        filter_in_dict={"pt_root_id": [root_id]},
        materialization_version=mat_vers,
    )

    # converts nucleus coordinates from n to 4x4x40 resolution #
    nuc_df["pt_position"] = [nmToNG(i) for i in nuc_df["pt_position"]]

    # creates output df using root, nuc id, and coords to keep aligned #
    out_df = pd.DataFrame(
        {
            "Root ID": list(nuc_df["pt_root_id"]),
            "Nucleus ID": list(nuc_df["id"]),
            "Nucleus Coordinates": list(nuc_df["pt_position"]),
        }
    )

    return out_df.astype(str)


@lru_cache
def getSyn(pre_root=0, post_root=0, cleft_thresh=0.0):
    """Create table of synapses for a given root id.

    Keyword arguments:
    pre_root -- single int-format root id number for upstream neuron (default 0)
    post_root -- single int-format root id number for downstream neuron (default 0)
    cleft_thresh -- float-format cleft score threshold to drop synapses (default 0.0)
    """

    # sets client #
    client = CAVEclient("flywire_fafb_production")

    # gets current materialization version #
    mat_vers = max(client.materialize.get_versions())

    if post_root == 0:
        # creates df that includes neuropil regions using root id #
        syn_df = client.materialize.join_query(
            [["synapses_nt_v1", "id"], ["fly_synapses_neuropil", "id"],],
            filter_in_dict={"synapses_nt_v1": {"pre_pt_root_id": [pre_root]}},
            suffixes=["syn", "nuc"],
            materialization_version=mat_vers,
        )
    elif pre_root == 0:
        # creates df that includes neuropil regions using root id #
        syn_df = client.materialize.join_query(
            [["synapses_nt_v1", "id"], ["fly_synapses_neuropil", "id"],],
            filter_in_dict={"synapses_nt_v1": {"post_pt_root_id": [post_root]}},
            suffixes=["syn", "nuc"],
            materialization_version=mat_vers,
        )
    else:
        # creates df that includes neuropil regions using root id #
        syn_df = client.materialize.join_query(
            [["synapses_nt_v1", "id"], ["fly_synapses_neuropil", "id"],],
            filter_in_dict={
                "synapses_nt_v1": {
                    "pre_pt_root_id": [pre_root],
                    "post_pt_root_id": [post_root],
                }
            },
            suffixes=["syn", "nuc"],
            materialization_version=mat_vers,
        )

    raw_num = len(syn_df)

    # removes synapses below cleft threshold #
    syn_df = syn_df[syn_df["cleft_score"] >= cleft_thresh].reset_index(drop=True)

    cleft_num = len(syn_df)

    # removes autapses #
    syn_df = syn_df[syn_df["pre_pt_root_id"] != syn_df["post_pt_root_id"]].reset_index(
        drop=True
    )

    aut_num = len(syn_df)

    # removes 0-roots #
    syn_df = syn_df[syn_df["pre_pt_root_id"] != 0].reset_index(drop=True)
    syn_df = syn_df[syn_df["post_pt_root_id"] != 0].reset_index(drop=True)

    zeroot_num = len(syn_df)

    output_message = (
        str(raw_num - cleft_num)
        + " subclefts, "
        + str(cleft_num - aut_num)
        + " autapses, and "
        + str(aut_num - zeroot_num)
        + " zero-roots removed for a total of "
        + str(raw_num - zeroot_num)
        + " bad synapses culled. \n"
    )

    if raw_num == 200000:
        output_message = "!Query capped at 200K entires!\n" + output_message

    return [syn_df, output_message]


def idConvert(id_val):
    """Identify id type and convert to root if necessary

    Keyword arguments:
    id -- root id, nuc id, or xyz coords
    """
    # converts coordinates or list-format input into non-listed int
    if type(id_val) == list:
        if len(id_val) == 3:
            id_val = coordsToRoot(id_val)
        else:
            id_val = int(id_val[0])

    elif type(id_val) == str or type(id_val) == float:
        id_val = int(id_val)

    # converts nucleus id to root id #
    if len(str(id_val)) == 7:
        id_val = nucToRoot(id_val)

    return id_val


def makePartnerDataFrame(root_id, cleft_thresh, upstream=False):
    """Make dataframe with summary info.

    Keyword arguments:
    root_id -- 18-digit int-format root id number
    cleft_thresh -- float-format cleft score threshold
    upstream -- Boolean that determines whether df is upstream or downstream (default False)
    """

    # makes df of queried neuron synapses #
    if upstream == True:
        query_df = getSyn(pre_root=0, post_root=root_id, cleft_thresh=cleft_thresh)[0]
        column_name = "pre_pt_root_id"
        title_name = "Upstream Partner ID"
    else:
        query_df = getSyn(pre_root=root_id, post_root=0, cleft_thresh=cleft_thresh)[0]
        column_name = "post_pt_root_id"
        title_name = "Downstream Partner ID"

    # creates array with unique IDs and counts occurrences of each #
    unique_array = np.unique(query_df[column_name], return_counts=True)

    # creates df out of unique_array #
    partner_df = pd.DataFrame(
        {title_name: unique_array[0], "Synapses": unique_array[1]}
    )

    # creates grouped dataframe of each partner means #
    raw_nt_df = query_df.groupby([column_name], as_index=False).mean()

    # drops all nonessential columns #
    nt_df = raw_nt_df.filter(
        [column_name, "gaba", "ach", "glut", "oct", "ser", "da",], axis=1,
    )

    # renames columns #
    nt_df = nt_df.rename(
        {
            column_name: title_name,
            "gaba": "Gaba Avg",
            "ach": "Ach Avg",
            "glut": "Glut Avg",
            "oct": "Oct Avg",
            "ser": "Ser Avg",
            "da": "Da Avg",
        },
        axis=1,
    )

    # rounds NT values to 3 decimal places #
    nt_df = nt_df.round(3)

    # adds neurotransmitter averages for each partner to partner df #
    partner_df = partner_df.join(nt_df.set_index(title_name), on=title_name,)

    # sorts by number of synapses and resets index #
    partner_df = (
        partner_df.astype({"Synapses": int})
        .sort_values(by="Synapses", ascending=False,)
        .reset_index(drop=True)
    )

    # needs to be converted to strings or the dash table will round the IDs #
    return partner_df.astype(str)


def makePie(root_id, cleft_thresh, incoming=False):
    """Create pie chart of relative synapse neuropils.

    Keyword arguments:
    root_id -- single int-format root id number
    cleft_thresh -- float-format cleft score threshold to drop synapses
    incoming -- boolean to specify incoming or outgoing synapses (default False)
    """

    # sets variable for incoming or outgoing synapses
    if incoming == True:
        query_df = getSyn(pre_root=0, post_root=root_id, cleft_thresh=cleft_thresh)[0]
        title_name = "Incoming Synapse Neuropils"
    elif incoming == False:
        query_df = getSyn(pre_root=root_id, post_root=0, cleft_thresh=cleft_thresh)[0]
        title_name = "Outgoing Synapse Neuropils"

    # counts number of synapses to use as denominator in ratios #
    num_syn = len(query_df)

    ratios_df = query_df.groupby(["neuropil"], as_index=False).count()

    # drops all nonessential columns and renames those that remain #
    ratios_df = ratios_df.filter(["neuropil", "id_syn"], axis=1)
    ratios_df = ratios_df.rename({"neuropil": "Neuropil", "id_syn": "Ratio"}, axis=1)

    # divides all counts by total number of synapses to get ratios #
    ratios_df["Ratio"] = ratios_df["Ratio"] / num_syn

    # sorts df from highest to lowest and fixes index #
    ratios_df = ratios_df.sort_values(by=["Ratio"], ascending=False)
    ratios_df.reset_index(inplace=True)
    # region_df = region_df.rename(columns = {'index':'Neuropil'})

    # consolidates all regions less than 1% into 'Other' #
    ratios_df.loc[ratios_df["Ratio"] < 0.01, "Neuropil"] = "Other"

    np_color_dict = {
        # SNP, pink #
        "SLP_L": "ff007f",
        "SLP_R": "ff007f",
        "SIP_L": "ff70b7",
        "SIP_R": "ff70b7",
        "SMP_L": "ff99cb",
        "SMP_R": "ff99cb",
        # LH, magenta #
        "LH_L": "ff00ff",
        "LH_R": "ff00ff",
        # MB, blue-purple #
        "MB_CA_L": "7f00ff",
        "MB_CA_R": "7f00ff",
        # "ACA_L": "9329ff",
        # "ACA_R": "9329ff",
        "MB_PED_L": "a852ff",
        "MB_PED_R": "a852ff",
        # "SPU_L": "b770ff",
        # "SPU_R": "b770ff",
        "MB_VL_L": "c48aff",
        "MB_VL_R": "c48aff",
        "MB_ML_L": "d9b3ff",
        "MB_ML_R": "d9b3ff",
        # AL, blue #
        "AL_L": "0000ff",
        "AL_R": "0000ff",
        # INP, cyan-blue #
        "CRE_L": "007fff",
        "CRE_R": "007fff",
        "SCL_L": "2e95ff",
        "SCL_R": "2e95ff",
        "ICL_L": "61afff",
        "ICL_R": "61afff",
        "IB_L": "80bfff",
        "IB_R": "80bfff",
        "ATL_L": "a8d3ff",
        "ATL_R": "a8d3ff",
        # VLNP, cyan #
        "AOTU_L": "00cccc",
        "AOTU_R": "00cccc",
        "AVLP_L": "00ffff",
        "AVLP_R": "00ffff",
        "PVLP_L": "52ffff",
        "PVLP_R": "52ffff",
        "PLP_L": "269e9e",
        "PLP_R": "269e9e",
        "WED_L": "85ffff",
        "WED_R": "85ffff",
        # OL, blue-green #
        # "LA_L": "00a854",
        # "LA_R": "00a854",
        "ME_L": "00f57a",
        "ME_R": "00f57a",
        "AME_L": "1fff8f",
        "AME_R": "1fff8f",
        "LO_L": "57ffab",
        "LO_R": "57ffab",
        "LOP_L": "85ffc2",
        "LOP_R": "85ffc2",
        # CX, yellow-green #
        "FB": "5ebd00",
        "EB": "7dfa00",
        "PB": "a8fd53",
        "NO": "ccff99",
        # LX, yellow #
        "BU_L": "ffff00",
        "BU_R": "ffff00",
        "LAL_L": "ffff8f",
        "LAL_R": "ffff8f",
        # VMNP, orange-yellow #
        "VES_L": "cc9600",
        "VES_R": "cc9600",
        "EPA_L": "ffbe05",
        "EPA_R": "ffbe05",
        "GOR_L": "ffcf47",
        "GOR_R": "ffcf47",
        "SPS_L": "ffdc7a",
        "SPS_R": "ffdc7a",
        "IPS_L": "ffe7a3",
        "IPS_R": "ffe7a3",
        # PENP, red-orange #
        "AMMC_L": "e04400",
        "AMMC_R": "e04400",
        "FLA_L": "ff590f",
        "FLA_R": "ff590f",
        "CAN_L": "ff8752",
        "CAN_R": "ff8752",
        "PRW": "ffbc9e",
        "SAD": "C1663E",
        # GNG, red #
        "GNG": "ff0000",
        # Other & None, <1% grey & black #
        "Other": "efefef",
        "None": "000000",
    }

    # makes pie chart #
    region_pie = px.pie(
        ratios_df,
        values="Ratio",
        names="Neuropil",
        title=title_name,
        color="Neuropil",
        color_discrete_map=np_color_dict,
    )

    # adds text labels inside pie chart slices #
    region_pie.update_traces(
        textposition="inside", textinfo="label",
    )

    # formats size of chart to match NTs #
    region_pie.update_layout(
        margin={"l": 5, "r": 5, "t": 25, "b": 5,}, width=400, height=200,
    )

    return region_pie


def makeSummaryDataFrame(root_id, cleft_thresh):
    """Make dataframe with summary info.

    Keyword arguments:
    root_id -- 18-digit int-format root id number
    cleft_thresh -- float-format cleft score threshold
    """

    # runs up and downstream queries and returns list with [df,message] #
    up_query = getSyn(pre_root=0, post_root=root_id, cleft_thresh=cleft_thresh)
    down_query = getSyn(pre_root=root_id, post_root=0, cleft_thresh=cleft_thresh)

    # makes df of query nucleus, upstream and downstream synapses #
    nuc_df = getNuc(root_id)
    up_df = up_query[0]
    down_df = down_query[0]

    # exception handling for segments without nuclei #
    if nuc_df.empty:
        nuc_df = pd.DataFrame(
            {"Root ID": root_id, "Nucleus ID": "n/a", "Nucleus Coordinates": "n/a",},
            index=[0],
        ).astype(str)

    # sets output message from up- and downstream messages #
    output_message = (
        "Upstream query results: "
        + up_query[1]
        + "Downstream query results: "
        + down_query[1]
    )

    # calculates total synapses #
    in_count = len(up_df)
    out_count = len(down_df)

    # gets lists of pre and post synaptic partners #
    upstream_partners = list(
        up_df.drop_duplicates(subset="pre_pt_root_id")["pre_pt_root_id"]
    )
    downstream_partners = list(
        down_df.drop_duplicates(subset="post_pt_root_id")["post_pt_root_id"]
    )

    # calculates number of upstream and downstream partners #
    up_count = len(upstream_partners)
    down_count = len(downstream_partners)

    # builds synapse summary df and converts values to strings#
    syn_sum_df = pd.DataFrame(
        {
            "Root ID": root_id,
            "Incoming Synapses": in_count,
            "Outgoing Synapses": out_count,
            "Upstream Partners": up_count,
            "Downstream Partners": down_count,
        },
        index=[0],
    ).astype(str)

    # joins synapse summary df to nucleus df to create full summary df #
    full_sum_df = nuc_df.join(syn_sum_df.set_index("Root ID"), on="Root ID")

    return [full_sum_df, output_message]


def makeViolin(root_id, cleft_thresh, incoming=False):
    """Build violin plots of up- and downstream neurotransmitter values.

    Keyword arguments:
    root_id -- single int-format root id number
    cleft_thresh -- float-format cleft score threshold to drop synapses
    incoming -- boolean to specify incoming or outgoing synapses (default False)
    """

    # sets variable for incoming or outgoing synapses
    if incoming == False:
        query_df = getSyn(pre_root=0, post_root=root_id, cleft_thresh=cleft_thresh)[0]
        title_name = "Outgoing Synapse NT Scores"
    elif incoming == True:
        query_df = getSyn(pre_root=root_id, post_root=0, cleft_thresh=cleft_thresh)[0]
        title_name = "Incoming Synapse NT Scores"

    # rounds data to 2 decimal places #
    query_df = query_df.round(2)

    # creates blank figures #
    fig = go.Figure()

    # adds line data #
    fig.add_trace(go.Violin(y=list(query_df["gaba"]), name="Gaba",))
    fig.add_trace(go.Violin(y=list(query_df["ach"]), name="Ach",))
    fig.add_trace(go.Violin(y=list(query_df["glut"]), name="Glut",))
    fig.add_trace(go.Violin(y=list(query_df["oct"]), name="Oct",))
    fig.add_trace(go.Violin(y=list(query_df["ser"]), name="Ser",))
    fig.add_trace(go.Violin(y=list(query_df["da"]), name="Da",))

    # hides points #
    fig.update_traces(points=False)

    # fixes layout to minimize padding and fit two on one line #
    fig.update_layout(
        title=title_name,
        margin={"l": 5, "r": 5, "t": 25, "b": 5,},
        width=400,
        height=200,
    )

    return fig


def nmToNG(coords):
    """Convert 1,1,1 nm coordinates to 4,4,40 nm resolution.

    Keyword arguments:
    coords -- list of x,y,z coordinates as ints in 1,1,1 nm resolution
    """
    coords[0] /= 4
    coords[1] /= 4
    coords[2] /= 40
    coords = [int(i) for i in coords]
    return coords


def nucToRoot(nuc_id):
    """Convert nucleus id to root id.

    Keyword arguments:
    nuc_id -- 7-digit nucleus id as int
    """
    client = CAVEclient("flywire_fafb_production")
    mat_vers = max(client.materialize.get_versions())
    nuc_df = client.materialize.query_table(
        "nuclei_v1", filter_in_dict={"id": [nuc_id]}, materialization_version=mat_vers,
    )
    root_id = int(nuc_df.loc[0, "pt_root_id"])
    return root_id
