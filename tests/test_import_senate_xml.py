from datetime import date

from jobs.import_senate_xml import parse_vote_xml


OFFICIAL_XML = """<?xml version="1.0" encoding="UTF-8"?>
<roll_call_vote>
  <congress>119</congress>
  <session>2</session>
  <congress_year>2026</congress_year>
  <vote_number>270</vote_number>
  <vote_date>November 19, 2026, 03:12 PM</vote_date>
  <vote_question_text>On Passage of the Bill</vote_question_text>
  <vote_result>Passed</vote_result>
  <majority_requirement>1/2</majority_requirement>
  <document>
    <document_congress>119</document_congress>
    <document_type>H.R.</document_type>
    <document_number>2347</document_number>
  </document>
  <count>
    <yeas>62</yeas>
    <nays>33</nays>
    <present>0</present>
    <absent>5</absent>
  </count>
  <members>
    <member>
      <member_full>Doe (R-UT)</member_full>
      <last_name>Doe</last_name>
      <first_name>Jane</first_name>
      <party>R</party>
      <state>UT</state>
      <vote_cast>Yea</vote_cast>
      <lis_member_id>S999</lis_member_id>
    </member>
    <member>
      <member_full>Roe (D-NY)</member_full>
      <last_name>Roe</last_name>
      <first_name>Richard</first_name>
      <party>D</party>
      <state>NY</state>
      <vote_cast>Nay</vote_cast>
      <lis_member_id>S998</lis_member_id>
    </member>
  </members>
</roll_call_vote>
"""


def test_parse_official_senate_vote_xml(tmp_path):
    path = tmp_path / "vote_119_2_00270.xml"
    path.write_text(OFFICIAL_XML, encoding="utf-8")

    record = parse_vote_xml(path)

    assert record["congress"] == 119
    assert record["session"] == 2
    assert record["roll_number"] == 270
    assert record["vote_date"] == date(2026, 11, 19)
    assert record["related_bill_type"] == "HR"
    assert record["related_bill_number"] == 2347
    assert record["yea_count"] == 62
    assert record["nay_count"] == 33
    assert record["not_voting_count"] == 5
    assert record["metadata_json"]["source"] == "senate.gov"
    assert record["voters"][0]["vote_cast"] == "Yea"
    assert record["voters"][1]["state"] == "NY"


def test_rejects_xml_without_member_votes(tmp_path):
    path = tmp_path / "vote_119_2_00001.xml"
    path.write_text(
        OFFICIAL_XML.replace(
            "<members>" + OFFICIAL_XML.split("<members>", 1)[1].split("</members>", 1)[0] + "</members>",
            "<members />",
        ),
        encoding="utf-8",
    )

    try:
        parse_vote_xml(path)
    except ValueError as exc:
        assert "no member vote rows" in str(exc)
    else:
        raise AssertionError("Expected empty official vote XML to be rejected")
