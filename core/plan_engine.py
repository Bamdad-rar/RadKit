import asyncio
import yaml
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterator, Dict, Any

from core.models import ExecutionPlan, Session
from core.engine import ExecutionEngine
from core.exceptions import PlanExecutionError


class PlanExecutionEngine:
    """Executes multi-session plans in parallel, sequential, or async modes."""
    
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.session_engine = ExecutionEngine()
    
    def load_plan(self, plan_file: Path) -> ExecutionPlan:
        """Load and validate a plan YAML file."""
        with open(plan_file, 'r') as f:
            data = yaml.safe_load(f)
        
        # Resolve session file paths relative to plan file
        plan_dir = plan_file.parent
        for i, session_file in enumerate(data.get('session_files', [])):
            data['session_files'][i] = plan_dir / session_file
        
        return ExecutionPlan(**data)
    
    def run_plan(self, plan: ExecutionPlan) -> Iterator[Dict[str, Any]]:
        """Execute a plan based on its mode."""
        if plan.mode == "sequential":
            yield from self._run_sequential(plan)
        elif plan.mode == "parallel":
            yield from self._run_parallel(plan)
        elif plan.mode == "async":
            yield from self._run_async(plan)
    
    def _run_sequential(self, plan: ExecutionPlan) -> Iterator[Dict[str, Any]]:
        """Run sessions one after another."""
        yield {"type": "plan_start", "name": plan.name, "mode": "sequential", "total_sessions": len(plan.session_files)}
        
        for idx, session_file in enumerate(plan.session_files, 1):
            yield {"type": "session_file_start", "index": idx, "file": str(session_file)}
            
            try:
                session = self._load_session(session_file)
                yield {"type": "session_loaded", "session_name": session.name}
                
                # Execute session and forward all events
                for event in self.session_engine.run_session(session):
                    event['session_index'] = idx
                    event['session_file'] = str(session_file)
                    yield event
                    
            except Exception as e:
                yield {"type": "session_error", "index": idx, "file": str(session_file), "error": str(e)}
                # Continue with next session in sequential mode
        
        yield {"type": "plan_complete", "status": "completed"}
    
    def _run_parallel(self, plan: ExecutionPlan) -> Iterator[Dict[str, Any]]:
        """Run sessions in parallel using ThreadPoolExecutor."""
        yield {"type": "plan_start", "name": plan.name, "mode": "parallel", "total_sessions": len(plan.session_files)}
        
        results = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all sessions
            future_to_session = {}
            for idx, session_file in enumerate(plan.session_files, 1):
                session = self._load_session(session_file)
                future = executor.submit(self._execute_session_collect, session, idx, str(session_file))
                future_to_session[future] = (idx, session_file, session.name)
            
            # Collect results as they complete
            for future in as_completed(future_to_session):
                idx, session_file, session_name = future_to_session[future]
                
                try:
                    session_results = future.result()
                    results[idx] = {"status": "success", "results": session_results}
                    yield {
                        "type": "session_complete",
                        "index": idx,
                        "file": str(session_file),
                        "name": session_name,
                        "results": session_results
                    }
                except Exception as e:
                    results[idx] = {"status": "error", "error": str(e)}
                    yield {
                        "type": "session_error",
                        "index": idx,
                        "file": str(session_file),
                        "error": str(e)
                    }
        
        yield {"type": "plan_complete", "status": "completed", "summary": results}
    
    async def _run_async_impl(self, plan: ExecutionPlan):
        """Actual async implementation."""
        # For true async, you'd need to make RADIUS clients async
        # For now, run in thread pool
        loop = asyncio.get_event_loop()
        
        tasks = []
        for idx, session_file in enumerate(plan.session_files, 1):
            session = self._load_session(session_file)
            task = loop.run_in_executor(None, self._execute_session_collect, session, idx, str(session_file))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
    
    def _run_async(self, plan: ExecutionPlan) -> Iterator[Dict[str, Any]]:
        """Run sessions asynchronously (wrapper for sync generator)."""
        yield {"type": "plan_start", "name": plan.name, "mode": "async"}
        
        results = asyncio.run(self._run_async_impl(plan))
        
        for idx, result in enumerate(results, 1):
            if isinstance(result, Exception):
                yield {"type": "session_error", "index": idx, "error": str(result)}
            else:
                yield {"type": "session_complete", "index": idx, "results": result}
        
        yield {"type": "plan_complete"}
    
    def _load_session(self, session_file: Path) -> Session:
        """Load a session from YAML file."""
        with open(session_file, 'r') as f:
            data = yaml.safe_load(f)
        return Session(**data)
    
    def _execute_session_collect(self, session: Session, index: int, file_path: str) -> Dict[str, Any]:
        """Execute a session and collect all results."""
        results = {
            "session_name": session.name,
            "index": index,
            "file": file_path,
            "steps": []
        }
        
        for event in self.session_engine.run_session(session):
            if event['type'] == 'step_success':
                results['steps'].append({
                    "step": event['step'],
                    "command": event['command'],
                    "response_time_ms": event['response_time_ms'],
                    "status": "success"
                })
            elif event['type'] == 'step_failure':
                results['steps'].append({
                    "step": event['step'],
                    "command": event['command'],
                    "status": "failure",
                    "error": event['error']
                })
        
        return results

