"""Built-in configuration: XML templates and guest presets."""

from azarovo_hyper.config.presets import PRESETS, preset, preset_names
from azarovo_hyper.config.render import Markup, available_templates, render, xml_escape

__all__ = [
    "PRESETS",
    "Markup",
    "available_templates",
    "preset",
    "preset_names",
    "render",
    "xml_escape",
]
