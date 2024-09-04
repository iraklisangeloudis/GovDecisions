import requests
import xml.etree.ElementTree as ET
import webbrowser
from datetime import datetime
import time
import os

# URL to fetch the XML data
url = "https://diavgeia.gov.gr/luminapi/api/search/export?q=decisionType:%22%CE%95%CE%93%CE%9A%CE%A5%CE%9A%CE%9B%CE%99%CE%9F%CE%A3%22&fq=organizationUid:%226%22&sort=recent&wt=xml"

# File to store downloaded URLs - Save to the Documents folder
downloaded_urls_file = r"C:\Users\irakl\Documents\downloaded_urls.txt"

# Variable to track the current day
current_day = datetime.now().strftime('%d/%m/%Y')

# Function to load already downloaded URLs from the file
def load_downloaded_urls(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            return set(line.strip() for line in file.readlines())
    return set()

# Function to save a new URL to the file
def save_downloaded_url(file_path, url):
    with open(file_path, "a", encoding="utf-8") as file:
        file.write(url + "\n")

# Function to clear the downloaded URLs file
def clear_downloaded_urls_file(file_path):
    open(file_path, "w").close()

# Main function to check for new decisions
def check_for_new_decisions():
    global current_day
    
    try:
        # Send a GET request to fetch the data
        response = requests.get(url)
        
        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Parse the XML content
            root = ET.fromstring(response.content)
            
            # Get today's date in the format used in <submissionTimestamp> (assuming it's in %d/%m/%Y %H:%M:%S format)
            today_date = datetime.now().strftime('%d/%m/%Y')
            
            # If the day has changed, clear the file and update the current day
            if today_date != current_day:
                clear_downloaded_urls_file(downloaded_urls_file)
                current_day = today_date
            
            # Load previously downloaded URLs
            downloaded_urls = load_downloaded_urls(downloaded_urls_file)
            
            # Iterate through each decision
            for decision in root.findall('.//decision'):
                submission_timestamp = decision.find('submissionTimestamp').text
                
                # Check if submissionTimestamp is today's date
                if submission_timestamp.startswith(today_date):
                    # Get the documentUrl
                    document_url = decision.find('documentUrl').text
                    
                    # If the document URL hasn't been downloaded yet, download it
                    if document_url not in downloaded_urls:
                        webbrowser.open(document_url)
                        # Save the URL to the list of downloaded URLs
                        save_downloaded_url(downloaded_urls_file, document_url)
                    # # get the first and break
                    # break
        else:
            print(f"Failed to retrieve data. Status code: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")

    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")


# Run
check_for_new_decisions()