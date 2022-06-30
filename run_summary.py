# Code to run an app locally
from flywiredashapps.summary import create_app


minnie_config = {
    # core info #
    "id": "minnie",
    "datastack": "minnie65_phase3_v1",
    "server_address": "https://global.daf-apis.com",
    # synapse table info #
    "syn_table_name": "",
    "out_syn_position_column": "pre_pt_position",
    "in_syn_position_column": "post_pt_position",
    "cleft_column_name": "",
    # nuc table info #
    "nuc_table_name": "",
    # "image_black": 0.35,
    # "image_white": 0.7,
}

flywire_config = {
    # core info #
    "id": "fafb",
    "datastack": "flywire_fafb_production",
    "server_address": "https://global.daf-apis.com",
    # synapse table info #
    "syn_table_name": "synapses_nt_v1",
    "out_syn_position_column": "pre_pt_position",
    "in_syn_position_column": "post_pt_position",
    "cleft_column_name": "",
    # nuc table info #
    "nuc_table_name": "nuclei_v1",
    # app url info #
    "con_app_base_url": "https://prod.flywire-daf.com/dash/datastack/flywire_fafb_production/apps/fly_connectivity/",
    "sum_app_base_url": "https://prod.flywire-daf.com/dash/datastack/flywire_fafb_production/apps/fly_summary/",
    "part_app_base_url": "https://prod.flywire-daf.com/dash/datastack/flywire_fafb_production/apps/fly_partners/",
}

fanc_config = {
    # core info #
    "id": "fanc",
    "datastack": "fanc_production_mar2021",
    "server_address": "https://global.daf-apis.com",
    # synapse table info #
    "syn_table_name": "",
    "out_syn_position_column": "pre_pt_position",
    "in_syn_position_column": "post_pt_position",
    "cleft_column_name": "",
    # nuc table info #
    "nuc_table_name": "",
}

if __name__ == "__main__":
    app = create_app(config=flywire_config)
    app.run_server(port=8050)
