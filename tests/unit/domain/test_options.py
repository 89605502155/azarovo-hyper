from typing import get_type_hints

from azarovo_hyper import VMOptions
from azarovo_hyper.domain.spec import spec_fields


def test_options_mirror_spec_fields():
    assert set(get_type_hints(VMOptions)) == set(spec_fields())
