import cloudvolume
from functools import lru_cache
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import json
import datetime
import time
import calendar
import datetime
from nglui.statebuilder import *
from ..common import lookup_utilities

def buildAllsynLink(query_id, cleft_thresh, nucleus, config={}, timestamp=None, filter_list=None):
    """Generate neuroglancer link with all synapses associated with queried neuron.

    Keyword arguments:
    query_id -- single queried root id (listed str)
    cleft_thresh -- cleft score threshold to drop synapses (float)
    nucleus -- x,y,z coords of query nucleus (listed str)
    config -- config settings (dict, default {})
    timestamp -- utc timestamp as datetime or unix (str)
    filter_list -- list of root ids to filter results by (str, default None)
    """

    # converts string timestamp to datetime object if present, otherwise sets to current time #
    if timestamp == None:
        timestamp == datetime.datetime.utcnow()
    else:
        timestamp = strToDatetime(timestamp)

    # sets client using flywire production datastack #
    client = lookup_utilities.make_client(
        config.get("datastack", None), config.get("server_address", None)
    )

    # sets configuration for EM layer #
    img = ImageLayerConfig(name="Production-image", source=client.info.image_source(),)

    # sets configuration for segmentation layer #
    seg = SegmentationLayerConfig(
        name="Production-segmentation_with_graph",
        source=client.info.segmentation_source(),
        fixed_ids=query_id,
        fixed_id_colors=["#00ffff"],  # cyan #
        view_kws={"alpha_3d": 0.8},
    )

    # builds nuc coords df using root id list #
    nuc_coords_df = rootsToNucCoords(query_id, config)

    query_id = [int(x) for x in query_id]

    # makes dfs of all synapses for query neuron #
    if filter_list == None:
        up_syns_df = client.materialize.query_table(
            "synapses_nt_v1",
            filter_in_dict={"post_pt_root_id": query_id},
            timestamp=timestamp,
        )
        down_syns_df = client.materialize.query_table(
            "synapses_nt_v1",
            filter_in_dict={"pre_pt_root_id": query_id},
            timestamp=timestamp,
        )
    else:
        up_syns_df = client.materialize.query_table(
            "synapses_nt_v1",
            filter_in_dict={
                "post_pt_root_id": query_id,
                "pre_pt_root_id": filter_list,
            },
            timestamp=timestamp,
        )
        down_syns_df = client.materialize.query_table(
            "synapses_nt_v1",
            filter_in_dict={
                "pre_pt_root_id": query_id,
                "post_pt_root_id": filter_list,
            },
            timestamp=timestamp,
        )

    # sets resolution of volume #
    res = getResolution()

    if len(up_syns_df) > 0:
        # makes truncated df of pre & post coords #
        up_coords_df = pd.DataFrame(
            {
                "pre": [nmToNG(x, res) for x in up_syns_df["pre_pt_position"]],
                "post": [nmToNG(x, res) for x in up_syns_df["post_pt_position"]],
            }
        )
    else:
        up_coords_df = pd.DataFrame()

    if len(down_syns_df) > 0:
        # makes truncated df of pre & post coords #
        down_coords_df = pd.DataFrame(
            {
                "pre": [nmToNG(x, res) for x in down_syns_df["pre_pt_position"]],
                "post": [nmToNG(x, res) for x in down_syns_df["post_pt_position"]],
            }
        )
    else:
        down_coords_df = pd.DataFrame()

    # defines configuration for point & line annotations #
    points = PointMapper(point_column="pt_position")
    lines = LineMapper(point_column_a="pre", point_column_b="post",)

    # defines configuration for annotation layers #
    up_anno = AnnotationLayerConfig(
        name="Incoming Synapses", color="#FF8800", mapping_rules=lines,
    )
    down_anno = AnnotationLayerConfig(
        name="Outgoing Synapses", color="#8800FF", mapping_rules=lines,
    )
    nuc_anno = AnnotationLayerConfig(
        name="Nucleus Coordinates", color="#FF0000", mapping_rules=points,
    )

    # sets view to nucelus of query cell #
    # defaults to center of dataset if no input #
    try:
        view_options = {
            "position": [int(x) for x in nucleus],
            "zoom_3d": 2000,
        }
    except:
        view_options = {
            "position": [119412, 62016, 3539,],
            "zoom_3d": 10000,
        }

    # defines 'sb' by passing in rules for img, seg, and anno layers #
    up_sb = StateBuilder([img, seg, up_anno], view_kws=view_options,)
    down_sb = StateBuilder([down_anno])
    nuc_sb = StateBuilder([nuc_anno])
    chained_sb = ChainedStateBuilder([up_sb, down_sb, nuc_sb])

    # render_state into non-dumped version using json.loads() #
    state_json = json.loads(
        chained_sb.render_state(
            [up_coords_df, down_coords_df, nuc_coords_df], return_as="json",
        )
    )

    # feeds state_json into state uploader to set the value of 'new_id' #
    new_id = client.state.upload_state_json(state_json)

    # defines url using builder, passing in the new_id and the ngl url #
    url = client.state.build_neuroglancer_url(
        state_id=new_id, ngl_url="https://ngl.flywire.ai/",
    )

    return url


def buildLink(
    query_id,
    up_ids,
    down_ids,
    cleft_thresh,
    nucleus,
    cb=False,
    config={},
    timestamp=None,
):
    """Generate NG link.

    Keyword arguments:
    query_id -- single queried root id as list of int
    up_id -- root ids of upstream partners as list of ints
    down_ids -- root ids of downstream partners as list of ints
    cleft_thresh -- cleft score threshold to drop synapses as float
    nucleus -- x,y,z coordinates of query nucleus as list of ints
    cb -- boolean option to make colorblind-friendly (default False)
    config -- dictionary of config settings (default {})
    timestamp -- datetime format utc timestamp
    """

    # checks for currently unused colorblind option, sets color #
    if cb == True:
        up_color = "#ffffff"  # white #
        query_color = "#999999"  # 40% grey #
        down_color = "#323232"  # 80% grey #
    else:
        up_color = "#ffff00"  # yellow #
        query_color = "#ff00ff"  # magenta #
        down_color = "#00ffff"  # cyan #

    # filters out 0 roots
    if up_ids == [0]:
        up_ids = []
    if down_ids == [0]:
        down_ids = []

    # builds id and color lists #
    id_list = query_id + up_ids + down_ids
    up_cols = [up_color] * len(up_ids)
    down_cols = [down_color] * len(down_ids)
    color_list = [query_color] + up_cols + down_cols

    # builds nuc coords df using root id list #
    nuc_coords_df = rootsToNucCoords(id_list, config, timestamp=timestamp,)

    # sets client using flywire production datastack #
    client = lookup_utilities.make_client(
        config.get("datastack", None), config.get("server_address", None)
    )

    # sets configuration for EM layer #
    img = ImageLayerConfig(name="Production-image", source=client.info.image_source(),)

    # sets configuration for segmentation layer #
    seg = SegmentationLayerConfig(
        name="Production-segmentation_with_graph",
        source=client.info.segmentation_source(),
        fixed_ids=id_list,
        fixed_id_colors=color_list,
        view_kws={"alpha_3d": 0.8},
    )

    # creates dataframe to use for link building and handles single-partner choices #
    if up_ids != [] and down_ids != []:
        up_syns_df = pd.DataFrame()
        down_syns_df = pd.DataFrame()
        for x in up_ids:
            row_df = getSyn(
                x,
                query_id[0],
                cleft_thresh,
                datastack_name=config.get("datastack", None),
                server_address=config.get("server_address", None),
                timestamp=timestamp,
            )[0]
            up_syns_df = pd.concat([up_syns_df, row_df], ignore_index=True,)
        for x in down_ids:
            row_df = getSyn(
                query_id[0],
                x,
                cleft_thresh,
                datastack_name=config.get("datastack", None),
                server_address=config.get("server_address", None),
                timestamp=timestamp,
            )[0]
            down_syns_df = pd.concat([down_syns_df, row_df], ignore_index=True,)
    elif up_ids == [] and down_ids != []:
        up_syns_df = pd.DataFrame()
        down_syns_df = pd.DataFrame()
        for x in down_ids:
            row_df = getSyn(
                query_id[0],
                x,
                cleft_thresh,
                datastack_name=config.get("datastack", None),
                server_address=config.get("server_address", None),
                timestamp=timestamp,
            )[0]
            down_syns_df = pd.concat([down_syns_df, row_df], ignore_index=True,)
    elif up_ids != [] and down_ids == []:
        up_syns_df = pd.DataFrame()
        down_syns_df = pd.DataFrame()
        for x in up_ids:
            row_df = getSyn(
                x,
                int(query_id[0]),
                cleft_thresh,
                datastack_name=config.get("datastack", None),
                server_address=config.get("server_address", None),
                timestamp=timestamp,
            )[0]
            up_syns_df = pd.concat([up_syns_df, row_df], ignore_index=True,)
    else:
        up_syns_df = pd.DataFrame()
        down_syns_df = pd.DataFrame()

    # gets volume resolution #
    res = getResolution()

    if len(up_syns_df) > 0:
        # makes truncated df of pre & post coords #
        up_coords_df = pd.DataFrame(
            {
                "pre": [nmToNG(x, res) for x in up_syns_df["pre_pt_position"]],
                "post": [nmToNG(x, res) for x in up_syns_df["post_pt_position"]],
            }
        )
    else:
        up_coords_df = pd.DataFrame()
    if len(down_syns_df) > 0:
        # makes truncated df of pre & post coords #
        down_coords_df = pd.DataFrame(
            {
                "pre": [nmToNG(x, res) for x in down_syns_df["pre_pt_position"]],
                "post": [nmToNG(x, res) for x in down_syns_df["post_pt_position"]],
            }
        )
    else:
        down_coords_df = pd.DataFrame()

    # defines configuration for point & line annotations #
    points = PointMapper(point_column="pt_position")
    lines = LineMapper(point_column_a="pre", point_column_b="post",)

    # defines configuration for annotation layers #
    up_anno = AnnotationLayerConfig(
        name="Incoming Synapses", color="#FF8800", mapping_rules=lines,
    )
    down_anno = AnnotationLayerConfig(
        name="Outgoing Synapses", color="#8800FF", mapping_rules=lines,
    )
    nuc_anno = AnnotationLayerConfig(
        name="Nucleus Coordinates", color="#FF0000", mapping_rules=points,
    )

    # sets view to nucelus of query cell #
    # defaults to center of dataset if no input #
    try:
        view_options = {
            "position": [int(x) for x in nucleus],
            "zoom_3d": 2000,
        }
    except:
        view_options = {
            "position": [119412, 62016, 3539,],
            "zoom_3d": 10000,
        }

    # defines 'sb' by passing in rules for img, seg, and anno layers #
    up_sb = StateBuilder([img, seg, up_anno], view_kws=view_options,)
    down_sb = StateBuilder([down_anno])
    nuc_sb = StateBuilder([nuc_anno])
    chained_sb = ChainedStateBuilder([up_sb, down_sb, nuc_sb])

    # render_state into non-dumped version using json.loads() #
    state_json = json.loads(
        chained_sb.render_state(
            [up_coords_df, down_coords_df, nuc_coords_df], return_as="json",
        )
    )

    # feeds state_json into state uploader to set the value of 'new_id' #
    new_id = client.state.upload_state_json(state_json)

    # defines url using builder, passing in the new_id and the ngl url #
    url = client.state.build_neuroglancer_url(
        state_id=new_id, ngl_url="https://ngl.flywire.ai/",
    )

    return url


def checkFreshness(root_id, config={}, timestamp=None):
    """Check to see if root id is outdated.
    
    Keyword arguments:
    root_id -- 18-digit int-format root id number
    config -- dictionary of config settings (default {})
    timestamp -- datetime format utc timestamp
    """

    # sets client #
    client = lookup_utilities.make_client(
        config.get("datastack", None), config.get("server_address", None),
    )

    # returns True if root id is current, False if not #
    return client.chunkedgraph.is_latest_roots(root_id, timestamp=timestamp,)


def coordsToRoot(coords, config={}, timestamp=None):
    """Convert coordinates in 4,4,40 nm resolution to root id.

    Keyword arguments:
    coords -- list of x,y,z coordinates in 4,4,40 nm resolution
    config -- dictionary of config settings (default {})
    timestamp -- datetime format utc timestamp
    """

    # converts coordinates to ints #
    coords = list(map(int, coords))

    # sets client #
    client = lookup_utilities.make_client(
        config.get("datastack", None), config.get("server_address", None)
    )

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
    root_result = str(
        client.chunkedgraph.get_root_id(supervoxel_id=point, timestamp=timestamp,)
    )

    return root_result


def datetimeToUnix(stamp):
    """Convert datetime object to unix timestamp.
    
    Keyword Arguments:
    stamp -- datetime object timestamp
    """
    return calendar.timegm(stamp.utctimetuple())


def getNuc(root_id, res, config={}, timestamp=None):
    """Build a dataframe of nucleus table data in string format.

    Keyword arguments:
    root_id -- root or nucleus id formatted as int
    config -- dictionary of config settings (default {})
    timestamp -- datetime format utc timestamp (default None)
    """

    # sets client #
    client = lookup_utilities.make_client(
        config.get("datastack", None), config.get("server_address", None)
    )

    # queries nucleus table using root id #
    nuc_df = client.materialize.query_table(
        "nuclei_v1", filter_in_dict={"pt_root_id": [root_id]}, timestamp=timestamp,
    )

    # handles roots with multiple nuclei #
    if len(nuc_df) > 1:
        out_df = pd.DataFrame(
            {
                "Root ID": [root_id],
                "Nuc ID": ["Multiple Nuc Returns"],
                "Nucleus Coordinates": ["Multiple Nuc Returns"],
            }
        )
        return out_df.astype(str)

    # converts nucleus coordinates from n to 4x4x40 resolution #
    nuc_df["pt_position"] = [nmToNG(i, res) for i in nuc_df["pt_position"]]

    # creates output df using root, nuc id, and coords to keep aligned #
    out_df = pd.DataFrame(
        {
            "Root ID": list(nuc_df["pt_root_id"]),
            "Nuc ID": list(nuc_df["id"]),
            "Nucleus Coordinates": list(nuc_df["pt_position"]),
        }
    )

    return out_df.astype(str)


def getResolution():
    # TEMPORARILY DISABLED DUE TO SLOW LOAD TIME #
    # # sets cloud volume #
    # cv = cloudvolume.CloudVolume(
    #     "graphene://https://prod.flywire-daf.com/segmentation/1.0/fly_v31",
    #     use_https=True,
    # )

    # # determines resolution of volume (important for nucleus coords)#
    # res = cv.resolution

    # return res
    return [16, 16, 40]



@lru_cache(maxsize=None)
def getSyn(
    pre_root=0,
    post_root=0,
    cleft_thresh=0.0,
    datastack_name=None,
    server_address=None,
    timestamp=None,
    filter_list=None,
):
    """Create a cached table of synapses for a given root id.

    Keyword arguments:
    pre_root -- single int-format root id number for upstream neuron (default 0)
    post_root -- single int-format root id number for downstream neuron (default 0)
    cleft_thresh -- float-format cleft score threshold to drop synapses (default 0.0)
    datastack_name -- string name of datastack (default None)
    server_address -- string format server address (default None)
    timestamp -- datetime format utc timestamp (default None)
    filter_list -- list of str-format ids to filter results (default None)
    """

    # sets client #
    client = lookup_utilities.make_client(datastack_name, server_address)

    if post_root == 0:

        # TEMPORARILY DISABLED JOIN QUERY #
        # syn_df = client.materialize.join_query(
        #     [["synapses_nt_v1", "id"], ["fly_synapses_neuropil", "id"],],
        #     filter_in_dict={"synapses_nt_v1": {"pre_pt_root_id": [pre_root]}},
        #     suffixes=["syn", "nuc"],
        #     # materialization_version=mat_vers,
        #     timestamp=timestamp,
        # )

        # creates df that includes neuropil regions using root id #
        # optionally fiters query using filter_list #
        # if no filter list, skips this step #
        if filter_list == None:
            raw_syn_df = client.materialize.query_table(
                "synapses_nt_v1",
                filter_in_dict={"pre_pt_root_id": [pre_root]},
                timestamp=timestamp,
            )
        else:
            # performs query with filter tuple #
            raw_syn_df = client.materialize.query_table(
                "synapses_nt_v1",
                filter_in_dict={
                    "pre_pt_root_id": [pre_root],
                    "post_pt_root_id": filter_list,
                },
                timestamp=timestamp,
            )
        np_df = client.materialize.query_table(
            "fly_synapses_neuropil",
            # filters using array of syn ids from raw_syn_df #
            filter_in_dict={"id": np.array(raw_syn_df["id"])},
            timestamp=timestamp,
            merge_reference=False,
        )
        syn_df = pd.merge(
            raw_syn_df,
            np_df,
            left_on="id",
            right_on="target_id",
            how="inner",
            suffixes=["syn", "np"],
        )

    elif pre_root == 0:
        # creates df that includes neuropil regions using root id #
        # TEMPORARILY UNUSED JOIN QUERY #
        # syn_df = client.materialize.join_query(
        #     [["synapses_nt_v1", "id"], ["fly_synapses_neuropil", "id"],],
        #     filter_in_dict={"synapses_nt_v1": {"post_pt_root_id": [post_root]}},
        #     suffixes=["syn", "nuc"],
        #     # materialization_version=mat_vers,
        #     timestamp=timestamp,
        # )
        # optionally fiters query using filter_list #
        if filter_list == None:
            raw_syn_df = client.materialize.query_table(
                "synapses_nt_v1",
                filter_in_dict={"post_pt_root_id": [post_root]},
                timestamp=timestamp,
            )
        else:
            raw_syn_df = client.materialize.query_table(
                "synapses_nt_v1",
                filter_in_dict={
                    "post_pt_root_id": [post_root],
                    "pre_pt_root_id": filter_list,
                },
                timestamp=timestamp,
            )
        np_df = client.materialize.query_table(
            "fly_synapses_neuropil",
            # filters using array of syn ids from raw_syn_df #
            filter_in_dict={"id": np.array(raw_syn_df["id"])},
            timestamp=timestamp,
            merge_reference=False,
        )
        syn_df = pd.merge(
            raw_syn_df,
            np_df,
            left_on="id",
            right_on="target_id",
            how="inner",
            suffixes=["syn", "np"],
        )
    else:
        raw_syn_df = client.materialize.query_table(
            "synapses_nt_v1",
            filter_in_dict={
                "pre_pt_root_id": [int(pre_root)],
                "post_pt_root_id": [int(post_root)],
            },
            timestamp=timestamp,
        )
        np_df = client.materialize.query_table(
            "fly_synapses_neuropil",
            # filters using array of syn ids from raw_syn_df #
            filter_in_dict={"id": np.array(raw_syn_df["id"])},
            timestamp=timestamp,
            merge_reference=False,
        )
        syn_df = pd.merge(
            raw_syn_df,
            np_df,
            left_on="id",
            right_on="target_id",
            how="inner",
            suffixes=["syn", "np"],
        )

    # sets the raw number of synapses equal to the length of the df #
    raw_num = len(syn_df)

    # removes synapses below cleft threshold #
    syn_df = syn_df[syn_df["cleft_score"] >= float(cleft_thresh)].reset_index(drop=True)

    # sets the number of synapses after removing those that fail the cleft score filter #
    cleft_num = len(syn_df)

    # removes autapses #
    syn_df = syn_df[syn_df["pre_pt_root_id"] != syn_df["post_pt_root_id"]].reset_index(
        drop=True
    )

    # sets the number of synapses after removing autapses #
    aut_num = len(syn_df)

    # removes 0-roots #
    syn_df = syn_df[syn_df["pre_pt_root_id"] != 0].reset_index(drop=True)
    syn_df = syn_df[syn_df["post_pt_root_id"] != 0].reset_index(drop=True)

    # sets the number of synapses after removing zero-roots #
    zeroot_num = len(syn_df)

    # constructs output message by calculating how many synapses were removed at each filter step #
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

    # adds message if query was capped by server #
    if raw_num == 200000:
        output_message = "!Query capped at 200K entires!\n" + output_message

    return [syn_df, output_message]


def getSynNoCache(
    pre_root=0,
    post_root=0,
    cleft_thresh=0.0,
    datastack_name=None,
    server_address=None,
    timestamp=None,
    filter_list=None,
):
    """Create an uncached table of synapses for a given root id.

    Keyword arguments:
    pre_root -- single int-format root id number for upstream neuron (default 0)
    post_root -- single int-format root id number for downstream neuron (default 0)
    cleft_thresh -- float-format cleft score threshold to drop synapses (default 0.0)
    datastack_name -- string name of datastack (default None)
    server_address -- string format server address (default None)
    timestamp -- datetime format utc timestamp (default None)
    filter_list -- list of str-format ids to filter results (default None)
    """

    # sets client #
    client = lookup_utilities.make_client(datastack_name, server_address)

    if post_root == 0:
        # creates df that includes neuropil regions using root id #
        # CURRENTLY UNUSED JOIN QUERY #
        # syn_df = client.materialize.join_query(
        #     [["synapses_nt_v1", "id"], ["fly_synapses_neuropil", "id"],],
        #     filter_in_dict={"synapses_nt_v1": {"pre_pt_root_id": [pre_root]}},
        #     suffixes=["syn", "nuc"],
        #     # materialization_version=mat_vers,
        #     timestamp=timestamp,
        # )
        # optionally fiters query using filter_list #
        if filter_list == None:
            raw_syn_df = client.materialize.query_table(
                "synapses_nt_v1",
                filter_in_dict={"pre_pt_root_id": [pre_root]},
                timestamp=timestamp,
            )
        else:
            raw_syn_df = client.materialize.query_table(
                "synapses_nt_v1",
                filter_in_dict={
                    "pre_pt_root_id": [pre_root],
                    "post_pt_root_id": filter_list,
                },
                timestamp=timestamp,
            )

        np_df = client.materialize.query_table(
            "fly_synapses_neuropil",
            # filters using array of syn ids from raw_syn_df #
            filter_in_dict={"id": np.array(raw_syn_df["id"])},
            timestamp=timestamp,
            merge_reference=False,
        )
        syn_df = pd.merge(
            raw_syn_df,
            np_df,
            left_on="id",
            right_on="target_id",
            how="inner",
            suffixes=["syn", "np"],
        )
    elif pre_root == 0:
        # creates df that includes neuropil regions using root id #
        # CURRENTLY UNUSED JOIN QUERY #
        # syn_df = client.materialize.join_query(
        #     [["synapses_nt_v1", "id"], ["fly_synapses_neuropil", "id"],],
        #     filter_in_dict={"synapses_nt_v1": {"post_pt_root_id": [post_root]}},
        #     suffixes=["syn", "nuc"],
        #     # materialization_version=mat_vers,
        #     timestamp=timestamp,
        # )
        if filter_list == None:
            raw_syn_df = client.materialize.query_table(
                "synapses_nt_v1",
                filter_in_dict={"post_pt_root_id": [post_root]},
                timestamp=timestamp,
            )
        else:
            raw_syn_df = client.materialize.query_table(
                "synapses_nt_v1",
                filter_in_dict={
                    "post_pt_root_id": [post_root],
                    "pre_pt_root_id": filter_list,
                },
                timestamp=timestamp,
            )

        np_df = client.materialize.query_table(
            "fly_synapses_neuropil",
            # filters using array of syn ids from raw_syn_df #
            filter_in_dict={"id": np.array(raw_syn_df["id"])},
            timestamp=timestamp,
            merge_reference=False,
        )
        syn_df = pd.merge(
            raw_syn_df,
            np_df,
            left_on="id",
            right_on="target_id",
            how="inner",
            suffixes=["syn", "np"],
        )
    else:
        # creates df that includes neuropil regions using root id #
        # CURRENTLY UNUSED JOIN QUERY #
        # syn_df = client.materialize.join_query(
        #     [["synapses_nt_v1", "id"], ["fly_synapses_neuropil", "id"],],
        #     filter_in_dict={
        #         "synapses_nt_v1": {
        #             "pre_pt_root_id": [pre_root],
        #             "post_pt_root_id": [post_root],
        #         }
        #     },
        #     suffixes=["syn", "nuc"],
        #     # materialization_version=mat_vers,
        #     timestamp=timestamp,
        # )
        raw_syn_df = client.materialize.query_table(
            "synapses_nt_v1",
            filter_in_dict={
                "pre_pt_root_id": [int(pre_root)],
                "post_pt_root_id": [int(post_root)],
            },
            timestamp=timestamp,
        )
        np_df = client.materialize.query_table(
            "fly_synapses_neuropil",
            # filters using array of syn ids from raw_syn_df #
            filter_in_dict={"id": np.array(raw_syn_df["id"])},
            timestamp=timestamp,
            merge_reference=False,
        )
        syn_df = pd.merge(
            raw_syn_df,
            np_df,
            left_on="id",
            right_on="target_id",
            how="inner",
            suffixes=["syn", "np"],
        )

    # sets raw number of synapses by counting length of df #
    raw_num = len(syn_df)

    # removes synapses below cleft threshold #
    syn_df = syn_df[syn_df["cleft_score"] >= float(cleft_thresh)].reset_index(drop=True)

    # sets number of synapses after removing those that fail the cleft score filter #
    cleft_num = len(syn_df)

    # removes autapses #
    syn_df = syn_df[syn_df["pre_pt_root_id"] != syn_df["post_pt_root_id"]].reset_index(
        drop=True
    )

    # sets number of synapses elft after removing autapses #
    aut_num = len(syn_df)

    # removes 0-roots #
    syn_df = syn_df[syn_df["pre_pt_root_id"] != 0].reset_index(drop=True)
    syn_df = syn_df[syn_df["post_pt_root_id"] != 0].reset_index(drop=True)

    # sets number of synapses elft after removing zero-roots #
    zeroot_num = len(syn_df)

    # sets output message by calculating number of synapses removed at each step #
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

    # adds message warning user if query was capped by server #
    if raw_num == 200000:
        output_message = "!Query capped at 200K entires!\n" + output_message

    return [syn_df, output_message]


def getTime():
    """Get current time in datetime.datetime format.
    """
    return datetime.datetime.utcnow().replace(microsecond=0)


def getUnixTime():
    """Get current time in unix format.
    """
    return calendar.timegm(getTime().utctimetuple())


def idConvert(id_val, config, timestamp=None):
    """Identify id type and convert to root if necessary. Return 0 on bad id.

    Keyword arguments:
    id -- root id, nuc id, or xyz coords (str)
    config -- config settings (dict)
    timestamp -- utc timestamp (datetime object, default None)
    """
    # converts coordinates or list-format input into non-listed int
    if type(id_val) == list:
        if len(id_val) == 3:
            id_val = coordsToRoot(id_val, config=config, timestamp=timestamp)
        else:
            id_val = int(id_val[0])

    # converts string and float formatted ids to ints #
    if (type(id_val) == str) or (type(id_val) == float):
        id_val = int(id_val)

    # converts nucleus id to root id #
    if len(str(id_val)) == 7:
        try:
            id_val = nucToRoot(id_val, config=config, timestamp=timestamp)
            if id_val == 0:
                return "invalid nuc id"
        except:
            return "invalid nuc id"

    # returns 0 if the length of the id isn't 18 digits #
    if len(str(id_val)) == 18:
        try:
            # uses freshness checker to test if id is valid or not #
            checkFreshness(id_val, config, timestamp)
            # if id is valid, returns id #
            return id_val
        except:
            # if id isn't valid, returns error #
            return "invalid root id"
    else:
        return 0


def makePartnerDataFrame(
    root_id, cleft_thresh, upstream=False, config={}, timestamp=None, filter_list=None
):
    """Make dataframe with summary info.

    Keyword arguments:
    root_id -- 18-digit int-format root id number
    cleft_thresh -- float-format cleft score threshold
    upstream -- Boolean that determines whether df is upstream or downstream (default False)
    config -- dictionary of config settings (default {})
    timestamp -- datetime format utc timestamp
    filter_list -- str list of root ids to filter results by (default None)
    """

    # makes df of queried neuron synapses #
    if upstream == True:
        query_df = getSyn(
            pre_root=0,
            post_root=root_id,
            cleft_thresh=cleft_thresh,
            datastack_name=config.get("datastack", None),
            server_address=config.get("server_address", None),
            timestamp=timestamp,
            filter_list=filter_list,
        )[0]
        column_name = "pre_pt_root_id"
        title_name = "Upstream Partner ID"
    else:
        query_df = getSyn(
            pre_root=root_id,
            post_root=0,
            cleft_thresh=cleft_thresh,
            datastack_name=config.get("datastack", None),
            server_address=config.get("server_address", None),
            timestamp=timestamp,
            filter_list=filter_list,
        )[0]
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

    # converts root ids into markdown-readable refeeder links #
    partner_df[title_name] = [
        refeedLink(str(x), config) for x in partner_df[title_name]
    ]

    # needs to be converted to strings or the dash table will round the IDs #
    return partner_df.astype(str)


def makePie(
    root_id, cleft_thresh, incoming=False, config={}, timestamp=None, filter_list=None
):
    """Create pie chart of relative synapse neuropils.

    Keyword arguments:
    root_id -- root id number (int)
    cleft_thresh -- cleft score threshold to drop synapses (float)
    incoming -- incoming or outgoing synapses (bool, default False)
    config -- dictionary of config settings (default {})
    timestamp -- utc timestamp (datetime object, default None)
    filter_list -- list of root ids to filter results by (str, default None)
    """

    # sets variable for incoming or outgoing synapses
    if incoming == True:
        query_df = getSyn(
            pre_root=0,
            post_root=root_id,
            cleft_thresh=cleft_thresh,
            datastack_name=config.get("datastack", None),
            server_address=config.get("server_address", None),
            timestamp=timestamp,
            filter_list=filter_list,
        )[0]
        title_name = "Incoming Synapse Neuropils"
    elif incoming == False:
        query_df = getSyn(
            pre_root=root_id,
            post_root=0,
            cleft_thresh=cleft_thresh,
            datastack_name=config.get("datastack", None),
            server_address=config.get("server_address", None),
            timestamp=timestamp,
            filter_list=filter_list,
        )[0]
        title_name = "Outgoing Synapse Neuropils"

    # counts number of synapses to use as denominator in ratios #
    num_syn = len(query_df)

    # make dataframe with counts of each category of neuropil #
    ratios_df = query_df.groupby(["neuropil"], as_index=False).count()

    # drops all nonessential columns and renames those that remain #
    ratios_df = ratios_df.filter(["neuropil", "idsyn"], axis=1)
    ratios_df = ratios_df.rename({"neuropil": "Neuropil", "idsyn": "Ratio"}, axis=1)

    # divides all counts by total number of synapses to get ratios #
    ratios_df["Ratio"] = ratios_df["Ratio"] / num_syn

    # sorts df from highest to lowest and fixes index #
    ratios_df = ratios_df.sort_values(by=["Ratio"], ascending=False)
    ratios_df.reset_index(inplace=True)

    # consolidates all regions less than 1% into 'Other' #
    ratios_df.loc[ratios_df["Ratio"] < 0.01, "Neuropil"] = "Other"

    # renames 'None' as 'Unknown' #
    ratios_df.loc[ratios_df["Neuropil"] == "None", "Neuropil"] = "Unknown"

    # sets color coding for neuropil regions #
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


def makeSummaryDataFrame(
    root_id, cleft_thresh, config={}, timestamp=None, filter_list=None
):
    """Make dataframe with summary info.

    Keyword arguments:
    root_id -- 18-digit root id number (int)
    cleft_thresh -- cleft score threshold (float)
    config -- config settings (dict, default {})
    timestamp -- utc timestamp (datetime object, default None)
    filter_list -- root ids for filtering results (list of str, default None)
    """

    # runs up and downstream queries and returns list with [df,message] #
    up_query = getSyn(
        pre_root=0,
        post_root=root_id,
        cleft_thresh=cleft_thresh,
        datastack_name=config.get("datastack", None),
        server_address=config.get("server_address", None),
        timestamp=timestamp,
        filter_list=filter_list,
    )
    down_query = getSyn(
        pre_root=root_id,
        post_root=0,
        cleft_thresh=cleft_thresh,
        datastack_name=config.get("datastack", None),
        server_address=config.get("server_address", None),
        timestamp=timestamp,
        filter_list=filter_list,
    )

    # sets volume resolution #
    res = getResolution()

    # makes df of query nucleus, upstream and downstream synapses #
    nuc_df = getNuc(root_id, res, config=config, timestamp=timestamp,)
    up_df = up_query[0]
    down_df = down_query[0]

    # exception handling for segments without nuclei #
    if nuc_df.empty:
        nuc_df = pd.DataFrame(
            {"Root ID": root_id, "Nuc ID": "n/a", "Nucleus Coordinates": "n/a",},
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


def makeViolin(
    root_id, cleft_thresh, incoming=False, config={}, timestamp=None, filter_list=None
):
    """Build violin plots of up- and downstream neurotransmitter values.

    Keyword arguments:
    root_id -- root id number (int)
    cleft_thresh -- cleft score threshold to drop synapses (float)
    incoming -- incoming or outgoing synapses (bool, default False)
    config -- config settings (dict, default {})
    timestamp -- utc timestamp (datetime object, default None)
    filter_list -- list of root ids to filter results by (str, default None)
    """

    # sets variable for incoming or outgoing synapses
    if incoming == False:
        query_df = getSyn(
            pre_root=root_id,
            post_root=0,
            cleft_thresh=cleft_thresh,
            datastack_name=config.get("datastack", None),
            server_address=config.get("server_address", None),
            timestamp=timestamp,
            filter_list=filter_list,
        )[0]
        title_name = "Outgoing Synapse NT Scores"
    elif incoming == True:
        query_df = getSyn(
            pre_root=0,
            post_root=root_id,
            cleft_thresh=cleft_thresh,
            datastack_name=config.get("datastack", None),
            server_address=config.get("server_address", None),
            timestamp=timestamp,
            filter_list=filter_list,
        )[0]
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


def markdownToInt(root_list):
    """Convert markdown synatx back into int root ids.
    
    Keyword Arguments:
    root_list -- list of root ids, may be mixed markdown and non-markdown
    """

    # converts markdown back into normal root id #
    output_list = []
    for x in root_list:
        if len(str(x)) > 18:
            output_list.append(int(x[1:19]))
        else:
            output_list.append(int(x))

    return output_list


def nmToNG(coords, res):
    """Convert 1,1,1 nm coordinates to desired resolution.

    Keyword arguments:
    coords -- x,y,z coordinates in 1,1,1 nm resolution (list of ints)
    res -- desired x,y,z resolution in nm/voxel, e.g. 16,16,40 (list of ints)
    """

    # converts coordinates using volume resolution #
    cv_xyz = [
        int(coords[0] / (res[0])),
        int(coords[1] / (res[1])),
        int(coords[2] / (res[2])),
    ]

    return cv_xyz


def nucToRoot(nuc_id, config={}, timestamp=None):
    """Convert nucleus id to root id.

    Keyword arguments:
    nuc_id -- 7-digit nucleus id (int)
    config -- config settings (dict, default {})
    timestamp -- utc timestamp (datetime object, default None)
    """

    # sets client using config #
    client = lookup_utilities.make_client(
        config.get("datastack", None), config.get("server_address", None)
    )

    # mat_vers = max(client.materialize.get_versions())
    nuc_df = client.materialize.query_table(
        "nuclei_v1", filter_in_dict={"id": [nuc_id]}, timestamp=timestamp,
    )

    # if no root id is found, return 0 #
    try:
        root_id = int(nuc_df.loc[0, "pt_root_id"])
    except:
        root_id = 0

    return root_id


def portUrl(input_ids, app_choice, cleft_thresh, config={}, timestamp=None):
    """Convert root ids into outbound url based on app choice.

    Keyword arguments:
    input_ids -- selected 18-digit root ids separated by commas (str)
    app choice -- choice of which app to send the inputs to (str)
    cleft_thresh -- cleft threshold for synapses (str)
    config -- config settings (dict, default {})
    timestamp -- utc timestamp (datetime object, default None)
    """

    # behavior for summary app porting #
    if app_choice == "summary":
        base = config.get("sum_app_base_url", None)
        input_ids = input_ids.replace("'", "").replace(" ", "")
        query = (
            "?input_field="
            + input_ids
            + "&timestamp_field="
            + str(timestamp).replace(" ", "")
        )
    # behavior for partner app porting #
    elif app_choice == "partner":
        base = config.get("part_app_base_url", None)
        input_list = input_ids.split(",")
        input_a = input_list[0].strip()[1:-1]
        input_b = input_list[1].strip()[1:-1]
        query = (
            "?input_a="
            + input_a
            + "&input_b="
            + input_b
            + "&cleft_thresh_input="
            + cleft_thresh
            + "&timestamp_field="
            + str(timestamp).replace(" ", "")
        )

    # constructs url using base address and constructed query string #
    out_url = base + query

    return out_url


def refeedLink(root_id, config={}):
    """Convert root id into markdown-format refeed link.

    Keyword arguments:
    root_id -- 18-digit root id (str)
    config -- config settings (dict, default {})
    """

    # sets base to base url found in config dict #
    base = config.get("con_app_base_url", None)

    # constructs query based on root id #
    query = "?input_field=" + root_id + "&cleft_thresh_field=50"

    # stitches query to base url #
    out_url = base + query

    # adds markdown syntax to turn string into link #
    markdown_url = "[" + root_id + "](" + out_url + ")"

    return markdown_url


def rootsToNucCoords(roots, config={}, timestamp=None):

    """Convert list of root ids to one-column df of nucleus coordinates.
    
    Keyword Arguments:
    roots -- root ids (list of markdown format strings)
    config -- config settings (dict, default {})
    timestamp -- utc timestamp (datetime object, default None)
    """
    # sets client #
    client = lookup_utilities.make_client(
        config.get("datastack", None), config.get("server_address", None)
    )

    # drops 0-roots #
    roots = [int(x) for x in roots if int(x) != 0]

    # queries nucleus table using root id #
    nuc_df = client.materialize.query_table(
        "nuclei_v1", filter_in_dict={"pt_root_id": roots}, timestamp=timestamp,
    )

    #sets volume resolution #
    res = getResolution()

    # converts nucleus coordinates from nm to volume resolution #
    nuc_coords_df = pd.DataFrame(
        {"pt_position": [nmToNG(i, res) for i in nuc_df["pt_position"]]}
    )

    return nuc_coords_df


def strToDatetime(string_timestamp):
    """Convert string timestamp to datetime object.
    
    Keyword Arguments:
    string_timestamp -- timestamp as %Y-%m-%d %H:%M:%S e.g. 2022-07-04 17:43:06 or unix UTC (str)
    """

    # converts if unix #
    if len(string_timestamp) == 10 and string_timestamp.isnumeric():
        out_stamp = unixToDatetime(int(string_timestamp))
    else:
        # converts if datetime #
        try:
            out_stamp = datetime.datetime.strptime(
                string_timestamp, "%Y-%m-%d %H:%M:%S"
            )
        # corrects for removal of space by url helper #
        except:
            try:
                string_timestamp = string_timestamp[0:10] + " " + string_timestamp[10:]
                out_stamp = datetime.datetime.strptime(
                    string_timestamp, "%Y-%m-%d %H:%M:%S"
                )
            # returns None if formatting still incorrect #
            except:
                out_stamp = None

    return out_stamp


def unixToDatetime(stamp):
    """Convert unix timestamp to datetime object.
    
    Keyword Arguments:
    stamp -- unix timestamp
    """
    return datetime.datetime.fromtimestamp(stamp)

