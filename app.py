from flask import Flask, render_template, send_file, request, redirect, url_for
import requests
import xml.etree.ElementTree as ET
from io import BytesIO

app = Flask(__name__)

# URL to fetch the XML data
url = "https://diavgeia.gov.gr/luminapi/api/search/export?q=decisionType:%22%CE%95%CE%93%CE%9A%CE%A5%CE%9A%CE%9B%CE%99%CE%9F%CE%A3%22&fq=organizationUid:%226%22&sort=recent&wt=xml"

# Function to fetch and parse XML data
def get_decisions():
    try:
        response = requests.get(url)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            decisions = []
            for decision in root.findall('.//decision')[:20]:
                ada = decision.find('ada').text
                subject = decision.find('subject').text
                submission_timestamp = decision.find('submissionTimestamp').text
                document_url = decision.find('documentUrl').text
                decisions.append({
                    'ada': ada,
                    'subject': subject,
                    'submissionTimestamp': submission_timestamp,
                    'documentUrl': document_url
                })
            return decisions
        else:
            print(f"Failed to retrieve data. Status code: {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return []

# Home route to display decisions
@app.route('/')
def index():
    decisions = get_decisions()
    return render_template('index.html', decisions=decisions)

# Route to download PDFs
@app.route('/download/<ada>')
def download_pdf(ada):
    decisions = get_decisions()
    for decision in decisions:
        if decision['ada'] == ada:
            document_url = decision['documentUrl']
            try:
                response = requests.get(document_url)
                if response.status_code == 200:
                    pdf_stream = BytesIO(response.content)
                    return send_file(pdf_stream, as_attachment=True, download_name=f"{ada}.pdf")
                else:
                    return f"Failed to download PDF for {ada}. Status code: {response.status_code}"
            except requests.exceptions.RequestException as e:
                return f"Error downloading PDF: {e}"
    return "Decision not found", 404

if __name__ == '__main__':
    app.run(debug=True)
