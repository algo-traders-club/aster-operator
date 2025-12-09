"""Utility functions for Aster SDK"""
import time
from urllib.parse import urlencode


def get_timestamp():
    """Get current timestamp in milliseconds"""
    return int(time.time() * 1000)


def cleanNoneValue(d):
    """Remove None values from dictionary"""
    out = {}
    for k in d.keys():
        if d[k] is not None:
            out[k] = d[k]
    return out


def encoded_string(query, special=False):
    """Encode query parameters"""
    if special:
        return urlencode(query, safe='@[]')
    return urlencode(query, True)


def check_required_parameter(value, name):
    """Check if required parameter is provided"""
    if not value:
        raise ValueError(f"Required parameter '{name}' is missing")


def check_required_parameters(params):
    """Check if multiple required parameters are provided"""
    for [param, name] in params:
        if not param and param != 0:
            raise ValueError(f"Required parameter '{name}' is missing")

