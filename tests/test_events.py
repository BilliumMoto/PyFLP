from __future__ import annotations

import pytest

from pyflp._events import AsciiEvent, EventEnum, EventTree, U8Event, WORD
from pyflp.exceptions import EventIDOutOfRange, InvalidEventChunkSize


def test_id_out_of_range():
    with pytest.raises(EventIDOutOfRange, match=str(tuple(range(0, WORD)))):
        U8Event(EventEnum(128), b"\x00")

    with pytest.raises(ValueError):
        AsciiEvent(EventEnum(0), b"1234-decode-me-baby")


def test_event_enum_lookup():
    # EventEnum has no members of its own; Python 3.12+ rejects calling such an
    # enum unless the metaclass resolves the ID itself.
    from pyflp.channel import DisplayGroupID

    assert EventEnum(int(DisplayGroupID.Name)) is DisplayGroupID.Name
    assert DisplayGroupID(int(DisplayGroupID.Name)) is DisplayGroupID.Name

    unknown = EventEnum(255)
    assert unknown is EventEnum(255)
    assert int(unknown) == 255

    for invalid in (256, -1, "1"):
        with pytest.raises(ValueError):
            EventEnum(invalid)


def test_invalid_chunk_size():
    with pytest.raises(InvalidEventChunkSize, match="1"):
        U8Event(EventEnum(0), b"12")


def test_event_tree():
    root = EventTree()
    child = EventTree(root)
    assert child in root.children
    event = U8Event(EventEnum(0), b"\x01")
    child.append(event)
    assert root.first(EventEnum(0)) == event
    child.remove(EventEnum(0))
    assert not root
