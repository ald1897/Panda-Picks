from panda_picks.ui.week_utils import extract_week_number, format_week_standard, week_sort_key


def test_extract_week_number_various_forms():
    assert extract_week_number('WEEK1') == 1
    assert extract_week_number('Week 01') == 1
    assert extract_week_number('wk3') == 3
    assert extract_week_number('3') == 3
    assert extract_week_number('WEEK12') == 12
    assert extract_week_number('PRE') is None
    assert extract_week_number(None) is None


def test_format_week_standard_zero_pad():
    assert format_week_standard('WEEK1') == 'WEEK01'
    assert format_week_standard('wk9') == 'WEEK09'
    assert format_week_standard('10') == 'WEEK10'
    # Unparseable returns original (or empty if None)
    assert format_week_standard('PRE') == 'PRE'
    assert format_week_standard(None) == ''


def test_week_sort_key():
    weeks = ['WEEK2','WEEK10','WEEK1','PRE','WK03','7']
    sorted_weeks = sorted(weeks, key=week_sort_key)
    # 'PRE' has no number so key=0, appears first; then 1,2,3,7,10
    assert sorted_weeks == ['PRE','WEEK1','WEEK2','WK03','7','WEEK10']

