# MBU Journalisering SolteqTand ATS

### Overview

This project automates journalizing processes for Solteq Tand using RPA and integrates with external APIs and databases. It handles patient data, document management, dashboard updates, and error handling for clinical workflows.

### Features

- Fetch and update dashboard data via REST API
- Journalize documents and create journal notes
- Validate contractor and clinic data

### Error Handling

- Business errors are reported with specific details.
- Application errors use a standardized message and code.


### Usage

The process is started via `main.py` and requires at least one phase flag and the `--subprocess` argument.

```
python main.py --subprocess <subprocess> [--queue] [--process] [--finalize]
```

**Phase flags** (one or more can be combined in a single invocation):

| Flag | Description |
|---|---|
| `--queue` | Fetch items from the source system and populate the workqueue |
| `--process` | Pick up items from the workqueue and run the automation |
| `--finalize` | Run any post-processing/finalization steps after the queue is done |

**Required argument:**

| Argument | Choices | Description |
|---|---|---|
| `--subprocess` | `tilflytter`, `udskrivning22ar` | Selects which sub-process logic to execute |

**Examples:**

```bash
# Populate the queue for the tilflytter sub-process
python main.py --subprocess tilflytter --queue

# Process queued items for udskrivning22ar
python main.py --subprocess udskrivning22ar --process

# Run all three phases in sequence for tilflytter
python main.py --subprocess tilflytter --queue --process --finalize
```

### Requirements
- Automation Server
- Process Dashboard API