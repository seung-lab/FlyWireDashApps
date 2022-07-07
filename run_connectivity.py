# Code to run an app locally
from flywiredashapps.connectivity import create_app


minnie_config = {
    "datastack": "minnie65_phase3_v1",
    "server_address": "https://global.daf-apis.com",
    "syn_position_column": "ctr_pt",
    "image_black": 0.35,
    "image_white": 0.7,
    "syn_table": "synapses_pni_2",
    "syn_id_col": "???????",
    "syn_pre_col": "pre_pt_root_id",
    "syn_post_col": "post_pt_root_id",
    "syn_cleft": False,
    # "syn_cleft_col": "",
    "syn_pre_pos_col": "pre_pt_position",
    "syn_post_pos_col": "post_pt_position",
    "syn_nt": False,
    # "syn_nt_cols": [],
    "nuc_table": "nucleus_detection_v0",
    "nuc_id_col": "????????",
    "nuc_root_col": "pt_root_id",
    "nuc_pos_col": "pt_position",
    "neuropils": False,
    # "neuropil_table": "",
    # "neuropil_id_col": "",
}

flywire_config = {
    "datastack": "flywire_fafb_production",
    "server_address": "https://global.daf-apis.com",
    "syn_table": "synapses_nt_v1",
    "syn_id_col": "id",
    "syn_pre_col": "pre_pt_root_id",
    "syn_post_col": "post_pt_root_id",
    "syn_cleft": True,
    "syn_cleft_col": "cleft_score",
    "syn_pre_pos_col": "pre_pt_position",
    "syn_post_pos_col": "pre_pt_position",
    "syn_nt": True,
    "syn_nt_cols": ["gaba", "ach", "glut", "oct", "ser", "da"],
    "nuc_table": "nuclei_v1",
    "nuc_id_col": "id",
    "nuc_root_col": "pt_root_id",
    "nuc_pos_col": "pt_position",
    "con_app_base_url": "https://prod.flywire-daf.com/dash/datastack/flywire_fafb_production/apps/fly_connectivity/",
    "sum_app_base_url": "https://prod.flywire-daf.com/dash/datastack/flywire_fafb_production/apps/fly_summary/",
    "part_app_base_url": "https://prod.flywire-daf.com/dash/datastack/flywire_fafb_production/apps/fly_partners/",
    "neuropils": True,
    "neuropil_table": "fly_synapses_neuropil",
    "neuropil_id_col": "id",
}

fanc_config = {
    "datastack": "fanc_production_mar2021",
    "server_address": "https://global.daf-apis.com",
    "syn_table": "synapses_jan2022",
    "syn_id_col": "???????",
    "syn_pre_col": "pre_pt_root_id",
    "syn_post_col": "post_pt_root_id",
    "syn_cleft": False,
    # "syn_cleft_col": ???,
    "syn_pre_pos_col": "pre_pt_position",
    "syn_post_pos_col": "post_pt_position",
    "syn_nt": False,
    # "syn_nt_cols": [],
    "nuc_table": "soma_jan2022",
    "nuc_id_col": "???????????",
    "nuc_root_col": "pt_root_id",
    "nuc_pos_col": "pt_position",
    "neuropils": False,
    # "neuropil_table": "",
    # "neuropil_id_col": "",
}

if __name__ == "__main__":
    app = create_app(config=flywire_config)
    app.run_server(port=8050)
