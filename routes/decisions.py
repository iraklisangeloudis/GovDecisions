from flask import Blueprint, render_template, send_file
from io import BytesIO
from utils.xml_parser import get_decisions
import requests

# Create a Blueprint for the decisions routes
decisions_bp = Blueprint('decisions', __name__)

# Home route to display decisions
@decisions_bp.route('/')
def index():
    decisions = get_decisions()
    return render_template('index.html', decisions=decisions)

# Route to download PDFs
@decisions_bp.route('/download/<ada>')
def download_pdf(ada):
    # Get the list of decisions from cache or fetch fresh data
    decisions = get_decisions()
    
    # Find the decision with the specified 'ada'
    for decision in decisions:
        if decision['ada'] == ada:
            document_url = decision['documentUrl']
            try:
                # Fetch the PDF from the document URL
                response = requests.get(document_url)
                if response.status_code == 200:
                    # Stream the PDF back to the user as a downloadable file
                    pdf_stream = BytesIO(response.content)
                    return send_file(pdf_stream, as_attachment=True, download_name=f"{ada}.pdf")
                else:
                    return f"Failed to download PDF for {ada}. Status code: {response.status_code}", 500
            except requests.exceptions.RequestException as e:
                return f"Error downloading PDF: {e}", 500
    
    return "Decision not found", 404
