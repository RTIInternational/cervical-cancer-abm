import copy
import pytest

from model.parameters import ParameterContainer


class EmptyParameters(ParameterContainer):
    pass


class SimpleParameters(ParameterContainer):
    def __init__(self):
        super().__init__()
        self.add_param("int_param", 1)
        self.add_param("bool_param", True)
        self.add_param("str_param", "value")
        self.add_param("list_param", [0, 1, 2])


simple_dict = {
    "int_param": 1,
    "bool_param": True,
    "str_param": "value",
    "list_param": [0, 1, 2],
}


class NestedParameters(ParameterContainer):
    def __init__(self):
        super().__init__()
        self.add_param("own", 1)
        self.add_param("nested", SimpleParameters())


nested_dict = {"own": 1, "nested": simple_dict}


def test_empty():
    p = EmptyParameters()
    assert p.keys == set()


def test_simple():
    p = SimpleParameters()
    assert p.int_param == 1
    assert p.bool_param is True
    assert p.str_param == "value"
    assert p.list_param == [0, 1, 2]


def test_nested():
    p = NestedParameters()
    assert p.own == 1
    assert p.nested.int_param == 1


def test_update_dict():
    p = NestedParameters()
    p.update_from_dict({"own": 12, "nested": {"str_param": "new"}})
    assert p.own == 12
    assert p.nested.str_param == "new"
    assert p.nested.int_param == 1


def test_request_undefined_param():
    p = NestedParameters()
    with pytest.raises(AttributeError):
        p.bad_param
    with pytest.raises(AttributeError):
        p.nested.bad_param


def test_update_undefined_param():
    p = NestedParameters()
    with pytest.raises(AttributeError):
        p.update_from_dict({"unknown": 0})
    with pytest.raises(AttributeError):
        p.update_from_dict({"nested": {"unknown": 0}})


def test_export_empty_dict():
    p = EmptyParameters()
    expected = {}
    assert p.export_to_dict() == expected


def test_export_dict():
    p = NestedParameters()
    assert p.export_to_dict() == nested_dict


def test_export_modified_dict():
    p = NestedParameters()
    p.own = 12
    p.nested.str_param = "new"

    expected = copy.deepcopy(nested_dict)
    expected["own"] = 12
    expected["nested"]["str_param"] = "new"

    assert p.export_to_dict() == expected
