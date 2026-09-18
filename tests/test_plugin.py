from __future__ import annotations

import copy
import struct
import unittest
import warnings
from typing import TypeVar

import construct as c

from pyflp._events import EventTree, IndexedEvent

from pyflp.plugin import (
    AnyPlugin,
    BooBass,
    FruitKick,
    FruityBalance,
    FruityBloodOverdrive,
    FruityCenter,
    FruityFastDist,
    FruitySend,
    FruitySoftClipper,
    FruityStereoEnhancer,
    Plucked,
    PluginID,
    Soundgoodizer,
    VSTPlugin,
    VSTPluginEvent,
    WrapperPage,
)

from .conftest import get_model

T = TypeVar("T", bound=AnyPlugin)


def get_plugin(preset_file: str, type: type[T]):
    return get_model(f"plugins/{preset_file}", type, PluginID.Data, PluginID.Wrapper)


def test_boobass():
    boobass = get_plugin("boobass.fst", BooBass)
    assert boobass.bass == boobass.mid == boobass.high == 32767


def test_fruit_kick():
    fruit_kick = get_plugin("fruit-kick.fst", FruitKick)
    assert fruit_kick.max_freq == -876
    assert fruit_kick.min_freq == 75
    assert fruit_kick.freq_decay == 163
    assert fruit_kick.amp_decay == 208
    assert fruit_kick.click == 39
    assert fruit_kick.distortion == 62


def test_fruity_balance():
    fruity_balance = get_plugin("fruity-balance.fst", FruityBalance)
    assert fruity_balance.volume == 256
    assert fruity_balance.pan == 0


def test_fruity_blood_overdrive():
    fruity_blood_overdrive = get_plugin("fruity-blood-overdrive.fst", FruityBloodOverdrive)
    assert fruity_blood_overdrive.pre_band == 0
    assert fruity_blood_overdrive.color == 5000
    assert fruity_blood_overdrive.pre_amp == 0
    assert fruity_blood_overdrive.x100 == 0
    assert fruity_blood_overdrive.post_filter == 0


def test_fruity_center():
    fruity_center = get_plugin("fruity-center.fst", FruityCenter)
    assert not fruity_center.enabled


def test_fruity_fast_dist():
    fruity_fast_dist = get_plugin("fruity-fast-dist.fst", FruityFastDist)
    assert fruity_fast_dist.pre == 128
    assert fruity_fast_dist.threshold == 10
    assert fruity_fast_dist.kind == "A"
    assert fruity_fast_dist.mix == 128
    assert fruity_fast_dist.post == 128


def test_fruity_send():
    fruity_send = get_plugin("fruity-send.fst", FruitySend)
    assert fruity_send.dry == 256
    assert fruity_send.send_to == -1
    assert fruity_send.pan == 0
    assert fruity_send.volume == 256


def test_fruity_soft_clipper():
    fruity_soft_clipper = get_plugin("fruity-soft-clipper.fst", FruitySoftClipper)
    assert fruity_soft_clipper.threshold == 100
    assert fruity_soft_clipper.post == 128


def test_fruity_stereo_enhancer():
    fruity_stereo_enhancer = get_plugin("fruity-stereo-enhancer.fst", FruityStereoEnhancer)
    assert fruity_stereo_enhancer.stereo_separation == 0
    assert fruity_stereo_enhancer.effect_position == "post"
    assert fruity_stereo_enhancer.phase_offset == 0
    assert fruity_stereo_enhancer.phase_inversion == "none"
    assert fruity_stereo_enhancer.pan == 0
    assert fruity_stereo_enhancer.volume == 256


def test_plucked():
    plucked = get_plugin("plucked.fst", Plucked)
    assert plucked.decay == 176
    assert plucked.color == 56
    assert plucked.normalize
    assert plucked.gate
    assert not plucked.widen


def test_soundgoodizer():
    soundgoodizer = get_plugin("soundgoodizer.fst", Soundgoodizer)
    assert soundgoodizer.amount == 600
    assert soundgoodizer.mode == "A"


def test_vst_plugin():
    djmfilter = get_plugin("xfer-djmfilter.fst", VSTPlugin)
    assert djmfilter.name == "DJMFilter"
    assert djmfilter.vendor == "Xfer Records"
    assert (
        djmfilter.plugin_path
        == r"C:\Program Files\Common Files\VST2\Xfer Records\DJMFilter_x64.dll"
    )


def test_fruity_wrapper():
    wrapper = get_plugin("fruity-wrapper.fst", VSTPlugin)

    # WrapperEvent properties
    assert not wrapper.compact
    assert not wrapper.demo_mode
    assert not wrapper.detached
    assert not wrapper.directx
    assert not wrapper.disabled
    assert wrapper.generator
    assert wrapper.height == 410
    assert not wrapper.minimized
    assert wrapper.multithreaded
    assert wrapper.page == WrapperPage.Settings
    assert not wrapper.smart_disable
    assert wrapper.visible
    assert wrapper.width == 561

    # VSTPluginEvent properties
    assert wrapper.automation.notify_changes
    assert wrapper.compatibility.buffers_maxsize
    assert wrapper.compatibility.fast_idle
    assert not wrapper.compatibility.fixed_buffers
    assert wrapper.compatibility.process_maximum
    assert wrapper.compatibility.reset_on_transport
    assert wrapper.compatibility.send_loop
    assert not wrapper.compatibility.use_time_offset
    assert wrapper.midi.input == 6
    assert wrapper.midi.output == 9
    assert wrapper.midi.pb_range == 36
    assert not wrapper.midi.send_modx
    assert not wrapper.midi.send_pb
    assert wrapper.midi.send_release
    assert wrapper.processing.allow_sd
    assert not wrapper.processing.bridged
    assert wrapper.processing.keep_state
    assert wrapper.processing.multithreaded
    assert wrapper.processing.notify_render
    assert wrapper.ui.accept_drop
    assert not wrapper.ui.always_update
    assert wrapper.ui.dpi_aware
    assert not wrapper.ui.scale_editor


# Synthetic wrapper payloads avoid distributing third-party plugin state.
def _vst_chunk(id, payload):
    return struct.pack("<IQ", id, len(payload)) + payload


def _vst_model(flags=0, flags2=0, fast_idle=False):
    flag_data = (
        b"opaque123" + struct.pack("<II", flags, flags2) + b"extra" + bytes([fast_idle]) + b"tail"
    )
    midi_data = struct.pack("<iiI", 6, 9, 36) + b"midi-extra"
    raw = struct.pack("<I", 12) + _vst_chunk(2, flag_data) + _vst_chunk(1, midi_data)
    event = VSTPluginEvent(PluginID.Data, raw)
    model = VSTPlugin(EventTree(init=[IndexedEvent(0, event)]))
    return model, event, raw


class VSTPayloadTests(unittest.TestCase):
    def test_known_markers_and_opaque_subevents_round_trip(self):
        for marker in (8, 10, 12):
            raw = (
                struct.pack("<I", marker)
                + _vst_chunk(54, b"Synthetic VST")
                + _vst_chunk(999, b"\xff\x00opaque")
            )
            with self.subTest(marker=marker), warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                event = VSTPluginEvent(PluginID.Data, raw)
                self.assertEqual(event.STRUCT.build(event.value), raw)
                self.assertEqual(event["events"][0]["data"], "Synthetic VST")
                self.assertFalse(caught)

    def test_unknown_full_marker_warns_even_if_low_byte_is_known(self):
        raw = struct.pack("<I", 0x10C)
        with self.assertWarnsRegex(RuntimeWarning, "Unknown marker 268"):
            event = VSTPluginEvent(PluginID.Data, raw)
        self.assertEqual(event.STRUCT.build(event.value), raw)

    def test_truncated_headers_and_subevents_are_rejected(self):
        marker = struct.pack("<I", 12)
        malformed = [
            b"",
            b"\x0c",
            b"\x0c\0",
            b"\x0c\0\0",
            marker + b"\0",
            marker + struct.pack("<I", 54),
            marker + struct.pack("<IQ", 54, 20) + b"short",
            marker + _vst_chunk(54, b"valid") + b"trailing",
        ]
        for raw in malformed:
            with self.subTest(raw=raw), self.assertRaises(c.ConstructError):
                VSTPluginEvent(PluginID.Data, raw)


class VSTPropertyWriteTests(unittest.TestCase):
    def test_flag_setters_preserve_other_bits_and_serialized_fields(self):
        cases = [
            ("compatibility", "fixed_buffers", 0, 1 << 1, False),
            ("compatibility", "buffers_maxsize", 1, 1 << 1, False),
            ("compatibility", "reset_on_transport", 0, 1 << 25, True),
        ]
        for group, prop, word, mask, inverted in cases:
            for enabled in (True, False):
                with self.subTest(prop=prop, enabled=enabled):
                    initial = [0xFFFFFFFF, 0xFFFFFFFF] if not (enabled ^ inverted) else [0, 0]
                    # Include an undocumented bit even when starting disabled.
                    initial[word] |= 1 << 4
                    model, event, raw = _vst_model(*initial)
                    setattr(getattr(model, group), prop, enabled)
                    self.assertIs(getattr(getattr(model, group), prop), enabled)
                    expected = bytearray(raw)
                    offset = 4 + 12 + 9 + word * 4
                    result = initial[word] | mask if enabled ^ inverted else initial[word] & ~mask
                    struct.pack_into("<I", expected, offset, result)
                    self.assertEqual(event.STRUCT.build(event.value), bytes(expected))

    def test_fast_idle_updates_only_its_byte(self):
        for enabled in (True, False):
            model, event, raw = _vst_model(0xABCDEF01, 0xFEDCBA98, not enabled)
            self.assertIs(model.compatibility.fast_idle, not enabled)
            model.compatibility.fast_idle = enabled
            self.assertIs(model.compatibility.fast_idle, enabled)
            expected = bytearray(raw)
            expected[4 + 12 + 22] = enabled
            self.assertEqual(event.STRUCT.build(event.value), bytes(expected))

    def test_midi_field_write_preserves_siblings(self):
        model, event, raw = _vst_model()
        model.midi.input = -1
        self.assertEqual((model.midi.input, model.midi.output, model.midi.pb_range), (-1, 9, 36))
        expected = raw.replace(struct.pack("<iiI", 6, 9, 36), struct.pack("<iiI", -1, 9, 36))
        self.assertEqual(event.STRUCT.build(event.value), expected)

    def test_scalar_subevent_write_still_works(self):
        event = VSTPluginEvent(PluginID.Data, struct.pack("<I", 12) + _vst_chunk(54, b"Old"))
        model = VSTPlugin(EventTree(init=[IndexedEvent(0, event)]))
        model.name = "New"
        self.assertEqual(
            event.STRUCT.build(event.value), struct.pack("<I", 12) + _vst_chunk(54, b"New")
        )

    def test_boolean_properties_reject_non_booleans_without_mutation(self):
        for prop in ("fast_idle", "fixed_buffers"):
            for invalid in (0, 1, None, "yes"):
                model, event, raw = _vst_model()
                with self.subTest(prop=prop, invalid=invalid), self.assertRaises(TypeError):
                    setattr(model.compatibility, prop, invalid)
                self.assertEqual(event.STRUCT.build(event.value), raw)

    def test_absent_subevent_raises_on_write(self):
        event = VSTPluginEvent(PluginID.Data, struct.pack("<I", 12))
        model = VSTPlugin(EventTree(init=[IndexedEvent(0, event)]))
        for prop in ("fast_idle", "fixed_buffers"):
            with self.subTest(prop=prop), self.assertRaises(AttributeError):
                setattr(model.compatibility, prop, True)

    def test_absent_optional_field_raises_without_mutation(self):
        for size, prop in ((9, "fixed_buffers"), (17, "fast_idle")):
            raw = struct.pack("<I", 12) + _vst_chunk(2, bytes(size))
            event = VSTPluginEvent(PluginID.Data, raw)
            model = VSTPlugin(EventTree(init=[IndexedEvent(0, event)]))
            before = copy.deepcopy(event.value)
            with self.subTest(prop=prop), self.assertRaises(AttributeError):
                setattr(model.compatibility, prop, True)
            self.assertEqual(event.value, before)
