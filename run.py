import logging
import csv
import gspread
import os
from oauth2client.service_account import ServiceAccountCredentials
from playwright.sync_api import Playwright, sync_playwright

ZIPCODES = 'all_us_zipcodes.csv'
ADDRESS_FILE = 'addresses.csv'
POSITION = 'position.txt'
BATCH_SIZE = 25
HEADLESS = True
ENABLE_GSHEETS = False

logging.basicConfig(level=logging.INFO)

# Use OAuth2 credentials to authenticate with Google Sheets API
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

# Open the Google Sheet by its ID
sheet = client.open_by_key('1OXOYS_IMm3PxNj_oryOn2F73_rxoeei7iGoFpNgfHv8')

# Select the worksheet by its name
worksheet = sheet.worksheet("Sheet1")

def get_zipcode_batch() -> list | None:

    start_position = get_start_position()
    batch_size = BATCH_SIZE
    property_data = []

    with open (ZIPCODES, 'r') as csvfile:
        csv_reader = csv.reader(csvfile)
        skip_row = True
        logging.info("processing batch of size {}".format(batch_size))
        while skip_row == True:
            row = next(csv_reader)
            position = row[0]
            zip_code = row[5]
            
            if position == start_position:
                logging.info("Found the starting position  -- {} at position {}".format(zip_code, position))
                skip_row = False
            else:
                continue
        
        while batch_size > 0:
            row = next(csv_reader)
            position = row[0]
            zip_code = row[5]
            save_position(position)
            
            try:
                data = scrape(zip_code)
                if data is not None:
                    for p in data:
                        property_data.append(p)
                        logging.info("Batch number {} --- position {} -- property {}".format(batch_size, position, p))
                batch_size = batch_size - 1
            except:
                logging.info("Batch number {} -- no data".format(batch_size))
                batch_size = batch_size - 1
                continue 
        
        logging.info("Batch complete")
    
    if property_data:
        return property_data
    else:
        return None


def get_start_position() -> str:
    
    if not os.path.exists(POSITION):
        with open(POSITION, 'w') as file:
            pass
        logging.info("Creating position file and starting from the top :)")
        start_position = "1"
    else:
        with open (POSITION, 'r') as file:
            line = file.readline()
            if line:
                start_position = str(line).strip()
                logging.info("Previous save point found starting from zipcode {}".format(start_position))
            else:
                start_position = "1"
                logging.info("No saved position found starting from the top :)")
    
    return start_position


def save_position(position: str) -> None:
    with open (POSITION, 'w') as file:
        file.write(position)
    return


def write_csv_data(csvdata: list) -> None:
    with open (ADDRESS_FILE, 'a') as csvfile:
        csv_writer = csv.writer(csvfile, delimiter=",")
        csv_writer.writerows(csvdata)
    return


def scrape(zip_code: str) -> list | None:
    
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=HEADLESS)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://myhome.freddiemac.com/renting/lookup")
        page.locator("label").filter(has_text="Search for all properties in").click()
        page.get_by_text("By checking this box and").click()
        page.get_by_label("Zip Code", exact=True).click()
        page.get_by_label("Zip Code", exact=True).fill(zip_code)
        page.get_by_role("button", name="Submit").click()
        page.wait_for_url('**/zipcode')
        zip_table = page.locator("#block-rentallookupapiresponseblock div").nth(1)
        addresses_table = zip_table.locator("tbody").locator("tr").all()
        csv_data = []
        
        logging.info("Scraping - {}".format(zip_code))
        
        for element in addresses_table:
            property_name = element.locator("td").nth(0).inner_text()
            address = element.locator("td").nth(1).inner_text()
            property_data = [zip_code, property_name, address]

            if property_data:
                csv_data.append(property_data)

        context.close()
        browser.close()

    if csv_data:
        return csv_data
    else:
        return None


if __name__ == "__main__":

    start_position = get_start_position()
    
    while start_position is not None:
        batch = get_zipcode_batch()
        
        if batch is not None:
            write_csv_data(batch)
        
        if batch is not None and ENABLE_GSHEETS:
            worksheet.append_rows(batch)