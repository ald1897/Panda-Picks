import math
import pytest
from panda_picks.ui.grade_utils import (
    grade_pick,
    resolve_line_for_pick,
    format_line,
    compute_confidence,
    ResultStatus,
)


def test_resolve_line_for_pick_basic_home_and_inversion():
    # Home line present
    assert resolve_line_for_pick('HOME', 'HOME', 'AWAY', -3.5, None) == -3.5
    # Only home line present, away pick inverts
    assert resolve_line_for_pick('AWAY', 'HOME', 'AWAY', -3.5, None) == 3.5
    # Only away line present
    assert resolve_line_for_pick('HOME', 'HOME', 'AWAY', None, +2.0) == -2.0
    assert resolve_line_for_pick('AWAY', 'HOME', 'AWAY', None, +2.0) == 2.0


def test_format_line_pk_and_signed():
    assert format_line(0.0) == 'PK'
    assert format_line(1e-5) == 'PK'
    assert format_line(+3.5) == '+3.5'
    assert format_line(-2.0) == '-2'
    assert format_line(None) == ''


def test_compute_confidence():
    assert compute_confidence(5.0, 10.0) == '50.0%'
    assert compute_confidence(None, 10.0) == 'N/A'
    assert compute_confidence(5.0, 0) == 'N/A'


def test_grade_pick_pending_and_na():
    # Pending (scores missing)
    res = grade_pick('HOME','AWAY','HOME', None, 10, -3.0, None)
    assert res.status == ResultStatus.PENDING
    # NA (no lines)
    res = grade_pick('HOME','AWAY','HOME', 21, 17, None, None)
    assert res.status == ResultStatus.NA


def test_grade_pick_straight_win_loss_push():
    # Win: HOME -3 covers 24-17
    res = grade_pick('HOME','AWAY','HOME', 24, 17, -3.0, None)
    assert res.status == ResultStatus.WIN
    assert math.isclose(res.picked_line, -3.0)
    # Loss: HOME -7 does not cover 24-20
    res = grade_pick('HOME','AWAY','HOME', 24, 20, -7.0, None)
    assert res.status == ResultStatus.LOSS
    # Push: HOME -3 with 20-17 (20-3=17)
    res = grade_pick('HOME','AWAY','HOME', 20, 17, -3.0, None)
    assert res.status == ResultStatus.PUSH


def test_grade_pick_away_side_and_inversion():
    # Only home line given, away pick should invert
    res = grade_pick('HOME','AWAY','AWAY', 21, 20, -3.0, None)
    # Away +3 (inverted) => picked_score 20 +3 =23 vs 21 => WIN
    assert res.status == ResultStatus.WIN
    assert math.isclose(res.picked_line, 3.0)


def test_teaser_adjustment_changes_outcome():
    # Base: HOME -3 results in PUSH (20-17) => teaser +6 => HOME +3 => WIN
    base = grade_pick('HOME','AWAY','HOME', 20, 17, -3.0, None)
    teased = grade_pick('HOME','AWAY','HOME', 20, 17, -3.0, None, line_adjust=6)
    assert base.status == ResultStatus.PUSH
    assert teased.status == ResultStatus.WIN
    assert math.isclose(teased.picked_line, 3.0)


def test_teaser_adjustment_from_loss_to_win():
    # HOME -2 loses 20-21 (20-2=18<21). Teaser +6 => +4: 24>21 win
    base = grade_pick('HOME','AWAY','HOME', 20, 21, -2.0, None)
    teased = grade_pick('HOME','AWAY','HOME', 20, 21, -2.0, None, line_adjust=6)
    assert base.status == ResultStatus.LOSS
    assert teased.status == ResultStatus.WIN
    assert math.isclose(teased.picked_line, 4.0)

