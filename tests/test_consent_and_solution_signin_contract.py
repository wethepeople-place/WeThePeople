from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_optional_email_consent_is_affirmative_not_preselected() -> None:
    signup = (ROOT / "frontend/src/pages/SignupPage.tsx").read_text(encoding="utf-8")
    digest = (ROOT / "frontend/src/pages/DigestSignupPage.tsx").read_text(encoding="utf-8")
    assert "useState(false);" in signup
    assert "const [digestOptIn, setDigestOptIn] = useState(false);" in signup
    assert "const [alertOptIn, setAlertOptIn] = useState(false);" in signup
    assert "const [consent, setConsent] = useState(false);" in digest


def test_signed_out_solution_votes_have_safe_signin_return_without_auto_vote() -> None:
    listing = (ROOT / "frontend/src/pages/SolutionsPage.tsx").read_text(encoding="utf-8")
    detail = (ROOT / "frontend/src/pages/SolutionDetailPage.tsx").read_text(encoding="utf-8")
    for source in (listing, detail):
        assert "Sign in to Support or Oppose" in source
        assert "No vote is submitted automatically." in source
        assert "/login?next=" in source
