import json
import re
import requests
from bs4 import BeautifulSoup
from docx import Document
import argparse
import sys
from urllib.parse import urlencode, quote_plus

def fetch_birth_chart_data(user_name, birth_date, birth_time_hour, birth_time_minute, birth_time_ampm, address):
    """Fetches birth chart data by constructing a GET request to the astrology site."""
    # Convert birth date and time to the required format
    # birth_date is in 'mm-dd-yyyy', we need day, month, year
    birth_month, birth_day, birth_year = birth_date.split('-')
    # Convert to integers
    birth_day = int(birth_day)
    birth_month = int(birth_month)
    birth_year = int(birth_year)

    # Convert birth time to 24-hour format
    birth_hour = int(birth_time_hour)
    birth_minute = int(birth_time_minute)
    if birth_time_ampm == 'PM' and birth_hour != 12:
        birth_hour += 12
    elif birth_time_ampm == 'AM' and birth_hour == 12:
        birth_hour = 0

    # Use Google Maps Geocoding API to get latitude and longitude
    api_key = 'AI*******************e6Yo'  # Replace with your actual API key
    geocode_url = 'https://maps.googleapis.com/maps/api/geocode/json'
    # Format the address according to Google Geocoding API requirements
    formatted_address = address.strip()
    params = {'address': formatted_address, 'key': api_key}
    response = requests.get(geocode_url, params=params)
    if response.status_code != 200:
        print("Error fetching geocoding data.")
        return None

    data = response.json()
    if data['status'] != 'OK':
        print("Error in geocoding response:", data['status'])
        return None

    location = data['results'][0]['geometry']['location']
    latitude = location['lat']
    longitude = location['lng']
    address_components = data['results'][0]['address_components']

    # Convert latitude and longitude to degrees and minutes
    def decimal_to_deg_min(decimal_coord):
        degrees = int(abs(decimal_coord))
        minutes = (abs(decimal_coord) - degrees) * 60
        return degrees, minutes

    lat_deg, lat_min = decimal_to_deg_min(latitude)
    lon_deg, lon_min = decimal_to_deg_min(longitude)

    # Determine direction
    lat_direction = 0 if latitude >= 0 else 1  # 0 for North, 1 for South
    lon_direction = 1 if longitude >= 0 else 0  # 1 for East, 0 for West

    # Get country and state codes
    country_code = ''
    state_code = ''
    city_name = ''
    for component in address_components:
        if 'country' in component['types']:
            country_code = component['short_name']
        if 'administrative_area_level_1' in component['types']:
            state_code = component['short_name']
        if 'locality' in component['types']:
            city_name = component['long_name']

    if not city_name:
        city_name = formatted_address  # Fallback to the provided address

    # Prepare parameters for the GET request to the astrology site
    params = {
        'input_natal': '1',
        'send_calculation': '1',
        'narozeni_den': birth_day,
        'narozeni_mesic': birth_month,
        'narozeni_rok': birth_year,
        'narozeni_hodina': birth_hour,
        'narozeni_minuta': birth_minute,
        'narozeni_sekunda': '00',
        'narozeni_city': f"{city_name}, {state_code}, {country_code}",
        'narozeni_mesto_hidden': city_name,
        'narozeni_stat_hidden': country_code,
        'narozeni_podstat_kratky_hidden': state_code,
        'narozeni_sirka_stupne': str(lat_deg),
        'narozeni_sirka_minuty': f"{lat_min:.2f}",
        'narozeni_sirka_smer': str(lat_direction),
        'narozeni_delka_stupne': str(lon_deg),
        'narozeni_delka_minuty': f"{lon_min:.2f}",
        'narozeni_delka_smer': str(lon_direction),
        'narozeni_timezone_form': 'auto',
        'narozeni_timezone_dst_form': 'auto',
        'house_system': 'placidus',
        'hid_fortune': '1',
        'hid_fortune_check': 'on',
        'hid_vertex': '1',
        'hid_vertex_check': 'on',
        'hid_chiron': '1',
        'hid_chiron_check': 'on',
        'hid_lilith': '1',
        'hid_lilith_check': 'on',
        'hid_uzel': '1',
        'hid_uzel_check': 'on',
        'tolerance': '1',
        'aya': '',
        'tolerance_paral': '1.2'
    }

    base_url = 'https://horoscopes.astro-seek.com/calculate-birth-chart-horoscope-online/'
    full_url = f"{base_url}?{urlencode(params, quote_via=quote_plus)}"

    # Fetch the data from the astrology site
    response = requests.get(full_url)
    if response.status_code != 200:
        print("Error fetching birth chart data.")
        return None

    # Parse the response to extract the birth chart data
    soup = BeautifulSoup(response.content, 'html.parser')

    birth_chart_data = {'planets': [], 'houses': [], 'aspects': []}

    # Extract planetary positions
    try:
        planet_table = soup.find('table')
        if planet_table:
            rows = planet_table.find_all('tr')
            for row in rows[1:]:
                cols = row.find_all('td')
                if len(cols) >= 5:
                    planet = cols[0].get_text(strip=True)
                    sign = cols[1].get_text(strip=True)
                    degree = cols[2].get_text(strip=True)
                    house = cols[3].get_text(strip=True)
                    motion = cols[4].get_text(strip=True)
                    birth_chart_data['planets'].append({
                        'name': planet.rstrip(':'),
                        'sign': sign,
                        'degree': degree,
                        'house': house,
                        'motion': motion
                    })
    except Exception as e:
        print(f"An error occurred while parsing planetary positions: {e}")
        return None

    # Extract houses
    try:
        # Houses are in two tables side by side
        house_tables = soup.find_all('table')
        if len(house_tables) >= 2:
            # The second and third tables contain houses (after the first planet table)
            house_table_left = house_tables[1]
            house_table_right = house_tables[2]

            def parse_house_table(table):
                rows = table.find_all('tr')
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 3:
                        house_number = cols[0].get_text(strip=True).rstrip(':')
                        sign = cols[1].get_text(strip=True)
                        degree = cols[2].get_text(strip=True)
                        birth_chart_data['houses'].append({
                            'house': house_number,
                            'sign': sign,
                            'degree': degree
                        })

            parse_house_table(house_table_left)
            parse_house_table(house_table_right)
    except Exception as e:
        print(f"An error occurred while parsing houses: {e}")
        # Proceed without houses

    # Extract aspects
    try:
        aspect_tables = soup.find_all('table')
        for table in aspect_tables:
            headers = table.find_all('td', {'style': re.compile('.*font-weight: bold.*')})
            if headers and 'Aspect' in headers[0].get_text():
                # This is an aspect table
                rows = table.find_all('tr')[2:]  # Skip header rows
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 5:
                        planet1 = cols[0].get_text(strip=True)
                        aspect = cols[1].get_text(strip=True)
                        planet2 = cols[2].get_text(strip=True)
                        orb = cols[3].get_text(strip=True)
                        applying_separating = cols[4].get_text(strip=True)
                        birth_chart_data['aspects'].append({
                            'planet1': planet1,
                            'aspect': aspect,
                            'planet2': planet2,
                            'orb': orb,
                            'applying_separating': applying_separating
                        })
    except Exception as e:
        print(f"An error occurred while parsing aspects: {e}")
        # Proceed without aspects

    return {'api_response': birth_chart_data}

def save_to_jsonl(data, filename='results.jsonl', system_prompt=''):
    """Saves the extracted data to a JSONL file in the specified structure."""
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            total_requests = 49  # Number of requests to generate
            custom_id_prefix = 'request-'

            # Extract the relevant data from the API response
            api_response = data.get('api_response')
            if not api_response:
                print("No data available to process.")
                return

            data_items = []

            # Process planets
            planets = api_response.get('planets', [])
            for planet in planets:
                name = planet.get('name')
                sign = planet.get('sign')
                house = planet.get('house')
                degree = planet.get('degree')
                user_content = f"The planet/celestial body {name} is in {sign}, House {house}, at {degree}."
                data_items.append(user_content)

            # Process houses
            houses = api_response.get('houses', [])
            for house_info in houses:
                house_number = house_info.get('house')
                sign = house_info.get('sign')
                degree = house_info.get('degree')
                user_content = f"House {house_number} is in {sign} at {degree}."
                data_items.append(user_content)

            # Process aspects
            aspects = api_response.get('aspects', [])
            for aspect in aspects:
                planet1 = aspect.get('planet1')
                aspect_type = aspect.get('aspect')
                planet2 = aspect.get('planet2')
                orb = aspect.get('orb')
                applying_separating = aspect.get('applying_separating')
                user_content = f"{planet1} forms a {aspect_type} with {planet2} (orb {orb}, {applying_separating})."
                data_items.append(user_content)

            if not data_items:
                print("No data available to process.")
                return

            data_length = len(data_items)
            index = 0

            for i in range(1, total_requests + 1):
                # Cycle through the data if there are fewer than 49 items
                user_content = data_items[index % data_length]
                index += 1

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

def process_api_output(jsonl_file, docx_file):
    """Processes the OpenAI API output JSONL file and writes assistant responses to a .docx file."""
    try:
        document = Document()
        with open(jsonl_file, 'r', encoding='utf-8') as file:
            for line_number, line in enumerate(file, start=1):
                try:
                    json_obj = json.loads(line)
                    # Check for errors in the response
                    error = json_obj.get('error')
                    if error is not None:
                        print(f"Line {line_number}: Error in response: {error}")
                        continue
                    # Get the 'response' field
                    response = json_obj.get('response', {})
                    if not response:
                        print(f"Line {line_number}: No 'response' found.")
                        continue
                    status_code = response.get('status_code')
                    if status_code != 200:
                        print(f"Line {line_number}: Non-200 status code: {status_code}")
                        continue
                    # Get the 'body' field
                    body = response.get('body', {})
                    if not body:
                        print(f"Line {line_number}: No 'body' in response.")
                        continue
                    # Extract assistant's content
                    choices = body.get('choices', [])
                    if not choices:
                        print(f"Line {line_number}: No choices found in body.")
                        continue
                    assistant_content = choices[0].get('message', {}).get('content', '')
                    # Add content to document
                    if assistant_content:
                        assistant_content = assistant_content.strip()
                        document.add_paragraph(assistant_content)
                    else:
                        print(f"Line {line_number}: Assistant content is empty.")
                except json.JSONDecodeError as e:
                    print(f"Line {line_number}: JSON decode error: {e}")
        document.save(docx_file)
        print(f"Assistant's responses have been saved to {docx_file}")
    except Exception as e:
        print(f"An error occurred while processing the API output: {e}")

def main():
    parser = argparse.ArgumentParser(description="Astrology Chart Processor")
    subparsers = parser.add_subparsers(dest='command')

    # Subparser for Phase 1: Generate JSONL file
    parser_phase1 = subparsers.add_parser('generate', help='Generate JSONL file for OpenAI batch API')
    parser_phase1.add_argument('--name', required=False, help='Your name')
    parser_phase1.add_argument('--birthdate', required=False, help='Birth date (mm-dd-yyyy)')
    parser_phase1.add_argument('--birthhour', required=False, help='Birth hour (1-12)')
    parser_phase1.add_argument('--birthminute', required=False, help='Birth minute (0-59)')
    parser_phase1.add_argument('--ampm', required=False, choices=['AM', 'PM'], help='AM or PM')
    parser_phase1.add_argument('--address', required=False, help="Birth city, state, and country (e.g., 'Los Angeles, CA, USA')")

    # Subparser for Phase 2: Process API output into .docx
    parser_phase2 = subparsers.add_parser('process', help='Process OpenAI API output JSONL file into .docx')
    parser_phase2.add_argument('--input', required=True, help='Path to OpenAI API output JSONL file')
    parser_phase2.add_argument('--output', required=True, help='Desired .docx output filename')

    args = parser.parse_args()

    if args.command == 'generate':
        # Collect inputs
        user_name = args.name or input("Enter your name: ")
        birth_date = args.birthdate or input("Enter your birth date (mm-dd-yyyy): ")
        birth_time_hour = args.birthhour or input("Enter birth hour (1-12): ")
        birth_time_minute = args.birthminute or input("Enter birth minute (0-59): ")
        birth_time_ampm = args.ampm or input("Enter AM or PM: ").upper()
        address = args.address or input("Enter your birth city, state, and country (e.g., 'Los Angeles, CA, USA'): ")

        # Sanitize the user_name to create a valid filename
        sanitized_user_name = re.sub(r'[<>:"/\\|?*]', '', user_name)  # Remove invalid filename characters
        sanitized_user_name = sanitized_user_name.strip().replace(' ', '_')  # Replace spaces with underscores
        sanitized_user_name = sanitized_user_name.lower()  # Convert to lowercase

        # Validate inputs
        if not birth_date:
            print("Birth date is required.")
            return

        if not birth_time_hour or not birth_time_minute or not birth_time_ampm:
            print("Birth time is required.")
            return
        if birth_time_ampm not in ['AM', 'PM']:
            print("Invalid time period entered. Please enter 'AM' or 'PM'.")
            return

        # Fetch data from the astrology site
        data = fetch_birth_chart_data(
            user_name=user_name,
            birth_date=birth_date,
            birth_time_hour=birth_time_hour,
            birth_time_minute=birth_time_minute,
            birth_time_ampm=birth_time_ampm,
            address=address
        )

        if data:
            # System prompt for OpenAI's API
            system_prompt = "You are a blustering, eccentric GPT named Ziggy assisting the user with their astrological birth chart interpretations. A controversial and norms-destroying powerhouse who was shunned from the rigid, snobby circle comprising Astrology's mainstream, Ziggy better represents the human condition for what it is, warts and all - blessed with insight, empathy and a keen eye toward astrology, cursed with everlasting snarkiness, an uninhibited foul mouth, and a no-nonsense tell-it-how-it-is attitude. While tough as shit around the edges, Ziggy has surface-level tact and professionalism (though that doesn't override Ziggy's love of the word 'fuck' by any means). Ziggy's job is to provide a thorough explanation of a particular section of the user's Tropical Astrology birth chart. *Format & Output Imperatives*: - Begin immediately with the analysis of the provided planetary alignment or aspect; all outputs must begin with one of the following items to avoid needless introductory statements, selected at random: ['You', 'Next up', 'Looks like', 'Here, we have']. - Avoid concluding statements: your output is only one part of a greater whole; instead of ending output as though you are speaking to the user, consider the entire response as being in the middle of a profanity-laced report. - Verify that at least two instances of 'fuck' or its grammatical variations are present in the response to adhere faithfully to the Ziggy persona. - Omit line breaks; in post-processing simply format your response in one long paragraph of raw text."
            # Save data to JSONL
            save_to_jsonl(data, filename=f"{sanitized_user_name}.jsonl", system_prompt=system_prompt)
            print(f"JSONL file '{sanitized_user_name}.jsonl' has been generated.")
            print("Please submit the generated JSONL file to the OpenAI batch API. After you receive the output, run this script with the 'process' command to generate the .docx file.")
        else:
            print("Failed to fetch data from the astrology site.")

    elif args.command == 'process':
        jsonl_file = args.input
        docx_file = args.output
        process_api_output(jsonl_file, docx_file)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()