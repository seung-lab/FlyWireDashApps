import cloudvolume
from functools import lru_cache
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import json
import time
from nglui.statebuilder import *
from ..common import lookup_utilities


def checkFreshness(root_id, config={}):
    """Check to see if root id is outdated.
    
    Keyword arguments:
    root_id -- 18-digit str-format root id number
    config -- dictionary of config settings (default {})
    """

    # sets client #
    client = lookup_utilities.make_client(
        config.get("datastack", None), config.get("server_address", None)
    )

    # returns True if root id is current, False if not #
    return client.chunkedgraph.is_latest_roots(root_id)


def getStrongest(root_id, syn_thresh, downstream, config={}):
    """Get the strongest connection in a given direction for a given root id.

    Keyword arguments:
    root_id -- single 18-digit str-format root id number
    syn_thresh -- int-format minimum number of synapses
    downstream -- bool denoting if the query is in the downstream direction
    config -- dictionary of config settings (default {})
    """

    # sets client #
    client = lookup_utilities.make_client(
        config.get("datastack", None), config.get("server_address", None)
    )

    # gets current materialization version #
    mat_vers = max(client.materialize.get_versions())

    # queries synapse table using root id and direction#
    if downstream == True:
        syn_df = client.materialize.query_table(
            "synapses_nt_v1",
            filter_in_dict={"pre_pt_root_id": [root_id]},
            materialization_version=mat_vers,
        )
        root_count_var = "post_pt_root_id"
    elif downstream == False:
        # queries synapse table using root id #
        syn_df = client.materialize.query_table(
            "synapses_nt_v1",
            filter_in_dict={"post_pt_root_id": [root_id]},
            materialization_version=mat_vers,
        )
        root_count_var = "pre_pt_root_id"

    # removes synapses below cleft threshold #
    syn_df = syn_df[syn_df["cleft_score"] >= 50].reset_index(drop=True)

    # removes autapses #
    syn_df = syn_df[syn_df["pre_pt_root_id"] != syn_df["post_pt_root_id"]].reset_index(
        drop=True
    )

    # removes 0-roots #
    syn_df = syn_df[syn_df["pre_pt_root_id"] != 0].reset_index(drop=True)
    syn_df = syn_df[syn_df["post_pt_root_id"] != 0].reset_index(drop=True)

    root_mode = syn_df[root_count_var].mode()
    root_count = syn_df[root_count_var].value_counts()[root_mode]

    # print(syn_df.head())
    print(root_mode[0])
    print(root_count[int(root_mode)])
    if root_count > syn_thresh:
        return str(root_mode)
    else:
        return False


def buildChain(root_id, syn_thresh, config={}):
    """Build a chain of all the strongest upstream and downstream connections for a root id.

    Keyword arguments:
    root_id -- single 18-digit str-format root id number
    syn_thresh -- int-format minimum number of synapses
    config -- dictionary of config settings (default {})
    """

    # makes blank lists to fill with id chain #
    upstream_chain = [root_id]
    downstream_chain = [root_id]

    # adds strongest partner until either none above threshold or duplicate is hit #
    while upstream_chain[-1] != False and len(upstream_chain) == len(
        set(upstream_chain)
    ):
        upstream_chain.append(
            getStrongest(upstream_chain[-1], syn_thresh, False, config={})
        )
    while downstream_chain[-1] != False and len(downstream_chain) == len(
        set(downstream_chain)
    ):
        upstream_chain.append(
            getStrongest(downstream_chain[-1], syn_thresh, True, config={})
        )

    # removes last value (always False or duplicate) #
    upstream_chain.pop()
    downstream_chain.pop()

    # reverses upstream chain and removes initial id value #
    upstream_chain.reverse()
    upstream_chain.pop()

    final_list = upstream_chain + downstream_chain

    return final_list

