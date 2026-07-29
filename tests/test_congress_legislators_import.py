import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from jobs.import_congress_legislators import bootstrap_tracked_members
from models.database import Base, MemberVote, TrackedMember, Vote


def test_bootstrap_creates_current_member_and_links_vote(tmp_path):
    fixture = [{
        "id": {"bioguide": "A000055"},
        "name": {"official_full": "Robert B. Aderholt"},
        "terms": [{
            "type": "rep",
            "state": "AL",
            "party": "Republican",
        }],
    }]
    (tmp_path / "legislators-current.yaml").write_text(
        yaml.safe_dump(fixture),
        encoding="utf-8",
    )

    engine = create_engine(f"sqlite:///{tmp_path / 'bootstrap.db'}")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        vote = Vote(
            congress=119,
            chamber="house",
            roll_number=74,
            vote_session=2,
            question="On Agreeing to the Resolution",
        )
        session.add(vote)
        session.flush()
        session.add(MemberVote(
            vote_id=vote.id,
            bioguide_id="A000055",
            member_name="Robert Aderholt",
            position="Aye",
        ))
        session.commit()

        assert bootstrap_tracked_members(session, str(tmp_path)) == (1, 0, 1)

        member = session.query(TrackedMember).one()
        assert member.person_id == "robert_b_aderholt"
        assert member.bioguide_id == "A000055"
        assert member.party == "R"
        assert member.chamber == "house"
        assert "congress-legislators" in member.claim_sources_json

        member_vote = session.query(MemberVote).one()
        assert member_vote.person_id == member.person_id

        assert bootstrap_tracked_members(session, str(tmp_path)) == (0, 0, 0)
        assert session.query(TrackedMember).count() == 1
