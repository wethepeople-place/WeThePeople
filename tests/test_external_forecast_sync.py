from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from jobs.sync_external_forecasts import run
from models.database import Base
from models.forecast_models import ExternalForecastAudit, ExternalForecastMarket


class Response:
    def raise_for_status(self): pass
    def json(self):
        return [{"id": "event-1", "slug": "example-election", "markets": [{
            "id": "market-1", "slug": "candidate-wins", "question": "Will Candidate A win?",
            "description": "This market will resolve to Yes if Candidate A wins the election, according to the official certified result.",
            "outcomes": '["Yes", "No"]', "outcomePrices": '["0.61", "0.39"]',
            "endDate": "2027-01-01T00:00:00Z", "active": True, "closed": False,
            "acceptingOrders": True, "volumeNum": 5000, "liquidityNum": 2000,
        }] }]


class Transport:
    @staticmethod
    def get(*args, **kwargs): return Response()


def test_automatic_import_publishes_and_audits_qualifying_market():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as db:
        result = run(db, transport=Transport, now=datetime(2026, 8, 30, tzinfo=timezone.utc))
        assert result == {"observed": 1, "published": 1, "quarantined": 0, "closed": 0}
        row = db.query(ExternalForecastMarket).one()
        assert row.quality_status == "published" and row.implied_probabilities_json == [0.61, 0.39]
        assert db.query(ExternalForecastAudit).one().action == "imported"
        run(db, transport=Transport, now=datetime(2026, 8, 30, 0, 5, tzinfo=timezone.utc))
        assert db.query(ExternalForecastAudit).count() == 1


def test_quality_bot_quarantines_low_activity_market():
    response = Response()
    response.json()[0]["markets"][0]["volumeNum"] = 1
    response.json()[0]["markets"][0]["liquidityNum"] = 1

    class ThinTransport:
        @staticmethod
        def get(*args, **kwargs):
            result = Response(); payload = result.json()
            payload[0]["markets"][0].update(volumeNum=1, liquidityNum=1)
            result.json = lambda: payload
            return result

    engine = create_engine("sqlite://"); Base.metadata.create_all(engine); Session = sessionmaker(bind=engine)
    with Session() as db:
        run(db, transport=ThinTransport, now=datetime(2026, 8, 30, tzinfo=timezone.utc))
        assert db.query(ExternalForecastMarket).one().quality_status == "quarantined"
