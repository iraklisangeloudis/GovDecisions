# Flask Web Application for Gov Decisions

This repository contains a Python-based web application using Flask that displays the most recent decisions from an XML feed. Each decision is displayed with its subject and submission timestamp, and users can click to download the corresponding PDF. The app provides a simple, user-friendly interface for accessing public documents from the "Diavgeia Program (https://www.diavgeia.gov.gr/api/help).

## Getting Started

### Prerequisites

* **Python**: Ensure Python is installed and added to your system's PATH.
* **Docker**: Install Docker Desktop for building and running the app in containers.

### Setup Instructions

1. **Clone the Repository**:

   ```cmd
   git clone https://github.com/iraklisangeloudis/GovDecisions.git
   cd GovDecisions
   ```

2. **Install Dependencies** (If not using Docker):
   Create a virtual environment and install dependencies:

   ```cmd
   python -m venv venv
   venv\Scripts\activate  # For Windows
   pip install -r requirements.txt
   ```

3. **Run the Flask Application Locally**:
   If running locally without Docker:

   ```cmd
   python app.py
   ```

   Open a web browser and go to `http://127.0.0.1:5000/` to view the application.

### Docker Setup

To run the app in a Docker container:

1. **Build the Docker Image**:

   ```cmd
   docker build -t flask-app .
   ```

2. **Run the Docker Container**:

   ```cmd
   docker run -p 5000:5000 flask-app
   ```

   Now, go to `http://localhost:5000` in your web browser to access the application.

#### (Optional) Using Docker Compose:

If you have a `docker-compose.yml` file, you can use Docker Compose to simplify running the app:

```cmd
docker-compose up
```

## Folder Structure

```
GovDecisions/
│
├── app.py                 # Main Flask application entry point
├── routes/
│   └── decisions.py       # Blueprint containing route logic
├── utils/
│   └── xml_parser.py      # Helper function to fetch and parse XML data
├── templates/
│   └── index.html         # HTML template to display recent decisions
├── Dockerfile             # Instructions to build Docker image
├── requirements.txt       # List of dependencies
├── docker-compose.yml     # Docker Compose file (optional)
└── README.md              # This file
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

Law 3861/2010 "Strengthening transparency with the mandatory posting of laws
and acts of governmental, administrative and self-governing bodies on the
internet "Diavgeia Program" and other provisions".

Ν. 3861/2010 «Ενίσχυση της διαφάνειας με την υποχρεωτική ανάρτηση νόμων
και πράξεων των κυβερνητικών, διοικητικών και αυτοδιοικητικών οργάνων στο
διαδίκτυο «Πρόγραμμα Διαύγεια» και άλλες διατάξεις», (Α΄ 112)


