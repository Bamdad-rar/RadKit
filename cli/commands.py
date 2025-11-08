import yaml
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from pathlib import Path
from pydantic import ValidationError

from core.models import Session
from core.engine import ExecutionEngine
from core.exceptions import SessionExecutionError

console = Console()

def run_session(
    session_file: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Path to the session YAML configuration file.",
    )
):
    """
    Run a RADIUS test session from a configuration file.
    """
    try:
        with open(session_file, 'r') as f:
            data = yaml.safe_load(f)
        session = Session(**data)
    
    except FileNotFoundError:
        console.print(f"[bold red]Error: File not found at {session_file}[/bold red]")
        raise typer.Exit(code=1)
    except (yaml.YAMLError, ValidationError) as e:
        console.print(f"[bold red]Error parsing session file:[/bold red]\n{e}")
        raise typer.Exit(code=1)

    engine = ExecutionEngine()
    results_table = Table(title="📊 Execution Results")
    results_table.add_column("Step", style="magenta")
    results_table.add_column("Command", style="cyan")
    results_table.add_column("Status", justify="center")
    results_table.add_column("Response Time (ms)", style="green")

    try:
        for result in engine.run_session(session):
            if result['type'] == 'session_start':
                console.print(Panel(f"▶️ Starting Session: [bold cyan]{result['name']}[/]", expand=False))
            elif result['type'] == 'step_start':
                console.rule(f"[bold]Step {result['step']}/{result['total']}: {result['command'].upper()}[/bold]")
            elif result['type'] == 'delay':
                console.print(f"⏳ Waiting for {result['duration_ms']}ms...")
            elif result['type'] == 'step_success':
                status_text = Text("✅ SUCCESS", style="bold green")
                console.print(f"   [green]Reply received in {result['response_time_ms']:.2f}ms.[/green]")
                console.print(result['result']) # Print raw reply
                results_table.add_row(
                    str(result['step']), 
                    result['command'], 
                    status_text, 
                    f"{result['response_time_ms']:.2f}"
                )
            elif result['type'] == 'step_failure':
                status_text = Text("❌ FAILED", style="bold red")
                console.print(f"[bold red]Error executing step {result['step']}:[/bold red] {result['error']}")
                results_table.add_row(str(result['step']), result['command'], status_text, "N/A")
            elif result['type'] == 'session_end':
                if result['status'] == 'failed':
                    console.print(Panel("[bold red]Session halted due to error.[/bold red]", border_style="red"))
    
    except SessionExecutionError as e:
        console.print(f"[bold red]Execution Engine Error:[/bold red] {e}")
        raise typer.Exit(code=1)

    console.print(results_table)



def run_plan(
    plan_file: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Path to the execution plan YAML file.",
    ),
    max_workers: int = typer.Option(
        5,
        "--workers", "-w",
        help="Maximum number of parallel workers"
    )
):
    """
    Run multiple RADIUS test sessions from a plan configuration file.
    """
    from core.plan_engine import PlanExecutionEngine
    
    try:
        engine = PlanExecutionEngine(max_workers=max_workers)
        plan = engine.load_plan(plan_file)
    except Exception as e:
        console.print(f"[bold red]Error loading plan:[/bold red]\n{e}")
        raise typer.Exit(code=1)
    
    console.print(Panel(
        f"▶️ Starting Plan: [bold cyan]{plan.name}[/]\n"
        f"Mode: [yellow]{plan.mode.upper()}[/]\n"
        f"Sessions: [green]{len(plan.session_files)}[/]",
        expand=False
    ))
    
    summary_table = Table(title="📊 Plan Execution Summary")
    summary_table.add_column("Session", style="magenta")
    summary_table.add_column("File", style="cyan")
    summary_table.add_column("Status", justify="center")
    summary_table.add_column("Steps", justify="center")
    
    session_stats = {}
    
    try:
        for event in engine.run_plan(plan):
            if event['type'] == 'plan_start':
                console.print(f"🚀 Starting {event['total_sessions']} sessions in [bold]{event['mode']}[/] mode...")
            
            elif event['type'] == 'session_file_start':
                console.print(f"\n📄 Loading session {event['index']}: {event['file']}")
            
            elif event['type'] == 'session_loaded':
                console.print(f"✅ Loaded: {event['session_name']}")
            
            elif event['type'] == 'step_start':
                if plan.mode == 'sequential':
                    console.print(f"  └─ Step {event['step']}/{event['total']}: {event['command'].upper()}")
            
            elif event['type'] == 'step_success':
                if plan.mode == 'sequential':
                    console.print(f"     ✅ Success ({event['response_time_ms']:.0f}ms)")
            
            elif event['type'] == 'step_failure':
                console.print(f"     ❌ Failed: {event['error']}", style="red")
            
            elif event['type'] == 'session_complete':
                idx = event['index']
                session_stats[idx] = event.get('results', {})
                
                steps = event.get('results', {}).get('steps', [])
                success_count = sum(1 for s in steps if s['status'] == 'success')
                
                summary_table.add_row(
                    f"Session {idx}",
                    Path(event['file']).name,
                    Text("✅ SUCCESS", style="green"),
                    f"{success_count}/{len(steps)}"
                )
            
            elif event['type'] == 'session_error':
                summary_table.add_row(
                    f"Session {event['index']}",
                    Path(event['file']).name if 'file' in event else "N/A",
                    Text("❌ ERROR", style="red"),
                    "N/A"
                )
            
            elif event['type'] == 'plan_complete':
                console.print("\n")
                console.print(summary_table)
                console.print(Panel(
                    "[bold green]✅ Plan execution completed![/]",
                    border_style="green"
                ))
    
    except Exception as e:
        console.print(f"[bold red]Plan execution error:[/bold red] {e}")
        raise typer.Exit(code=1)
