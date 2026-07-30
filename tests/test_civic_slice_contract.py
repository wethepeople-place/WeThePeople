from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.committee_models import Committee, CommitteeMembership
from models.database import Base, TrackedMember
from routers import politics_committees
from routers.lookup import zip_lookup


def test_committee_membership_and_exact_zip_delegation_contract(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'civic-slice.db'}")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        members = [
            TrackedMember(
                person_id="bill_huizenga",
                bioguide_id="H001058",
                display_name="Bill Huizenga",
                chamber="house",
                state="MI",
                party="R",
                is_active=1,
            ),
            TrackedMember(
                person_id="elissa_slotkin",
                bioguide_id="S001208",
                display_name="Elissa Slotkin",
                chamber="senate",
                state="MI",
                party="D",
                is_active=1,
            ),
            TrackedMember(
                person_id="gary_c_peters",
                bioguide_id="P000595",
                display_name="Gary C. Peters",
                chamber="senate",
                state="MI",
                party="D",
                is_active=1,
            ),
        ]
        session.add_all(members)
        session.add(Committee(
            thomas_id="HSBA",
            name="House Committee on Financial Services",
            chamber="house",
            committee_type="standing",
            url="https://financialservices.house.gov/",
        ))
        session.flush()
        session.add(CommitteeMembership(
            committee_thomas_id="HSBA",
            bioguide_id="H001058",
            person_id="bill_huizenga",
            member_name="Bill Huizenga",
            role="member",
            party="majority",
        ))
        session.commit()

        monkeypatch.setattr(politics_committees, "SessionLocal", Session)
        committee = politics_committees.get_committee_detail("HSBA")
        assert committee["url"] == "https://financialservices.house.gov/"
        assert committee["member_count"] == 1
        assert committee["members"][0]["person_id"] == "bill_huizenga"

        lookup = zip_lookup("49001", db=session)
        assert lookup["state"] == "MI"
        assert {
            (member["person_id"], member["chamber"])
            for member in lookup["representatives"]
        } == {
            ("bill_huizenga", "house"),
            ("elissa_slotkin", "senate"),
            ("gary_c_peters", "senate"),
        }
