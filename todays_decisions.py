import requests
import xml.etree.ElementTree as ET
import webbrowser
from datetime import datetime

# URL to fetch the XML data
url = "https://diavgeia.gov.gr/luminapi/api/search/export?q=decisionType:%22%CE%95%CE%93%CE%9A%CE%A5%CE%9A%CE%9B%CE%99%CE%9F%CE%A3%22&fq=organizationUid:%226%22&sort=recent&wt=xml"

try:
    # Send a GET request to fetch the data
    response = requests.get(url)
    
    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the XML content
        root = ET.fromstring(response.content)
        
        # Get today's date in the format used in <submissionTimestamp> (assuming it's in %d/%m/%Y %H:%M:%S format)
        today_date = datetime.now().strftime('%d/%m/%Y')
        
        # Iterate through each decision
        for decision in root.findall('.//decision'):
            submission_timestamp = decision.find('submissionTimestamp').text
            
            # Check if submissionTimestamp is today's date
            if submission_timestamp.startswith(today_date):
                # Get the documentUrl
                document_url = decision.find('documentUrl').text
                
                # Open the documentUrl in the default web browser
                webbrowser.open(document_url)
                
    else:
        print(f"Failed to retrieve data. Status code: {response.status_code}")

except requests.exceptions.RequestException as e:
    print(f"Error fetching data: {e}")

except ET.ParseError as e:
    print(f"Error parsing XML: {e}")

