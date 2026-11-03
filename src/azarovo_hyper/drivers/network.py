"""Network choices: ``"auto"``, ``"user"``, ``"none"``, ``"network:NAME"``, ``"bridge:NAME"``.

A bare name such as ``"default"`` means a libvirt virtual network.
"""

from __future__ import annotations

from dataclasses import dataclass

from azarovo_hyper.config.render import Markup, render, xml_escape
from azarovo_hyper.errors import ConfigurationError

KINDS = ("user", "network", "bridge", "none")


@dataclass(frozen=True, slots=True)
class NetworkChoice:
    kind: str
    source: str | None = None


def parse_network(value: str, auto: str) -> NetworkChoice:
    """Turn the ``network`` option into a :class:`NetworkChoice`."""
    text = (auto if value == "auto" else value).strip()
    if not text:
        raise ConfigurationError("network must not be empty; use 'none' to disable it")
    if text in ("user", "none"):
        return NetworkChoice(text)
    kind, sep, source = text.partition(":")
    if not sep:
        return NetworkChoice("network", text)
    if kind not in ("network", "bridge") or not source:
        raise ConfigurationError(
            f"invalid network {value!r}; use auto, user, none, network:NAME or bridge:NAME"
        )
    return NetworkChoice(kind, source)


def interface_xml(choice: NetworkChoice, model: str | None) -> Markup:
    """The ``<interface>`` element, or an empty fragment for ``none``."""
    if choice.kind == "none":
        return Markup("")
    source = ""
    if choice.source is not None:
        source = f"\n      <source {choice.kind}='{xml_escape(choice.source)}'/>"
    model_xml = f"\n      <model type='{xml_escape(model)}'/>" if model else ""
    return render(
        "devices/interface.xml",
        type="bridge" if choice.kind == "bridge" else choice.kind,
        source=Markup(source),
        model=Markup(model_xml),
    )
