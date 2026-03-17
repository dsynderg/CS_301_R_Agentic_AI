# Docker Run Guide

This project can run the multi-agent workflow in Docker.

## Prerequisites

- Docker Desktop installed and running
- An OpenAI API key exported in your terminal

PowerShell:

```powershell
$env:OPENAI_API_KEY="your_api_key_here"
```

Git Bash:

```bash
export OPENAI_API_KEY="your_api_key_here"
```

## Build

```bash
docker compose build
```

## Run (default software_team.yaml with debug)

```bash
docker compose run --rm software-team-agent
```

## Run a different YAML config

```bash
docker compose run --rm software-team-agent cat.yaml
```

## Run without debug

```bash
docker compose run --rm software-team-agent software_team.yaml
```

## Direct docker alternative

```bash
docker build -t software-team-agent .
docker run -it --rm -e OPENAI_API_KEY="$OPENAI_API_KEY" software-team-agent software_team.yaml --debug
```
