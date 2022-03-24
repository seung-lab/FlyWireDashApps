from ..common import lookup_utilities
import cloudvolume
import pandas as pd
import numpy as np


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


def inputToRootList(input_str, config={}):
    """Convert input string into list of int root ids.

    Keyword arguments:
    input_str -- string of ids or 4,4,40nm coords separated by ,
    config -- dictionary of config settings (default {})
    """
    # splits input_str into list and strips spaces #
    input_list = [x.strip(" ") for x in str(input_str).split(",")]
    # if ids are roots #
    if all([len(i) == 18 for i in input_list]):
        root_list = [int(i) for i in input_list]
    # if ids are nucs #
    elif all([len(i) == 7 for i in input_list]):
        root_list = [nucToRoot(int(i), config) for i in input_list]
    # if id is coordinates #
    elif len(input_list) % 3 == 0:
        root_list = [coordsToRoot(input_list, config)]
    return root_list


def coordsToRoot(coords, config={}):
    """Convert coordinates in 4,4,40 nm resolution to root id.

    Keyword arguments:
    coords -- list of x,y,z coordinates in 4,4,40 nm resolution
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


def rootListToDataFrame(root_list, config={}):
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
        ]
    )
    # generates df row and adds to output df for each root id #
    for i in root_list:
        change_df = pd.DataFrame(client.chunkedgraph.get_tabular_change_log(i)[i])
        edits_dict = change_df["is_merge"].value_counts().to_dict()
        if True not in edits_dict:
            edits_dict[True] = 0
        if False not in edits_dict:
            edits_dict[False] = 0
        proofreader_list = np.unique(change_df["user_id"])
        proofreaders = ", ".join([str(i) for i in proofreader_list])

        row_df = getNuc(i, config)

        # handles segments without nuclei #
        if row_df.empty:
            row_df = pd.DataFrame(
                {"Root ID": i, "Nuc ID": "n/a", "Nucleus Coordinates": "n/a",},
                index=[0],
            ).astype(str)

        row_df["Splits"] = str(edits_dict[False])
        row_df["Merges"] = str(edits_dict[True])
        row_df["Total Edits"] = str(len(change_df))
        row_df["Editors"] = proofreaders

        output_df = pd.concat([output_df, row_df])

    return output_df
