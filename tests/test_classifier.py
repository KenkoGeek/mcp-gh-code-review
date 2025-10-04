from mcp_server.classifier import ActorClassifier


def test_classifier_matches_default_patterns():
    classifier = ActorClassifier(["dependabot\\[bot\\]", "custom-bot"])
    result = classifier.classify("dependabot[bot]")
    assert result.actor_type == "bot"
    assert "suffix" in result.reason.lower()


def test_classifier_human():
    classifier = ActorClassifier(["dependabot\\[bot\\]"])
    result = classifier.classify("alice")
    assert result.actor_type == "human"
