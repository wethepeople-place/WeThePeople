from datetime import date

from jobs.sync_donations import current_fec_cycle


def test_current_fec_cycle_uses_even_year_period():
    assert current_fec_cycle(date(2026, 11, 16)) == "2026"
    assert current_fec_cycle(date(2027, 1, 1)) == "2028"
