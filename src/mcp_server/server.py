"""MCP server entry point binding all tools."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .actions import ActionExecutor, GitHubClient
from .classifier import ActorClassifier
from .config import PolicyConfig, ServerConfig, load_policy
from .jsonrpc import JSONRPCServer
from .responder import Responder
from .schemas import (
    ApplyActionsRequest,
    ApplyActionsResponse,
    ClassificationResult,
    ClassifyActorRequest,
    GenerateReplyRequest,
    HealthResponse,
    MapInlineThreadRequest,
    SetPolicyRequest,
    TriageEventRequest,
    schema_for,
)
from .storage import Storage
from .thread_manager import ThreadManager
from .triage import TriageEngine


@dataclass(slots=True)
class MCPServer:
    """Register MCP tools and expose JSON-RPC handler."""

    config: ServerConfig
    policy: PolicyConfig
    classifier: ActorClassifier
    responder: Responder
    triage_engine: TriageEngine
    action_executor: ActionExecutor
    thread_manager: ThreadManager

    @classmethod
    def create(cls, config: ServerConfig) -> MCPServer:
        policy = load_policy(config.policy_path) if config.policy_path else PolicyConfig()
        classifier = ActorClassifier(config.bot_actors)
        responder = Responder()
        triage_engine = TriageEngine(classifier=classifier, policy=policy)
        action_executor = ActionExecutor(client=GitHubClient(config=config.github))
        storage = Storage(config.db_path)
        thread_manager = ThreadManager(storage=storage)
        return cls(
            config=config,
            policy=policy,
            classifier=classifier,
            responder=responder,
            triage_engine=triage_engine,
            action_executor=action_executor,
            thread_manager=thread_manager,
        )

    def jsonrpc_handlers(self) -> dict[str, Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]]:
        return {
            "classify_actor": self._wrap(self.classify_actor),
            "triage_event": self._wrap(self.triage_event),
            "generate_reply": self._wrap(self.generate_reply),
            "apply_actions": self._wrap(self.apply_actions),
            "map_inline_thread": self._wrap(self.map_inline_thread),
            "set_policy": self._wrap(self.set_policy),
            "health": self._wrap(self.health),
        }

    def _wrap(
        self, func: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]
    ) -> Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]:
        async def wrapper(params: dict[str, Any]) -> dict[str, Any]:
            return await func(params)

        return wrapper

    async def classify_actor(self, params: dict[str, Any]) -> dict[str, Any]:
        request = ClassifyActorRequest.model_validate(params)
        result = self.classifier.classify(request.login, request.name)
        return ClassificationResult(**asdict(result)).model_dump()

    async def triage_event(self, params: dict[str, Any]) -> dict[str, Any]:
        request = TriageEventRequest.model_validate(params)
        triaged = self.triage_engine.triage(request.event)
        return triaged.model_dump()

    async def generate_reply(self, params: dict[str, Any]) -> dict[str, Any]:
        request = GenerateReplyRequest.model_validate(params)
        response = self.responder.generate(request)
        return response.model_dump()

    async def apply_actions(self, params: dict[str, Any]) -> dict[str, Any]:
        request = ApplyActionsRequest.model_validate(params)
        results = self.action_executor.apply(
            request.actions, dry_run=request.dry_run or self.config.dry_run
        )
        return ApplyActionsResponse(results=results).model_dump()

    async def map_inline_thread(self, params: dict[str, Any]) -> dict[str, Any]:
        request = MapInlineThreadRequest.model_validate(params)
        response = await self.thread_manager.map_thread(request)
        return response.model_dump()

    async def set_policy(self, params: dict[str, Any]) -> dict[str, Any]:
        request = SetPolicyRequest.model_validate(params)
        self.policy = PolicyConfig(**request.policy)
        self.triage_engine.policy = self.policy
        return {"ok": True}

    async def health(self, params: dict[str, Any]) -> dict[str, Any]:
        db_healthy = self.thread_manager.storage.health_check()
        rate_limit = {
            "remaining": self.action_executor.client.rate_limit_remaining,
            "reset": self.action_executor.client.rate_limit_reset,
        }
        return HealthResponse(
            version="0.1.0",
            database_healthy=db_healthy,
            rate_limit=rate_limit,
        ).model_dump()

    async def serve_stdio(self) -> None:
        server = JSONRPCServer(self.jsonrpc_handlers())
        await server.serve_stdio()

    def schemas(self) -> dict[str, dict[str, Any]]:
        return {
            "classify_actor": schema_for(ClassifyActorRequest),
            "triage_event": schema_for(TriageEventRequest),
            "generate_reply": schema_for(GenerateReplyRequest),
            "apply_actions": schema_for(ApplyActionsRequest),
            "map_inline_thread": schema_for(MapInlineThreadRequest),
            "set_policy": schema_for(SetPolicyRequest),
        }


async def run_stdio(config: ServerConfig) -> None:
    server = MCPServer.create(config)
    await server.serve_stdio()


__all__ = ["MCPServer", "run_stdio"]
