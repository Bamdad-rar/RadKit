import typer
from core.logging_config import setup_logging

setup_logging()

from cli import commands

app = typer.Typer(
    name="rtc",
    help="A professional CLI for testing RADIUS server implementations.",
    add_completion=False
)

# Register the run command with the Typer app
app.command(name='run-session')(commands.run_session)
app.command(name='run-plan')(commands.run_plan)

@app.command()
def test_connection():
    """
    (Placeholder) A command to test the connection to a RADIUS server.
    """
    print("TODO: Implement connection test.")

if __name__ == "__main__":
    app()
