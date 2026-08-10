from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_bill_detail_exposes_related_court_proceedings_path():
    page = (ROOT / "frontend" / "src" / "pages" / "BillDetailPage.tsx").read_text(encoding="utf-8")
    assert "Related court proceedings" in page
    assert "`/courts?bill=${encodeURIComponent(bill.bill_id)}`" in page
