from __future__ import annotations

from pathlib import Path

from autoresearch.agent_protocol.models import JobSpec
from autoresearch.executions.runner import AgentExecutionRunner


def test_haystack_langgraph_and_a2a_demo_adapters_map_to_driver_results(tmp_path) -> None:
    runner = AgentExecutionRunner(
        repo_root=Path.cwd(),
        runtime_root=tmp_path / "runtime",
        manifests_dir=Path.cwd() / "configs" / "agents",
    )

    haystack = runner.run_job(JobSpec(run_id="haystack-test", agent_id="haystack_demo", task="AAS knowledge runtime"))
    langgraph = runner.run_job(JobSpec(run_id="langgraph-test", agent_id="langgraph_order_flow", task="approval checkpoint"))
    a2a = runner.run_job(JobSpec(run_id="a2a-test", agent_id="a2a_bridge", task="A2A bridge"))

    assert haystack.driver_result.status == "succeeded"
    assert haystack.driver_result.output_artifacts[0].kind == "report"
    assert langgraph.driver_result.status == "succeeded"
    assert any("checkpoint" in item.name for item in langgraph.driver_result.output_artifacts)
    assert a2a.driver_result.status == "succeeded"
