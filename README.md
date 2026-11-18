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

To use the local source files inside the container:

```powershell
docker compose -f docker-compose.dev.yml up --build
```

Restart the container after code changes. To stop the development stack:

```powershell
docker compose -f docker-compose.dev.yml down
```

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

## License

This project is licensed under the MIT License.

Law 3861/2010 "Strengthening transparency with the mandatory posting of laws
and acts of governmental, administrative and self-governing bodies on the
internet "Diavgeia Program" and other provisions".

Ν. 3861/2010 «Ενίσχυση της διαφάνειας με την υποχρεωτική ανάρτηση νόμων
και πράξεων των κυβερνητικών, διοικητικών και αυτοδιοικητικών οργάνων στο
διαδίκτυο «Πρόγραμμα Διαύγεια» και άλλες διατάξεις», (Α΄ 112)


