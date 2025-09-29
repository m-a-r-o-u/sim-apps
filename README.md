# sim-apps

Utilities and command line applications built on top of the [sim-api-wrapper](https://github.com/m-a-r-o-u/sim-api-wrapper.git). The project provides reusable filters and pipelines for SIM API data as well as a CLI for generating group email lists.

## Features

- Composable filter architecture for SIM groups, members, and email candidates.
- Pipeline system that chains SIM API calls with filters and output generation.
- `sim-apps` CLI with an `email-list` subcommand supporting dry runs and CSV export.
- Strict typing and structured logging for easier troubleshooting.

## Installation

The project uses [uv](https://github.com/astral-sh/uv) for dependency management. Install both the wrapper and sim-apps in editable mode:

```bash
# Install the SIM API wrapper
cd /path/to/sim-api-wrapper
uv venv
uv pip install -e .

# Install sim-apps
cd /path/to/sim-apps
uv venv
uv pip install -e .[dev]
```

Authentication is handled by the wrapper. Configure credentials as described in the wrapper documentation. `sim-apps` forwards any relevant environment variables to the wrapper client.

## Usage

The CLI entry point is `sim-apps`. Use `--help` for details.

```bash
sim-apps --help
sim-apps email-list --help
```

### Email list examples

```bash
sim-apps email-list --service AI --project-groups-only --with-ai-c --stdout
sim-apps email-list --service AI --with-ai-c-but-without-ai-h-mcml --dry-run
sim-apps email-list --service AI --minimal-run --with-ai-c --unique-emails --dedup by-id --output emails.txt
sim-apps email-list --service AI --institution institution --domain-hint institution.de --csv emails.csv
sim-apps email-list --service AI --project-groups-only --dedup by-best-email --dry-run --debug-intermediate debug/
```

Dry runs still perform API calls but skip file writes and print a preview:

- Group counts before and after filters
- Unique member count after deduplication
- Sample of selected emails

### Logging and debugging

Control verbosity with `--log-level`. The email list pipeline now emits structured summaries for every step, including the
projects returned by the SIM API, how filters affect the project list, which members are loaded per project, user lookups, and
the chosen email candidates. Combine the detailed logs with `--minimal-run` to limit processing to a small subset while
debugging complex scenarios.

## Development

Run quality checks from the repository root:

```bash
uv pip install -e .[dev]
pytest -q
ruff check src tests
black --check src tests
mypy src
```

## License

Distributed under the MIT License. See `LICENSE` for details.
