import flask
from caveclient import CAVEclient


def make_client(datastack, server_address):
    """Build a framework client with appropriate auth token.
    
    Keyword Arguments:
    datastack -- Datastack name for client (str)
    server_address -- Global server address for the client (str)
    """
    auth_token = flask.g.get("auth_token", None)
    client = CAVEclient(datastack, server_address=server_address, auth_token=auth_token)
    return client
