# Flask Web Application for Recent Decisions

This repository contains a Python-based web application using Flask that displays the most recent decisions from an XML feed. Each decision is displayed with its subject and submission timestamp, and users can click to download the corresponding PDF.

## Getting Started

### Prerequisites

* **Python**: Ensure Python is installed and added to your system's PATH.
* **Flask**: Install Flask using pip:
  ```cmd
  pip install Flask requests
  ```
* **requests**: Install requests using pip:
  ```cmd
  pip install requests
  ```
* **Windows**: These instructions are specific to Windows 11, but the Flask app can run on any OS that supports Python.

### Setup Instructions

1. **Clone the Repository**:
   ```cmd
   git clone https://github.com/iraklisangeloudis/GovDecisions.git
   cd GovDecisions
   ```

2. **Install Dependencies**:
   Ensure Flask is installed:
   ```cmd
   pip install Flask
   ```

3. **Run the Flask Application**:
   * Navigate to the folder where the `app.py` file is located.
   * Run the Flask development server:
     ```cmd
     python app.py
     ```
   * Open a web browser and go to `http://127.0.0.1:5000/` to view the application.

## Folder Structure

```
GovDecisions/
│
├── app.py           # Main Flask application
├── templates/
│   └── index.html   # HTML template to display recent decisions
└── README.md        # This file
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

Law 3861/2010 "Strengthening transparency with the mandatory posting of laws
and acts of governmental, administrative and self-governing bodies on the
internet "Diavgeia Program" and other provisions".

Ν. 3861/2010 «Ενίσχυση της διαφάνειας με την υποχρεωτική ανάρτηση νόμων
και πράξεων των κυβερνητικών, διοικητικών και αυτοδιοικητικών οργάνων στο
διαδίκτυο «Πρόγραμμα Διαύγεια» και άλλες διατάξεις», (Α΄ 112)
