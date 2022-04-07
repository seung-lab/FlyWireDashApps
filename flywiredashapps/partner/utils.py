from ..common import lookup_utilities
import time
import json
import cloudvolume
import pandas as pd
import numpy as np
from nglui.statebuilder import *
import plotly.express as px
import plotly.graph_objects as go
from functools import lru_cache


def checkFreshness(root_id, config={}):
    """Check to see if root id is outdated.
    
    Keyword arguments:
    root_id -- 18-digit int-format root id number
    config -- dictionary of config settings (default {})
    """
    # sets client #
    client = lookup_utilities.make_client(
        config.get("datastack", None), config.get("server_address", None)
    )

    # returns True if root id is current, False if not #
    return client.chunkedgraph.is_latest_roots(root_id)


def getNuc(root_id, config={}):
    """Build a dataframe of nucleus table data in string format.

    Keyword arguments:
    root_id -- root or nucleus id formatted as listed str
    config -- dictionary of config settings (default {})
    """

    # sets client #
    client = lookup_utilities.make_client(
        config.get("datastack", None), config.get("server_address", None)
    )

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
            "Nuc ID": list(nuc_df["id"]),
            "Nucleus Coordinates": list(nuc_df["pt_position"]),
        }
    )

    return out_df.astype(str)


@lru_cache(maxsize=None)
def getSyn(
    pre_root=0, post_root=0, cleft_thresh=0.0, datastack_name=None, server_address=None
):
    """Create a cached table of synapses for a given root id.

    Keyword arguments:
    pre_root -- single int-format root id number for upstream neuron (default 0)
    post_root -- single int-format root id number for downstream neuron (default 0)
    cleft_thresh -- float-format cleft score threshold to drop synapses (default 0.0)
    """

    # sets client #
    client = lookup_utilities.make_client(datastack_name, server_address)

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
        + " synapses below threshold, "
        + str(cleft_num - aut_num)
        + " autapses, and "
        + str(aut_num - zeroot_num)
        + " synapses on segments with ID '0' were removed for a total of "
        + str(raw_num - zeroot_num)
        + " bad synapses culled. \n"
    )

    if raw_num == 200000:
        output_message = "!Query capped at 200K entires!\n" + output_message

    return [syn_df, output_message]


def makePartnerPie(root_a, root_b, cleft_thresh, config={}):
    """Create pie chart of relative synapse neuropils.

    Keyword arguments:
    root_a -- single int-format root id number for upstream neuron
    root_b -- single int-format root id number for downstream neuron
    cleft_thresh -- float-format cleft score threshold to drop synapses
    config -- dictionary of config settings (default {})
    """

    query_df = getSyn(
        pre_root=root_a,
        post_root=root_b,
        cleft_thresh=cleft_thresh,
        datastack_name=config.get("datastack", None),
        server_address=config.get("server_address", None),
    )[0]
    title_name = str(root_a) + " to " + str(root_b) + " Synapse Neuropils"

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

    # renames 'None' as 'Unknown' #
    ratios_df.loc[ratios_df["Neuropil"] == "None", "Neuropil"] = "Unknown"

    # creates dict of neuropil color codes in hex #
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
        "MB_PED_L": "a852ff",
        "MB_PED_R": "a852ff",
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
        "GA": "a6a600",
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
        # Other & Unknown, <1% grey & black #
        "Other": "efefef",
        "Unknown": "000000",
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


def makePartnerViolin(root_a, root_b, cleft_thresh, config={}):
    """Build violin plots of up- and downstream neurotransmitter values.

    Keyword arguments:
    root_a -- single int-format root id number of upstream neuron
    root_b -- single int-format root id number of downstream neuron
    cleft_thresh -- float-format cleft score threshold to drop synapses
    config -- dictionary of config settings (default {})
    """

    # creates df of synapses using ids #
    query_df = getSyn(
        pre_root=root_a,
        post_root=root_b,
        cleft_thresh=cleft_thresh,
        datastack_name=config.get("datastack", None),
        server_address=config.get("server_address", None),
    )[0]
    title_name = str(root_a) + " to " + str(root_b) + " Synapse NT Scores"

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


def nucToRoot(nuc_id, config={}):
    """Convert nucleus id to root id.

    Keyword arguments:
    nuc_id -- 7-digit nucleus id as int
    """
    client = lookup_utilities.make_client(
        config.get("datastack", None), config.get("server_address", None)
    )
    mat_vers = max(client.materialize.get_versions())
    nuc_df = client.materialize.query_table(
        "nuclei_v1", filter_in_dict={"id": [nuc_id]}, materialization_version=mat_vers,
    )
    root_id = int(nuc_df.loc[0, "pt_root_id"])
    return root_id
