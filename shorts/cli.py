"""
shorts/cli.py — Typer CLI for Shorts Factory.

Provides four subcommands:
  serve   — start the FastAPI web UI via uvicorn
  run     — execute all pending pipeline steps for a job
  step    — manage individual pipeline step records (reset)
  voice   — manage voice examples (seed)
"""

import json
import sqlite3
import typer

from pathlib import Path
from shorts.config import DB_PATH
from shorts.db import init_db
from shorts.pipeline import Pipeline

app = typer.Typer(help="Shorts Factory CLI")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Bind host"),
    port: int = typer.Option(8765, help="Bind port"),
) -> None:
    """Start the web UI server."""
    import uvicorn
    from shorts.web.app import app as web_app

    uvicorn.run(web_app, host=host, port=port)


@app.command()
def run(
    job_id: str = typer.Argument(..., help="Job ID to execute"),
) -> None:
    """Run all pending pipeline steps for a job.

    Iterates through the pipeline DAG, skipping steps already marked done/skipped,
    and exits on the first error.
    """
    init_db(str(DB_PATH))
    pipeline = Pipeline()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT step_name FROM step_results WHERE job_id=? AND status='done'",
            (job_id,),
        ).fetchall()
        done: set = {r["step_name"] for r in rows}

        while True:
            runnable = pipeline.get_runnable_steps(done)
            if not runnable:
                typer.echo("Pipeline complete.")
                break
            step_name = runnable[0]
            typer.echo(f"Running step: {step_name}")

            import importlib

            node = importlib.import_module(f"shorts.nodes.{step_name}")
            job = conn.execute(
                "SELECT execution_context FROM jobs WHERE id=?", (job_id,)
            ).fetchone()
            ctx = json.loads(job["execution_context"] or "{}") if job else {}
            result = node.run(job_id, ctx, conn, {})
            conn.execute(
                "INSERT OR REPLACE INTO step_results "
                "(job_id, step_name, status, output_path, output_checksum) VALUES (?,?,?,?,?)",
                (
                    job_id,
                    step_name,
                    result.status,
                    result.output_path,
                    result.output_checksum,
                ),
            )
            conn.commit()
            typer.echo(f"  status={result.status}")
            if result.status in ("done", "skipped"):
                done.add(step_name)
            else:
                typer.echo(f"  error: {result.error_msg}")
                break
    finally:
        conn.close()


@app.command()
def step(
    action: str = typer.Argument(..., help="Action: reset"),
    job_id: str = typer.Argument(..., help="Job ID"),
    step_name: str = typer.Argument(..., help="Step name"),
) -> None:
    """Manage pipeline steps.

    Supported actions:
      reset — marks a step as failed so it will be retried on next run.
    """
    if action == "reset":
        conn = sqlite3.connect(str(DB_PATH))
        try:
            conn.execute(
                "UPDATE step_results SET status='failed' WHERE job_id=? AND step_name=?",
                (job_id, step_name),
            )
            conn.commit()
        finally:
            conn.close()
        typer.echo(f"Reset step {step_name} for job {job_id}")
    else:
        typer.echo(f"Unknown action: {action}", err=True)
        raise typer.Exit(1)


@app.command()
def voice(
    action: str = typer.Argument(..., help="Action: seed"),
    content: str = typer.Option("", help="Script content to add as voice example"),
) -> None:
    """Manage voice examples.

    Supported actions:
      seed — insert a script body into approved_scripts.
    """
    if action == "seed":
        if not content:
            typer.echo("--content is required for seed", err=True)
            raise typer.Exit(1)
        init_db(str(DB_PATH))
        conn = sqlite3.connect(str(DB_PATH))
        try:
            conn.execute(
                "INSERT INTO approved_scripts (script_body) VALUES (?)", (content,)
            )
            conn.commit()
        finally:
            conn.close()
        typer.echo("Voice example added.")
    else:
        typer.echo(f"Unknown action: {action}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
