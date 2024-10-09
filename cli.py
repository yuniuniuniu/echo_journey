#!/usr/bin/env python
import subprocess
import sys

import click


@click.group()
def cli():
    assert sys.version_info > (3, 10), "Python version must be newer than 3.10"


@click.command(context_settings={"ignore_unknown_options": True})
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def run_uvicorn(args):
    click.secho("Running uvicorn server...", fg="green")
    subprocess.run(
        [
            "uvicorn",
            "echo_journey.main:app",
            "--host",
            "0.0.0.0",
            "--ws-ping-interval",
            "60",
            "--ws-ping-timeout",
            "60",
            "--timeout-keep-alive",
            "60",
        ]
        + list(args)
    )


cli.add_command(run_uvicorn)

if __name__ == "__main__":
    cli()
