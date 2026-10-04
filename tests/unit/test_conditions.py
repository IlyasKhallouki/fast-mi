"""Unit tests for C3 condition validation and serialisation."""

import json
import tomllib
from types import MappingProxyType

import pytest

from speedrun.conditions import ConditionError, parse_condition, parse_conditions, to_json

VALID = [
    {"var": 123, "eq": 1},
    {"bit": 45, "eq": 0},
    {"room": 33},
    {"owner": 316, "eq": 1},
    {"state": 316, "eq": 1},
    {"has": 316},
    {"var": 9, "eq": -1},
    {"not": {"bit": 45, "eq": 1}},
    {"not": {"not": {"has": 316}}},
]


@pytest.mark.parametrize("cond", VALID, ids=json.dumps)
def test_valid_condition_round_trips(cond):
    out = parse_condition(cond)
    assert out == cond
    assert type(out) is dict


def test_returns_plain_dict_from_any_mapping():
    out = parse_condition(MappingProxyType({"not": MappingProxyType({"room": 3})}))
    assert out == {"not": {"room": 3}}
    assert type(out) is dict and type(out["not"]) is dict


def test_parses_toml_tables():
    data = tomllib.loads('until = [{var = 250, eq = 0}, {not = {has = 316}}]\n')
    assert parse_conditions(data["until"]) == [{"var": 250, "eq": 0}, {"not": {"has": 316}}]


def test_output_is_independent_of_input():
    src = {"not": {"room": 3}}
    out = parse_condition(src)
    out["not"]["room"] = 99
    assert src == {"not": {"room": 3}}


INVALID = [
    {},
    {"var": 1},  # missing eq
    {"eq": 1},
    {"room": 3, "eq": 1},  # room takes no eq
    {"has": 316, "eq": 1},
    {"var": 1, "eq": 1, "extra": 2},  # extra key
    {"bit": 1, "eq": 1, "cite": "x"},
    {"var": 1, "bit": 2},
    {"room": 3, "has": 4},
    {"flag": 1},  # unknown key
    {"var": "1", "eq": 1},  # non-int values
    {"var": 1, "eq": 1.0},
    {"room": None},
    {"room": True},  # bool is not an int here
    {"var": 1, "eq": False},
    {"not": [{"room": 3}]},  # not takes one condition, not a list
    {"not": {"room": 3}, "room": 4},
    {"not": {}},
    {"not": {"not": {"var": 1}}},  # nested error
    {"not": 3},
]


@pytest.mark.parametrize("cond", INVALID, ids=repr)
def test_invalid_condition_rejected(cond):
    with pytest.raises(ConditionError):
        parse_condition(cond)


@pytest.mark.parametrize("bad", [[{"room": 3}], "room", 3, None])
def test_condition_must_be_a_mapping(bad):
    with pytest.raises(ConditionError):
        parse_condition(bad)


def test_condition_error_is_value_error():
    assert issubclass(ConditionError, ValueError)


def test_parse_conditions_conjunction():
    assert parse_conditions([]) == []
    assert parse_conditions(({"room": 1}, {"has": 2})) == [{"room": 1}, {"has": 2}]


@pytest.mark.parametrize("bad", [{"room": 3}, "room", None, 3])
def test_parse_conditions_requires_a_list(bad):
    with pytest.raises(ConditionError):
        parse_conditions(bad)


def test_parse_conditions_reports_bad_index():
    with pytest.raises(ConditionError, match=r"\[1\]"):
        parse_conditions([{"room": 1}, {"room": "x"}])


def test_to_json_is_compact():
    conds = [{"bit": 85, "eq": 1}, {"not": {"has": 316}}]
    assert to_json(conds) == '[{"bit":85,"eq":1},{"not":{"has":316}}]'
    assert to_json([]) == "[]"


def test_to_json_validates():
    with pytest.raises(ConditionError):
        to_json([{"bit": 85}])
