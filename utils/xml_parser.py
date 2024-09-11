import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from config import DATA_URL

# Global variables for caching decisions and timestamp
cached_decisions = []
cache_timestamp = None

# URL to fetch the XML data (can be moved to a config file)
URL = DATA_URL

def get_decisions():
    # Fetch and parse decisions from the external XML source.
    # If the cache is older than 10 minutes, it will fetch fresh data.
    global cached_decisions, cache_timestamp
    now = datetime.now()

    # Check if cached data is older than 10 minutes
    if not cache_timestamp or (now - cache_timestamp).seconds > 600:
        try:
            # Fetch XML data from the URL
            response = requests.get(URL)
            if response.status_code == 200:
                # Parse the XML data
                root = ET.fromstring(response.content)
                decisions = []
                
                # Extract the relevant decision fields (first 20 decisions)
                for decision in root.findall('.//decision')[:20]:
                    ada = decision.find('ada').text
                    subject = decision.find('subject').text
                    submission_timestamp = decision.find('submissionTimestamp').text
                    document_url = decision.find('documentUrl').text

                    # Add each decision to the list
                    decisions.append({
                        'ada': ada,
                        'subject': subject,
                        'submissionTimestamp': submission_timestamp,
                        'documentUrl': document_url
                    })
                
                # Cache the results and update the timestamp
                cached_decisions = decisions
                cache_timestamp = now

            else:
                # Log or print an error message if the request failed
                print(f"Failed to retrieve data. Status code: {response.status_code}")
                return []
        except requests.exceptions.RequestException as e:
            # Handle exceptions related to the HTTP request
            print(f"Error fetching data: {e}")
            return []

    # Return the cached decisions
    return cached_decisions
