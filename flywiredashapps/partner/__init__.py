from dash import Dash
from .callbacks import register_callbacks
from .layout import title, page_layout, app_layout
from ..common.external_stylesheets import external_stylesheets
from ..common.dash_url_helper import setup


def create_app(name=__name__, config={}, **kwargs):
    """Create app using layout and config.
    
    Keyword Arguments:
    name -- name of app (str)
    config -- dictionary of config settings (dict)
    **kwargs -- allows for variable number of keyword arguments
    """
    # sets default stylesheet if none specified #
    if "external_stylesheets" not in kwargs:
        kwargs["external_stylesheets"] = external_stylesheets

    # creates app using name and any kwargs passed #
    app = Dash(name, **kwargs)

    # sets app title attribute, assumes one is passed through **kwargs #
    app.title = title

    # sets app layout attribute #
    app.layout = app_layout

    # adds page layout to app #
    setup(app, page_layout=page_layout)

    # adds callbacks to app #
    register_callbacks(app, config)

    return app
