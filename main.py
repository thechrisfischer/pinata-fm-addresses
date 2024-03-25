import csv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from playwright.sync_api import Playwright, sync_playwright, expect

ZIPCODES = 'all_us_zipcodes.csv'
ADDRESS_FILE = 'addresses.txt'

sheet_id = ''
worksheet_name = ''


# Use OAuth2 credentials to authenticate with Google Sheets API
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

# Open the Google Sheet by its ID
sheet = client.open_by_key('1OXOYS_IMm3PxNj_oryOn2F73_rxoeei7iGoFpNgfHv8')

# Select the worksheet by its name
worksheet = sheet.worksheet("Sheet1")


def scrape(playwright: Playwright, zip_code) -> None:
    browser = playwright.chromium.launch(headless=True)
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
    count = 0
    for i in addresses_table:
        property_name = i.locator("td").nth(0).inner_text()
        addy = i.locator("td").nth(1).inner_text()
        csv_data = "{}|{}|{}".format(property_name, zip_code, addy)
        count = count + 1 
        
        if count > 100:
            with open(ADDRESS_FILE, 'a') as file:
                file.write(csv_data + '\n')
    
        # Append data from the CSV
            values = csv_data.split('|')
            worksheet.append_row(values)

            count = 0
    
    # ---------------------
    context.close()
    browser.close()

with open(ZIPCODES, 'r') as csvfile:
        csv_reader = csv.reader(csvfile)

        next(csv_reader)
        
        for row in csv_reader:
            with sync_playwright() as playwright:
                zip_code = row[0]
                try:
                    scrape(playwright, zip_code)
                except:
                    continue