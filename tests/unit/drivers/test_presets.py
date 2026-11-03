import pytest

from azarovo_hyper import ConfigurationError, VMSpec, preset_names
from azarovo_hyper.config import preset


def test_known_presets_build_valid_specs():
    for name in preset_names():
        VMSpec(name="p", **preset(name))
    assert preset(None) == {}
    assert preset("Ubuntu")["memory"] == "4G"


def test_preset_is_a_copy():
    preset("ubuntu")["memory"] = "1M"
    assert preset("ubuntu")["memory"] == "4G"


def test_unknown_preset():
    with pytest.raises(ConfigurationError, match="known presets"):
        preset("beos")
