import os
import shlex
import subprocess
from dataclasses import asdict, dataclass

from loguru import logger


@dataclass(frozen=True)
class CommandResult:
    command: list[str]
    success: bool
    stdout: str = ""
    stderr: str = ""
    return_code: int | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class KubectlExecutor:
    """Execute read-only kubectl commands without invoking a shell."""

    ALLOWED_COMMANDS = {
        "api-resources",
        "auth",
        "cluster-info",
        "config",
        "describe",
        "get",
        "logs",
        "version",
    }

    def __init__(
        self,
        kubeconfig_path: str = "",
        context_name: str = "",
        timeout_seconds: int = 30,
        kubectl_binary: str = "kubectl",
    ) -> None:
        self.kubeconfig_path = kubeconfig_path
        self.context_name = context_name
        self.timeout_seconds = timeout_seconds
        self.kubectl_binary = kubectl_binary

    def execute(self, arguments: list[str]) -> CommandResult:
        self._validate(arguments)
        command = [self.kubectl_binary]
        if self.kubeconfig_path:
            command.extend(["--kubeconfig", self.kubeconfig_path])
        if self.context_name:
            command.extend(["--context", self.context_name])
        command.extend(arguments)

        logger.info("Executing read-only command: {}", shlex.join(command))

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                check=False,
                env=self._safe_environment(),
                text=True,
                timeout=self.timeout_seconds,
            )
        except FileNotFoundError:
            message = f"kubectl executable was not found: {self.kubectl_binary}"
            logger.error(message)
            return CommandResult(command=command, success=False, error=message)
        except subprocess.TimeoutExpired as exc:
            message = f"kubectl command timed out after {self.timeout_seconds} seconds"
            logger.warning("{}: {}", message, shlex.join(command))
            return CommandResult(
                command=command,
                success=False,
                stdout=self._as_text(exc.stdout),
                stderr=self._as_text(exc.stderr),
                error=message,
            )
        except OSError as exc:
            message = f"kubectl could not be executed: {exc}"
            logger.error(message)
            return CommandResult(command=command, success=False, error=message)

        success = completed.returncode == 0
        if not success:
            logger.warning(
                "kubectl exited with code {}: {}",
                completed.returncode,
                completed.stderr.strip(),
            )

        return CommandResult(
            command=command,
            success=success,
            stdout=completed.stdout.strip(),
            stderr=completed.stderr.strip(),
            return_code=completed.returncode,
            error=None if success else "kubectl command failed",
        )

    def _validate(self, arguments: list[str]) -> None:
        if not arguments:
            raise ValueError("A kubectl command is required")
        if arguments[0] not in self.ALLOWED_COMMANDS:
            raise ValueError(f"kubectl command is not read-only: {arguments[0]}")
        if arguments[0] == "config" and (
            len(arguments) < 2 or arguments[1] not in {"current-context", "get-contexts"}
        ):
            raise ValueError("kubectl config command is not read-only")
        if any("\x00" in argument or "\n" in argument or "\r" in argument for argument in arguments):
            raise ValueError("kubectl arguments cannot contain control characters")

    @staticmethod
    def _safe_environment() -> dict[str, str]:
        environment = os.environ.copy()
        environment.setdefault("KUBECTL_COMMAND_HEADERS", "false")
        return environment

    @staticmethod
    def _as_text(value: str | bytes | None) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode(errors="replace")
        return value
