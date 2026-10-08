import argparse

import pytest

from drivegrab.cli import build_parser, parse_size


def test_parse_size():
    assert parse_size("2560x1440") == (2560, 1440)
    with pytest.raises(argparse.ArgumentTypeError):
        parse_size("big")


def test_defaults():
    args = build_parser().parse_args([])
    assert args.urls == []
    assert args.size == (1920, 1080)
    assert args.out == "downloads"
    assert not args.no_zip
