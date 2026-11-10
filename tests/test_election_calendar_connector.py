from datetime import date

from connectors.election_calendar import _parse_missouri_calendar


def test_parses_future_missouri_dates_with_deadlines_and_source():
    html = """
    <table><tr><th>Official Election Day</th><th>Style</th><th>Last Day to Register</th></tr>
    <tr><td>April 6, 2027</td><td>General Municipal Election Day</td><td>March 10, 2027</td></tr>
    <tr><td>August 3, 2026</td><td>Past election</td><td>July 7, 2026</td></tr></table>
    """
    items = _parse_missouri_calendar(html, 2027, date(2026, 11, 11))
    assert len(items) == 1
    assert items[0]["electionDay"] == "2027-04-06"
    assert items[0]["registrationDeadline"] == "2027-03-10"
    assert items[0]["source"]["name"] == "Missouri Secretary of State"
