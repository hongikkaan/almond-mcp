"""Expose Holon vocabulary without rewriting saved Rhino identities/history."""
from functools import wraps
import json
import re


def public_key(key):
    return re.sub(r'(^|_)component(s?)(?=_|$)', lambda m: m[1] + 'holon' + m[2], key)


def public_result(value, field=''):
    if isinstance(value, dict):
        return {public_key(key): public_result(item, key) for key, item in value.items()}
    if isinstance(value, list):
        return [public_result(item, field) for item in value]
    # Only generated diagnostics/options are rewritten. User names, goals,
    # reference text and stable ID values must remain byte-for-byte unchanged.
    if isinstance(value, str) and field in {'message', 'next_step', 'next_step_guide', 'available_details'}:
        return re.sub(r'\bcomponent(s)?\b', lambda m: 'holons' if m[1] else 'holon',
                      re.sub(r'\bComponents?\b', lambda m: 'Holons' if m[0].endswith('s') else 'Holon',
                             re.sub(r'\b(?:[a-z]+_)*component(?:s|_ids?|_count)?\b', lambda m: public_key(m[0]), value)))
    return value


def holon_output(function):
    @wraps(function)
    def invoke(*args, **kwargs):
        result = function(*args, **kwargs)
        if isinstance(result, str):
            return json.dumps(public_result(json.loads(result)), ensure_ascii=False)
        return public_result(result)
    return invoke
