import dataclasses
from typing import get_type_hints

from azarovo_hyper import ResourcePolicy, VMOptions
from azarovo_hyper.domain.spec import spec_fields


def test_options_mirror_spec_and_policy_fields():
    policy = {f.name for f in dataclasses.fields(ResourcePolicy)}
    assert set(get_type_hints(VMOptions)) == set(spec_fields()) | policy
