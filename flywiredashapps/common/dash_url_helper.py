# from https://gist.github.com/fzyzcjy/0322eebd54d4889b03e0c3ea9fd9e965
import ast
import re
from typing import Dict, Callable, Any
from urllib.parse import urlparse, parse_qsl, urlencode, quote

import dash
from dash.dependencies import Input, Output, ALL

_COMPONENT_ID_TYPE = "url_helper"

"""
definition: {id_inner: {property: your_value}}
NOTE here we use id_inner, NOT the real id (which is a dict)
"""
State = Dict[str, Dict[str, Any]]


def create_component_kwargs(
    state: State, id_inner: str, **raw_kwargs
) -> Dict[str, Any]:
    # noinspection PyDictCreation
    kwargs = {**raw_kwargs}

    # create "id"
    kwargs["id"] = {
        "type": _COMPONENT_ID_TYPE,
        "id_inner": id_inner,
    }

    # apply default value
    if id_inner in state:
        param_key_dict = state[id_inner]
        kwargs.update(param_key_dict)

    return kwargs


_ID_PARAM_SEP = "::"


def _parse_url_to_state(href: str) -> State:
    # parses url string #
    parse_result = urlparse(href)
    # parses query string into list of [key,value] pairs #
    query_string = parse_qsl(parse_result.query)

    # creates blank dictionary
    state = {}
    # for each listed [key,value] pair #
    for key, value in query_string:
        # if :: is present in the key e.g. x::y #
        if _ID_PARAM_SEP in key:
            # id = x, param = y #
            id, param = key.split(_ID_PARAM_SEP)
        # if :: isn't present in the key #
        else:
            # id = key, param = 'value'
            id, param = key, "value"
        try:
            # A: state.setdefault(id,{}) #
            #     tries to lookup id in state (wouldn't this always fail?), returns blank dict if not present #
            # B. A[param] = ast.literal_eval(value) #
            #     sets value of key=param to value of value variable #
            #     unclear why it uses the ast.literal_eval to do so #
            state.setdefault(id, {})[param] = ast.literal_eval(value)
        except SyntaxError:
            # if the previous returns a syntax error, sets A[param] directly to value #
            state.setdefault(id, {})[param] = value

    # returns {param:value} where param is either a keyword or 'value' #
    return state


def _param_string(id_inner: str, property: str) -> str:
    return id_inner if property == "value" else id_inner + _ID_PARAM_SEP + property


_RE_SINGLE_QUOTED = re.compile("^'|'$")


def _myrepr(o: str) -> str:
    """Optional but chrome URL bar hates "'" """
    # p.s. Pattern.sub(repl, string)
    return _RE_SINGLE_QUOTED.sub('"', repr(o))


def setup(app: dash.Dash, page_layout: Callable[[State], Any]):
    """
    NOTE ref: https://github.com/plotly/dash/issues/188
    """

    @app.callback(
        Output("page-layout", "children"), inputs=[Input("url", "href")],
    )
    def page_load(href: str):
        if not href:
            return []

        state = _parse_url_to_state(href)
        print(f"page_load href={href} state={state}")
        return page_layout(state)

    @app.callback(
        Output("url", "search"),
        # NOTE currently only support property="value"...
        Input({"type": _COMPONENT_ID_TYPE, "id_inner": ALL}, "value"),
        prevent_initial_call=True,
    )
    def update_url_state(values):
        """Updates URL from component values."""

        state = {}

        # https://dash.plotly.com/pattern-matching-callbacks
        inputs = dash.callback_context.inputs_list[0]
        for input in inputs:
            id = input["id"]
            assert isinstance(id, Dict)
            assert id["type"] == _COMPONENT_ID_TYPE
            id_inner = id["id_inner"]
            state[_param_string(id_inner, input["property"])] = _myrepr(input["value"])

        params = urlencode(state, safe="%/:?~#+!$,;'@()*[]\"", quote_via=quote)
        print(f"update_url_state values={values} params={params}")
        return f"?{params}"

