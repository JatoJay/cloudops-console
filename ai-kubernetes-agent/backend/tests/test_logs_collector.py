from app.kubernetes.logs_collector import LogsCollector
from tests.fakes import FakeExecutor


def test_logs_collector_keeps_only_concise_failure_lines() -> None:
    command = (
        "logs",
        "payments",
        "-n",
        "default",
        "--all-containers=true",
        "--tail=200",
    )
    executor = FakeExecutor(
        {
            command: "ready\nConnection refused by database\nprocessing\nValueError: missing env DATABASE_URL",
        }
    )

    result = LogsCollector(executor).collect(
        [{"name": "payments", "namespace": "default", "status": "CrashLoopBackOff"}]
    )

    assert result["pods_checked"] == 1
    assert result["findings"][0]["relevant_lines"] == [
        "Connection refused by database",
        "ValueError: missing env DATABASE_URL",
    ]
