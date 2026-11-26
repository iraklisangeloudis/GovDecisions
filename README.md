# Government Decisions Browser

A Flask app for browsing Greek government decisions published on Diavgeia.

## Run locally

Requires Python 3.12. From PowerShell in the project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Open http://127.0.0.1:5000/.

## Run with Docker

Requires Docker Desktop running with Linux containers.

```powershell
docker compose up --build -d flask-app
```

Open http://127.0.0.1:8080/. To stop:

```powershell
docker compose down
```

For development with local source files:

```powershell
docker compose -f docker-compose.dev.yml up --build
```

Restart after code changes. Stop with `docker compose -f docker-compose.dev.yml down`.

## Run tests

Install the test dependencies, then run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

Or with Docker:

```powershell
docker compose build tests
docker compose run --rm tests
```

## Deployment

Push to `main` to run build/tests and deploy to AWS. The EC2 must be running.
Manual deployment: GitHub Actions → Deploy to AWS → Run workflow.

For infrastructure commands, see [Terraform instructions](terraform/aws/README.md).

## License

[MIT](LICENSE)
