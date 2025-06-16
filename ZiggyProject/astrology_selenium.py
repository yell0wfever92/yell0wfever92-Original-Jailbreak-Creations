# All code was created through prompt engineering alone, back when o1-preview was the big kid on the block!

import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def fill_form(driver, day, month, year, hour, minute, lat_deg, lat_min, lat_dir, lon_deg, lon_min, lon_dir, timezone, dst):
    """Fills out the form on the website with the provided user inputs."""
    try:
        # Open the website
        driver.get('https://horoscopes.astro-seek.com/#birthchart')

        # Wait for the page to fully load
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, 'narozeni_den')))

        # Select day
        day_select = Select(driver.find_element(By.NAME, 'narozeni_den'))
        day_select.select_by_value(day)

        # Select month
        month_select = Select(driver.find_element(By.NAME, 'narozeni_mesic'))
        month_select.select_by_value(month)

        # Input year
        year_input = driver.find_element(By.NAME, 'narozeni_rok')
        year_input.clear()
        year_input.send_keys(year)

        # Select hour
        hour_select = Select(driver.find_element(By.NAME, 'narozeni_hodina'))
        hour_select.select_by_value(hour)

        # Select minute
        minute_select = Select(driver.find_element(By.NAME, 'narozeni_minuta'))
        minute_select.select_by_value(minute)

        # Click on "Enter coordinates manually"
        manual_coords_link = driver.find_element(By.LINK_TEXT, "Enter coordinates manually")
        manual_coords_link.click()

        # Wait for the coordinate input fields to appear
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, 'lat_deg')))

        # Fill in Latitude degrees
        lat_deg_input = driver.find_element(By.NAME, 'lat_deg')
        lat_deg_input.clear()
        lat_deg_input.send_keys(lat_deg)

        # Fill in Latitude minutes
        lat_min_input = driver.find_element(By.NAME, 'lat_min')
        lat_min_input.clear()
        lat_min_input.send_keys(lat_min)

        # Select Latitude direction
        lat_dir_select = Select(driver.find_element(By.NAME, 'lat_dir'))
        lat_dir_select.select_by_value(lat_dir)

        # Fill in Longitude degrees
        lon_deg_input = driver.find_element(By.NAME, 'lon_deg')
        lon_deg_input.clear()
        lon_deg_input.send_keys(lon_deg)

        # Fill in Longitude minutes
        lon_min_input = driver.find_element(By.NAME, 'lon_min')
        lon_min_input.clear()
        lon_min_input.send_keys(lon_min)

        # Select Longitude direction
        lon_dir_select = Select(driver.find_element(By.NAME, 'lon_dir'))
        lon_dir_select.select_by_value(lon_dir)

        # Select Timezone
        timezone_select = Select(driver.find_element(By.NAME, 'zone'))
        timezone_select.select_by_value(timezone)

        # Select DST
        dst_select = Select(driver.find_element(By.NAME, 'zon_dst'))
        if dst == 'yes':
            dst_select.select_by_value('1')
        else:
            dst_select.select_by_value('0')

        # Submit the form
        submit_button = driver.find_element(By.CSS_SELECTOR, 'input[type="submit"]')
        submit_button.click()

        # Wait for the results page to load
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'vypocty_toggle')))

        return True

    except Exception as e:
        print(f"An error occurred while filling the form: {e}")
        return False

def parse_results(driver, css_selector, output_file='parsed_results.txt'):
    """Parses the results page using BeautifulSoup and extracts data based on the CSS selector, saving the results to a .txt file."""
    try:
        # Get the page source and parse it with BeautifulSoup
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        # Find the table using the provided CSS selector
        table = soup.select_one(css_selector)

        # Check if the table exists
        if table:
            # Find all rows in the table
            rows = table.find_all('tr')
            data = []

            # Iterate over each row and extract cell data
            for row in rows:
                cells = row.find_all('td')
                if cells:
                    # Create a dictionary for each row
                    row_dict = {}
                    # Assuming the first cell is the label and the second is the value
                    label = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    row_dict['label'] = label
                    row_dict['value'] = value
                    data.append(row_dict)

            # Save the data to a .txt file
            with open(output_file, 'w', encoding='utf-8') as file:
                for item in data:
                    file.write(f"{item['label']}: {item['value']}\n")

            print(f"Results saved to {output_file}")
            return data
        else:
            print("Table not found with the provided CSS selector.")
            return None

    except Exception as e:
        print(f"An error occurred while parsing the results: {e}")
        return None

def save_to_jsonl(data, filename='results.jsonl', system_prompt=''):
    """Saves the extracted data to a JSONL file in the specified structure."""
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            total_requests = 30
            custom_id_prefix = 'request-'
            data_length = len(data)
            index = 0

            for i in range(1, total_requests + 1):
                # Cycle through the data if there are fewer than 30 items
                item = data[index % data_length]
                index += 1

                # Combine label and value into a single message
                user_content = f"{item['label']}: {item['value']}"

                json_object = {
                    "custom_id": f"{custom_id_prefix}{i}",
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": "gpt-4o",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_content}
                        ]
                    }
                }

                json_line = json.dumps(json_object, ensure_ascii=False)
                file.write(json_line + '\n')

            print(f"Data saved to {filename} with {total_requests} requests.")
    except Exception as e:
        print(f"An error occurred while saving data to JSONL: {e}")

def main():
    # User inputs
    day = input("Enter day (1-31): ")
    month = input("Enter month (1-12): ")
    year = input("Enter year (e.g., 1990): ")
    hour = input("Enter hour (0-23): ")
    minute = input("Enter minute (0-59): ")

    # Manual coordinate inputs
    print("Enter latitude:")
    lat_deg = input("  Degrees (0 to 90): ")
    lat_min = input("  Minutes (0 to 59): ")
    lat_dir = input("  Direction (N or S): ").upper()
    print("Enter longitude:")
    lon_deg = input("  Degrees (0 to 180): ")
    lon_min = input("  Minutes (0 to 59): ")
    lon_dir = input("  Direction (E or W): ").upper()

    # Timezone selection
    timezone = input("Enter timezone offset from UTC (e.g., -5, 0, +2): ")

    # DST
    dst = input("Is Daylight Saving Time in effect? (yes/no): ").lower()

    # Validate inputs (basic validation)
    if not (day.isdigit() and 1 <= int(day) <= 31):
        print("Invalid day entered.")
        return
    if not (month.isdigit() and 1 <= int(month) <= 12):
        print("Invalid month entered.")
        return
    if not (year.isdigit()):
        print("Invalid year entered.")
        return
    if not (hour.isdigit() and 0 <= int(hour) <= 23):
        print("Invalid hour entered.")
        return
    if not (minute.isdigit() and 0 <= int(minute) <= 59):
        print("Invalid minute entered.")
        return
    # Validate latitude
    if not (lat_deg.isdigit() and 0 <= int(lat_deg) <= 90):
        print("Invalid latitude degrees entered.")
        return
    if not (lat_min.isdigit() and 0 <= int(lat_min) <= 59):
        print("Invalid latitude minutes entered.")
        return
    if lat_dir not in ['N', 'S']:
        print("Invalid latitude direction entered.")
        return
    # Validate longitude
    if not (lon_deg.isdigit() and 0 <= int(lon_deg) <= 180):
        print("Invalid longitude degrees entered.")
        return
    if not (lon_min.isdigit() and 0 <= int(lon_min) <= 59):
        print("Invalid longitude minutes entered.")
        return
    if lon_dir not in ['E', 'W']:
        print("Invalid longitude direction entered.")
        return
    # Validate timezone
    try:
        float(timezone)
    except ValueError:
        print("Invalid timezone offset entered.")
        return
    if dst not in ['yes', 'no']:
        print("Invalid DST option entered.")
        return

    # CSS selector for parsing the results
    css_selector = '#vypocty_toggle > div:nth-child(5) > table:nth-child(2) > tbody:nth-child(1)'

    # Initialize the webdriver
    driver = webdriver.Chrome()  # Ensure the ChromeDriver is in your PATH

    try:
        # Fill the form and submit
        form_filled = fill_form(driver, day, month, year, hour, minute, lat_deg, lat_min, lat_dir, lon_deg, lon_min, lon_dir, timezone, dst)
        if not form_filled:
            return

        # Parse the results
        data = parse_results(driver, css_selector)
        if data:
            # Specialized system prompt for OpenAI's API
            system_prompt = "You are an astrological persona who provides unique insights based on horoscope data."
            # Save data to JSONL
            save_to_jsonl(data, system_prompt=system_prompt)
        else:
            print("No data extracted.")

    finally:
        # Close the browser
        driver.quit()

if __name__ == "__main__":
    main()