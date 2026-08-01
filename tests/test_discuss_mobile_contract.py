from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_discuss_mobile_shell_stays_on_reviewed_contract():
    navigation = (ROOT / "mobile/src/navigation/TabNavigator.tsx").read_text(encoding="utf-8")
    watch = (ROOT / "mobile/src/screens/WatchScreen.tsx").read_text(encoding="utf-8")
    feed = (ROOT / "mobile/src/screens/DiscussFeedScreen.tsx").read_text(encoding="utf-8")
    detail = (ROOT / "mobile/src/screens/DiscussDetailScreen.tsx").read_text(encoding="utf-8")
    client = (ROOT / "mobile/src/api/client.ts").read_text(encoding="utf-8")

    assert 'name="DiscussTab"' in navigation
    assert 'name="DiscussDetail"' in navigation
    assert "navigate('DiscussTab')" in watch
    assert 'accessibilityLabel="Civic discussion feed"' in feed
    assert "No discussions yet" in feed and "Discussions could not load" in feed
    assert 'accessibilityLabel="Write a reply"' in detail
    assert "reportDiscussionPost" in detail and "blockDiscussionUser" in detail
    assert "/discussions/reports" in client and "/discussions/blocks/" in client
    assert "firebase" not in (navigation + watch + feed + detail + client).lower()
