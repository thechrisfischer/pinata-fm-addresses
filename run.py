import logging
import csv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from playwright.sync_api import Playwright, sync_playwright, expect

ZIPCODES = 'all_us_zipcodes.csv'
ADDRESS_FILE = 'addresses.txt'
POSITION = 'position.txt'
BATCH_SIZE = 10
HEADLESS = True

logging.basicConfig(level=logging.INFO)

# Use OAuth2 credentials to authenticate with Google Sheets API
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

# Open the Google Sheet by its ID
sheet = client.open_by_key('1OXOYS_IMm3PxNj_oryOn2F73_rxoeei7iGoFpNgfHv8')

# Select the worksheet by its name
worksheet = sheet.worksheet("Sheet1")

def get_zipcode_batch(start_position):
    last_position = int(start_position)
    batch_size = BATCH_SIZE
    property_data = []

    with open (ZIPCODES, 'r') as csvfile:
        csv_reader = csv.reader(csvfile)
        
        #Skip the header
        next(csv_reader)
        
        #hacky seek to last position 
        while last_position > 0:
            next(csv_reader)
            last_position = last_position - 1
        
        print("processing batch # {}".format(batch_size))
        for row in csv_reader:
            zip_code = row[5]
            if batch_size > 0:
                with sync_playwright() as playwright:
                    try:
                        data = scrape(playwright, zip_code)
                        property_data.append(data)
                        print("Batch number {} --- {}".format(batch_size, data))
                        batch_size = batch_size - 1
                    except:
                        print("Batch number {} -- no data".format(batch_size))
                        batch_size = batch_size - 1
                        continue 
    return property_data


def get_start_position():
    with open (POSITION, 'r') as file:
        saved_position = file.readline()
        return saved_position


def save_position(position):
    with open (POSITION, 'w') as file:
        file.write(position)


def write_csv_data(csvdata):
    with open (ADDRESS_FILE, 'a') as csvfile:
        csv_writer = csv.writer(csvfile, delimiter=",")
        csv_writer.writerows(csvdata)


def scrape(playwright: Playwright, zip_code):
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
    for i in addresses_table:
        property_name = i.locator("td").nth(0).inner_text()
        address = i.locator("td").nth(1).inner_text()
        property_data = [zip_code, property_name, address]
        csv_data.append(property_data)
        logging.info("Scraping - {}".format(zip_code))

        print(csv_data)
    
    context.close()
    browser.close()

    return csv_data


if __name__ == "__main__":

    start_position = get_start_position()
    batch = get_zipcode_batch(start_position)
    print(batch)
    write_csv_data(batch)
