from mcp_server.classifier import ActorClassifier
from mcp_server.config import PolicyConfig
from mcp_server.responder import Responder
from mcp_server.schemas import (
    ActorType,
    CommentEvent,
    GenerateReplyRequest,
    ThreadContext,
)
from mcp_server.triage import TriageEngine


def test_triage_labels_failure():
    classifier = ActorClassifier(["bot"])
    policy = PolicyConfig(labels={"src/": ["area-core"]})
    engine = TriageEngine(classifier=classifier, policy=policy)
    event = CommentEvent(
        pr={"owner": "acme", "repo": "demo", "number": 1},
        actor_login="alice",
        actor_name="Alice",
        event_id="evt-1",
        comment_id="c-1",
        body="Please update",
        path="src/main.py",
        line=10,
    )
    triaged = engine.triage(event)
    assert "area-core" in triaged.labels
    assert any(a.value.startswith("Thanks") for a in triaged.actions)


def test_responder_human_reply_summary():
    responder = Responder()
    req = GenerateReplyRequest(
        actor_type=ActorType.human,
        thread=ThreadContext(id="t1", file="src/app.py", line=42),
        comment="Could we rename this variable?",
    )
    response = responder.generate(req)
    assert "Thanks for taking the time" in response.body
    assert not response.resolve_thread
