import flask
from caveclient import CAVEclient


def make_client(datastack, server_address):
    """Build a framework client with appropriate auth token

    Parameters
    ----------
    datastack : str
        Datastack name for client
    config : dict
        Config dict for settings such as server address.
    server_address : str, optional
        Global server address for the client, by default None. If None, uses the config dict.

    """
    auth_token = flask.g.get("auth_token", None)
    client = CAVEclient(datastack, server_address=server_address, auth_token=auth_token)
    return client
