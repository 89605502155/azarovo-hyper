"""Rendering of the embedded XML templates.

Templates use ``$name`` placeholders (:class:`string.Template`). Every value is
XML-escaped unless it is wrapped in :class:`Markup`, which marks an already
rendered fragment. That keeps paths and titles with quotes or ``&`` safe.
"""

from __future__ import annotations

import functools
from collections.abc import Iterable
from importlib.resources import files
from pathlib import Path
from string import Template
from xml.sax.saxutils import escape

from azarovo_hyper.errors import ConfigurationError

_ENTITIES = {"'": "&apos;", '"': "&quot;"}


class Markup(str):
    """A string that is already valid XML and must not be escaped again."""

    __slots__ = ()


def xml_escape(value: object) -> str:
    return escape(str(value), _ENTITIES)


def join(fragments: Iterable[str]) -> Markup:
    """Join rendered fragments, dropping empty ones."""
    return Markup("\n".join(f for f in fragments if f))


@functools.lru_cache(maxsize=64)
def _builtin(name: str) -> Template | None:
    resource = files("azarovo_hyper.config").joinpath("templates", *name.split("/"))
    try:
        return Template(resource.read_text(encoding="utf-8"))
    except (FileNotFoundError, IsADirectoryError, NotADirectoryError):
        return None


def load_template(name: str | Path) -> Template:
    """A built-in template (``"kvm.xml"``, ``"devices/dimm.xml"``) or a file path."""
    if isinstance(name, str) and (builtin := _builtin(name)) is not None:
        return builtin
    path = Path(name).expanduser()
    try:
        return Template(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigurationError(f"unknown template {name!r}: {exc}") from exc


def render(template: str | Path, /, **values: object) -> Markup:
    """Render a template; plain values are escaped, :class:`Markup` is inserted as is."""
    prepared = {
        key: value if isinstance(value, Markup) else xml_escape(value)
        for key, value in values.items()
    }
    try:
        return Markup(load_template(template).substitute(prepared).rstrip("\n"))
    except KeyError as exc:
        raise ConfigurationError(f"template {template} needs a value for {exc}") from exc
    except ValueError as exc:
        raise ConfigurationError(f"template {template} is malformed: {exc}") from exc


def available_templates() -> list[str]:
    root = files("azarovo_hyper.config").joinpath("templates")
    names = [p.name for p in root.iterdir() if p.name.endswith(".xml")]
    names += [f"devices/{p.name}" for p in root.joinpath("devices").iterdir()]
    return sorted(names)
