import json

from app.kubernetes.executor import CommandResult


class FakeExecutor:
    def __init__(self, responses: dict[tuple[str, ...], object]) -> None:
        self.responses = responses
        self.commands: list[list[str]] = []

    def execute(self, arguments: list[str]) -> CommandResult:
        self.commands.append(arguments)
        response = self.responses.get(tuple(arguments))
        if isinstance(response, CommandResult):
            return response
        if response is None:
            return CommandResult(
                command=["kubectl", *arguments],
                success=False,
                stderr="missing fake response",
                return_code=1,
                error="kubectl command failed",
            )
        stdout = response if isinstance(response, str) else json.dumps(response)
        return CommandResult(command=["kubectl", *arguments], success=True, stdout=stdout, return_code=0)
