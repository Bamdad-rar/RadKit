import time
from rich.console import Console
import logging

from core.models import Session, Step, ConnectionConfig
from core.radius_clients import get_radius_client
from core.exceptions import SessionExecutionError

class ExecutionEngine:
    """Orchestrator of RADIUS sessions."""

    def __init__(self):
        self.console = Console()

    def run_session(self, session: Session):
        """
        Executes all steps in a session, yielding results for each step.
        This makes it UI-agnostic.
        """
        yield {"type": "session_start", "name": session.name}
        
        try:
            client = get_radius_client(
                vendor=session.config.vendor,
                server=session.config.server,
                secret=session.config.secret,
                dict_path="./core/dictionaries/E_develop/dictionary",
                logger=logging.getLogger(f"{session.config.vendor}_logger")
            )
        except Exception as e:
            raise SessionExecutionError(f"Failed to initialize RADIUS client: {e}")

        total_steps = len(session.sequence)
        for i, step in enumerate(session.sequence):
            step_num = i + 1
            yield {"type": "step_start", "step": step_num, "total": total_steps, "command": step.command}

            if step.delay_before > 0:
                yield {"type": "delay", "duration_ms": step.delay_before}
                time.sleep(step.delay_before / 1000)

            try:
                start_time = time.time()
                result = self._execute_step(client, step, session.config)
                end_time = time.time()
                response_time_ms = (end_time - start_time) * 1000
                
                yield {
                    "type": "step_success",
                    "step": step_num,
                    "command": step.command,
                    "response_time_ms": response_time_ms,
                    "result": result 
                }

            except Exception as e:
                yield {"type": "step_failure", "step": step_num, "command": step.command, "error": str(e)}
                yield {"type": "session_end", "status": "failed"}
                return

        yield {"type": "session_end", "status": "completed"}

    def _execute_step(self, client, step: Step, config: ConnectionConfig) -> dict:
        command_map = {
            "auth": client.authenticate,
            "start": client.start,
            "alive": client.alive,
            "stop": client.stop,
        }
        
        if step.command not in command_map:
            raise SessionExecutionError(f"Unknown command: {step.command}")
            
        if step.command == "auth":
            return command_map[step.command](config.username, config.password, **step.avps)
        else:
            return command_map[step.command](config.username, **step.avps)
