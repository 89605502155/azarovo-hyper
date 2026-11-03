import pytest

from azarovo_hyper import ConfigurationError
from azarovo_hyper.config import Markup, available_templates, render, xml_escape


def test_escaping_and_markup():
    assert xml_escape("a<b>&'\"") == "a&lt;b&gt;&amp;&apos;&quot;"
    out = render("devices/snapshot.xml", name="<s>", description=Markup("<b/>"))
    assert "<name>&lt;s&gt;</name>" in out
    assert "<description><b/></description>" in out
    assert isinstance(out, Markup)


def test_missing_value_and_unknown_template(tmp_path):
    with pytest.raises(ConfigurationError, match="needs a value"):
        render("devices/dimm.xml")
    with pytest.raises(ConfigurationError, match="unknown template"):
        render("devices/nope.xml")
    bad = tmp_path / "bad.xml"
    bad.write_text("$")
    with pytest.raises(ConfigurationError, match="malformed"):
        render(bad)


def test_templates_are_packaged():
    names = available_templates()
    assert {"kvm.xml", "xen.xml", "devices/dimm.xml", "devices/spice.xml"} <= set(names)
