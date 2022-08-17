from ..common import lookup_utilities
import pandas as pd

# defines function to convert raw connectivity information from dict of dicts to network graph readable format #
def dictToElements(input_data):
    """Convert raw connectivity information into network graph readable format.
    
    Keyword Arguments:
    input_data -- raw connectivity data (dict of dicts where first key is upstream, second key is downstream, value is number of connections e.g. {'id1':{'id2':65,'id3':0},'id2'{'id1':4,'id3':57},'id3'{'id1':0,'id2':5},})
    """
    # makes blank lists to populate with nodes and edges #
    nodes = []
    edges = []

    # for each key in the input dict... #
    for x in list(input_data.keys()):
        # add that key as a node #
        nodes.append({"data": {"id": str(x), "label": str(x)}})
        # for each key in the input dict other than the x key... #
        for y in list(input_data[x].keys()):
            # ...not including edges with 0 connections... #
            if input_data[x][y] != 0:
                # add the source, target, and weight of the connection as an edge #
                edges.append(
                    {
                        "data": {
                            "source": str(x),
                            "target": str(y),
                            "weight": input_data[x][y],
                        }
                    }
                )
            else:
                pass

    # combine the lists to feed into the graph constructor #
    directed_weighted_elements = nodes + edges

    return directed_weighted_elements


def getSynDoD(root_list, cleft_thresh, config={}, timestamp=None):
    """Get number of synapses between each pair of ids, return as dict-of-dicts.
    
    Keyword Arguments:
    root_list -- ids to check (list of strings or ints)
    cleft_thresh -- drop synapses with cleft scores below this value (float)
    timestamp -- utc timestamp (datetime object, default None)
    config -- config settings (dict, default {})
    """

    # converts list items to integers if not already #
    if type(root_list[0]) != int:
        root_list = [int(x) for x in root_list]

    # sets client #
    client = lookup_utilities.make_client(
        config.get("datastack", None), config.get("server_address", None)
    )

    # creates synapse df using root list for pre and post partner ids #
    syn_df = client.materialize.query_table(
        "synapses_nt_v1",
        filter_in_dict={"pre_pt_root_id": root_list, "post_pt_root_id": root_list,},
        timestamp=timestamp,
    )

    # calculates initial number of synapses by counting legth of df #
    raw_num = len(syn_df)

    # removes synapses below cleft threshold #
    syn_df = syn_df[syn_df["cleft_score"] >= float(cleft_thresh)].reset_index(drop=True)

    # counts synapses remaining after filtering out those below cleft score threshold #
    cleft_num = len(syn_df)

    # removes autapses #
    syn_df = syn_df[syn_df["pre_pt_root_id"] != syn_df["post_pt_root_id"]].reset_index(
        drop=True
    )

    # counts synapses remaining after filtering out autapses #
    aut_num = len(syn_df)

    # constructs feedback message using previous counts #
    output_message = (
        str(raw_num - cleft_num)
        + " synapses below threshold and "
        + str(cleft_num - aut_num)
        + " autapses were removed for a total of "
        + str(raw_num - aut_num)
        + " bad synapses culled. \n"
    )

    print(syn_df)

    # creates list of all pre-post pairs as combined strings #
    count_list = [
        str(syn_df.loc[x, "pre_pt_root_id"]) + str(syn_df.loc[x, "post_pt_root_id"])
        for x in syn_df
    ]

    # creates nested dict where first keys are all root IDs (keyXs), all values are dicts #
    # the keys of these dicts are all the root ids (keyYs) except keyX (no self-pairing) #
    # the values for these dicts are the number of times their keyX-keyY pair occurs in count_list #
    outgoing_connections = {
        str(x): {str(y): count_list.count(str(x) + str(y)) for y in root_list if y != x}
        for x in root_list
    }

    return [outgoing_connections, output_message]


def inputToRootList(input_str, config={}, timestamp=None):
    """Convert input string into list of str root ids.

    Keyword arguments:
    input_str -- ids or 4,4,40nm coords separated by commas (str)
    config -- config settings (dict, default {})
    timestamp -- utc timestamp (datetime object, default None)
    """

    # splits input_str into list and strips spaces, brackets, and quotes #
    input_list = [x.strip() for x in str(input_str).split(",")]
    input_list = [x.strip("[") for x in input_list]
    input_list = [x.strip("]") for x in input_list]
    input_list = [x.strip("'") for x in input_list]
    input_list = [x.strip('"') for x in input_list]

    # creates blank lists for output and removed ids #
    root_list = []
    removed_entries = []

    # populates lists based on root/nuc/bad id status
    for i in input_list:
        if len(i) == 18:
            root_list.append(i)
        elif len(i) == 7:
            root_for_nuc = nucToRoot(i, config, timestamp)
            if root_for_nuc != None:
                root_list.append(root_for_nuc)
            else:
                removed_entries.append(i)
        else:
            removed_entries.append(i)

    return [root_list, removed_entries]


def nucToRoot(nuc_id, config={}, timestamp=None):
    """Convert nucleus id to root id.

    Keyword arguments:
    nuc_id -- 7-digit nucleus id (str)
    config -- config settings (dict, default {})
    timestamp -- utc timestamp (datetime object, default None)
    """

    # sets client using config #
    client = lookup_utilities.make_client(
        config.get("datastack", None), config.get("server_address", None)
    )

    # gets nuc info as df using id and timestamp #
    nuc_df = client.materialize.query_table(
        "nuclei_v1", filter_in_dict={"id": [int(nuc_id)]}, timestamp=timestamp,
    )

    # if no root id is found, return None #
    try:
        root_id = str(nuc_df.loc[0, "pt_root_id"])
    except:
        root_id = None

    return root_id
