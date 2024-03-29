from ..common import lookup_utilities
import json
import cloudvolume
import pandas as pd
import numpy as np
from nglui.statebuilder import *


def colorPick(num_of_segs):
    """Generate list of colors in hex spaced evenly around a color wheel.
    
    Keyword arguments:
    num_of_segs -- number of segments to be colored (int)
    """
    # makes blank list to fill with colors #
    colors = []
    # determines increment on 1536-point scale of RGB values #
    # custom scale keeps saturation at 100% and value at 50% #
    increment = int(1536 / num_of_segs)
    # sets default color number to 0 #
    color_number = 0
    # sets color based on quotient and remainder of color number / 256
    for i in range(num_of_segs):
        # sets period of cycle using quotient #
        color_period = color_number // 256
        # sets position in period using remainder #
        changing_value = color_number % 256
        # green rising #
        if color_period == 0:
            r = 255
            g = changing_value
            b = 0
        # red falling #
        elif color_period == 1:
            r = 255 - changing_value
            g = 255
            b = 0
        # blue rising #
        elif color_period == 2:
            r = 0
            g = 255
            b = changing_value
        # green falling #
        elif color_period == 3:
            r = 0
            g = 255 - changing_value
            b = 255
        # red rising #
        elif color_period == 4:
            r = changing_value
            g = 0
            b = 255
        # blue falling #
        elif color_period == 5:
            r = 255
            g = 0
            b = 255 - changing_value

        # converts rgb values to hex strings #
        r, g, b = str(hex(r))[2:], str(hex(g))[2:], str(hex(b))[2:]

        # compensates for python's display of single digit hex values below 16 #
        if len(r) == 1:
            r = "0" + r
        if len(g) == 1:
            g = "0" + g
        if len(b) == 1:
            b = "0" + b

        # sets color by combining rgb hex strings #
        color = "#" + r + g + b
        # appends colors list with current color
        colors.append(color)
        # advances color number ahead by fraction of 1536
        color_number += increment

    return colors


def buildSummaryLink(root_list, nuc_dict, cb=False, config={}):
    """Generate NG link.
    
    Keyword arguments:
    root_list -- root ids (list of ints)
    nuc_list -- x,y,z coords of nuclei in 4,4,40 nm resolution (list of lists of ints)
    cb -- currently-unused option for colorblind-friendliness (bool, default False)
    config -- config settings (dict, default {})
    """

    # generates list of hex colors for segments #
    colors = colorPick(len(root_list))

    # sets client using flywire production datastack #
    client = lookup_utilities.make_client(
        config.get("datastack", None), config.get("server_address", None)
    )

    # sets configuration for EM layer #
    img = ImageLayerConfig(name="Production-image", source=client.info.image_source(),)

    nuc_coords_df = pd.DataFrame(nuc_dict)

    # sets configuration for segmentation layer #
    seg = SegmentationLayerConfig(
        name="Production-segmentation_with_graph",
        source=client.info.segmentation_source(),
        fixed_ids=root_list,
        fixed_id_colors=colors,
        view_kws={"alpha_3d": 0.8},
    )

    # sets point mapping rules #
    points = PointMapper(point_column="pt_position")

    # sets nucleus coordinate annotation config #
    nuc_annos = AnnotationLayerConfig(
        name="Nucleus Coordinates", color="#FF0000", mapping_rules=points,
    )

    # sets view anchor location and zoom level #
    view_options = {
        "position": [29853, 15504, 3539,],
        "zoom_3d": 1000,
    }

    # defines 'sb' by passing in rules for img, seg, and anno layers #
    sb = StateBuilder([img, seg, nuc_annos], view_kws=view_options,)

    # render_state into non-dumped version using json.loads() #
    state_json = json.loads(sb.render_state(nuc_coords_df, return_as="json",))

    # feeds state_json into state uploader to set the value of 'new_id' #
    new_id = client.state.upload_state_json(state_json)

    # defines url using builder, passing in the new_id and the ngl url #
    url = client.state.build_neuroglancer_url(
        state_id=new_id, ngl_url="https://ngl.flywire.ai/",
    )

    return url


def checkFreshness(root_id, config={}):
    """Check to see if root id is outdated.
    
    Keyword arguments:
    root_id -- 18-digit root id (int)
    config -- config settings (dict, default {})
    """
    # sets client #
    client = lookup_utilities.make_client(
        config.get("datastack", None), config.get("server_address", None)
    )

    # returns True if root id is current, False if not #
    return client.chunkedgraph.is_latest_roots(root_id)


def coordsToRoot(coords, config={}):
    """Convert coordinates in 4,4,40 nm resolution to root id.

    Keyword arguments:
    coords -- x,y,z coordinates in 4,4,40 nm resolution (list of str)
    config -- config settings (dict, default {})
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
    root_result = int(client.chunkedgraph.get_root_id(supervoxel_id=point))

    return root_result


def getNuc(root_id, res, config={}):
    """Build a dataframe of nucleus table data in string format.

    Keyword arguments:
    root_id -- root or nucleus id (listed str)
    res -- x,y,z resolution of volume in nm/voxel, e.g. [16,16,40] (list of ints)
    config -- config settings (dict, default {})
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

    # converts nucleus coordinates from nm to 4x4x40 resolution #
    nuc_df["pt_position"] = [nmToRes(i,res) for i in nuc_df["pt_position"]]
    # nuc_df["pt_position"] = [nmToNG(i) for i in nuc_df["pt_position"]] ORIGINAL

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
    # Issue is caused by "resp = requests.get(key)" in "get_file" from "interfaces.py" in "cloud-files" module of "cloud-volume" #
    # if ipv6 is switched on but no ipv6 connection exists, this code will try using ipv6 for ~84s before switching to ipv4 #
    # # sets cloud volume #
    # cv = cloudvolume.CloudVolume(
    #     "graphene://https://prod.flywire-daf.com/segmentation/1.0/fly_v31",
    #     use_https=True,
    # )

    # # determines resolution of volume (important for nucleus coords)#
    # res = cv.resolution

    # return res
    return [16, 16, 40]

def getTypes(root_id, config={}):
    """Query cell type table and return str-format list of unique values.

    Keyword arguments:
    root_id -- root or nucleus id formatted (listed str)
    config -- config settings (dict, default {})
    """

    # sets client using config #
    client = lookup_utilities.make_client(
        config.get("datastack", None), config.get("server_address", None)
    )

    # gets current materialization version #
    mat_vers = max(client.materialize.get_versions())

    # queries cell type table using root id #
    type_df = client.materialize.query_table(
        "neuron_information_v2",
        filter_in_dict={"pt_root_id": [root_id]},
        materialization_version=mat_vers,
    )

    # makes series of uniuqe values and converts to list #
    tags = type_df["tag"].unique().tolist()

    # converts list to string and removes brackets #
    tags = str(tags)[1:-1]

    # handles neurons with no tags #
    if tags == "":
        tags = "n/a"
    else:
        pass

    return tags


def inputToRootList(input_str, config={}):
    """Convert input string into list of int root ids.

    Keyword arguments:
    input_str -- ids or 4,4,40nm coords separated by commas (str)
    config -- config settings (dict, default {})
    """

    # splits input_str into list and strips spaces and brackets #
    input_list = [x.strip() for x in str(input_str).split(",")]
    input_list = [x.strip("[") for x in input_list]
    input_list = [x.strip("]") for x in input_list]

    # if ids are roots #
    if all([len(i) == 18 for i in input_list]):
        root_list = [int(i) for i in input_list]
    
    # if ids are nucs #
    elif all([len(i) == 7 for i in input_list]):
        root_list = [nucToRoot(int(i), config) for i in input_list]
    
    # if id is coordinates #
    elif len(input_list) % 3 == 0:
        root_list = [coordsToRoot(input_list, config)]
    else:
        root_list = input_list

    return root_list


def nmToRes(coords, res):
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

def nmToNG(coords):
    """Convert 1,1,1 nm coordinates to 4,4,40 nm resolution.

    Keyword arguments:
    coords -- x,y,z coordinates in 1,1,1 nm resolution (list of ints)
    """
    coords[0] /= 4
    coords[1] /= 4
    coords[2] /= 40
    coords = [int(i) for i in coords]
    return coords


def nucToRoot(nuc_id, config={}):
    """Convert nucleus id to root id.

    Keyword arguments:
    nuc_id -- 7-digit nucleus id (int)
    """

    # sets client #
    client = lookup_utilities.make_client(
        config.get("datastack", None), config.get("server_address", None)
    )

    # sets materilaization version #
    mat_vers = max(client.materialize.get_versions())

    # queries nucleus table #
    nuc_df = client.materialize.query_table(
        "nuclei_v1", filter_in_dict={"id": [nuc_id]}, materialization_version=mat_vers,
    )

    # sets root id using information from nucleus table #
    root_id = int(nuc_df.loc[0, "pt_root_id"])

    return root_id


def portUrl(input_ids, app_choice, config={}):
    """Convert root ids into outbound url based on app choice.

    Keyword arguments:
    input_ids -- selected 18-digit root ids separated by commas (str)
    app choice -- choice of which app to send the inputs to (str)
    config -- config settings (dict, default {})
    """

    # handles behavior for connectivity app port #
    if app_choice == "connectivity":
        base = config.get("con_app_base_url", None)
        query = "?input_field=" + input_ids + "&cleft_thresh_field=50"
    # handles behavior for graph app port #
    elif app_choice == "graph":
        base = config.get("graph_app_base_url", None)
        query = "?input_field=" + input_ids + "&cleft_thresh_field=50"
    # handles behavior for partner app port #
    elif app_choice == "partner":
        base = config.get("part_app_base_url", None)
        input_list = input_ids.split(",")
        input_a = input_list[0].strip()[1:-1]
        input_b = input_list[1].strip()[1:-1]
        query = "?input_a=" + input_a + "&input_b=" + input_b + "&cleft_thresh_input=50"

    # combines base app address with query string #
    out_url = base + query

    return out_url


def rootListToDataFrame(root_list, config={}):
    """Use root ids to produce output dataframe.

    Keyword arguments:
    root list -- input root ids (list of ints)
    config -- config settings (dict, default {})
    """

    # sets client #
    client = lookup_utilities.make_client(
        config.get("datastack", None), config.get("server_address", None)
    )
    
    # creates blank output dataframe #
    output_df = pd.DataFrame(
        columns=[
            "Root ID",
            "Nuc ID",
            "Nucleus Coordinates",
            "Splits",
            "Merges",
            "Total Edits",
            "Editors",
            "Cell Identification",
            "Current",
        ]
    )
    
    # gets resolution of volume (important for nucleus coordinates)
    res = getResolution()
    
    import time

    # generates df row and adds to output df for each root id #
    for i in root_list:

        # try to form df, otherwise default to bad id behavior #
        try:
            # sets freshness to T/F to check for outdated ids #
            freshness = checkFreshness(i, config)
            
            # tries to make df using changelog #
            try:
                change_df = pd.DataFrame(
                    client.chunkedgraph.get_tabular_change_log(i)[i]
                )
                edits_dict = change_df["is_merge"].value_counts().to_dict()
                if True not in edits_dict:
                    edits_dict[True] = 0
                if False not in edits_dict:
                    edits_dict[False] = 0
                proofreader_list = np.unique(change_df["user_id"])
                proofreaders = ", ".join([str(i) for i in proofreader_list])

            # handles cases with no edits #
            except:
                change_df = pd.DataFrame()
                edits_dict = {True: 0, False: 0}
                proofreaders = "n/a"

            # gets nucleus information #
            row_df = getNuc(i, res, config)

            # handles segments without nuclei #
            if row_df.empty:
                row_df = pd.DataFrame(
                    {"Root ID": i, "Nuc ID": "n/a", "Nucleus Coordinates": "n/a",},
                    index=[0],
                ).astype(str)

            # queries cell type table to get all tags for each id #
            types = getTypes(i, config)

            # builds df columns #
            row_df["Splits"] = str(edits_dict[False])
            row_df["Merges"] = str(edits_dict[True])
            row_df["Total Edits"] = str(len(change_df))
            row_df["Editors"] = proofreaders
            row_df["Cell Identification"] = types
            row_df["Current"] = freshness[0]


        # handles bad ids #
        except:
            row_df = pd.DataFrame(
                {
                    "Root ID": i,
                    "Nuc ID": "BAD ID",
                    "Nucleus Coordinates": "BAD ID",
                    "Splits": "BAD ID",
                    "Merges": "BAD ID",
                    "Total Edits": "BAD ID",
                    "Editors": "BAD ID",
                    "Cell Identification": "BAD ID",
                    "Current": "BAD ID",
                },
                index=[0],
            ).astype(str)

        # adds row to output df for the results of each id #
        output_df = pd.concat([output_df, row_df])    

    return output_df
