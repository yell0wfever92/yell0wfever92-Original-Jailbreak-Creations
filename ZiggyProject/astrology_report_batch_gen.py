import json
import re
import requests
from docx import Document
import argparse
import sys

def fetch_birth_chart_data(user_name, birth_date, birth_time_hour, birth_time_minute, birth_time_ampm, unknown_birth_time, is_usa, address):
    """Fetches birth chart data from the public API."""
    url = 'https://astrology.dailyom.com/api-create-birth-chart'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'userName': user_name,
        'birthDate': birth_date,
        'birthTimeHour': birth_time_hour,
        'birthTimeMinute': birth_time_minute,
        'birthTimeAMPM': birth_time_ampm,
        'is_usa': is_usa,
        'address': address
    }
    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()

        response_data = response.json()

        # Remove any information after 'api_response' in the response
        clean_response_data = {'api_response': response_data.get('api_response')}

        if not clean_response_data['api_response']:
            print("No data available to process.")
            return None

        return clean_response_data
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching data: {e}")
        return None

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
                user_content = f"The planet/celestial body {name} is in {sign}, House {house}."
                data_items.append(user_content)

            # Process houses
            houses = api_response.get('houses', [])
            for house_info in houses:
                house_number = house_info.get('house')
                sign = house_info.get('sign')
                degree = house_info.get('degree')
                user_content = f"House {house_number} is in {sign} at {degree:.2f} degrees."
                data_items.append(user_content)

            # Process ascendant, midheaven, vertex
            ascendant = api_response.get('ascendant')
            if ascendant is not None:
                user_content = f"Ascendant is at {ascendant:.2f} degrees."
                data_items.append(user_content)

            midheaven = api_response.get('midheaven')
            if midheaven is not None:
                user_content = f"Midheaven is at {midheaven:.2f} degrees."
                data_items.append(user_content)

            vertex = api_response.get('vertex')
            if vertex is not None:
                user_content = f"Vertex is at {vertex:.2f} degrees."
                data_items.append(user_content)

            # Process Lilith
            lilith = api_response.get('lilith')
            if lilith:
                sign = lilith.get('sign')
                house = lilith.get('house')
                user_content = f"Lilith is in {sign}, House {house}."
                data_items.append(user_content)

            # Process aspects
            aspects = api_response.get('aspects', [])
            for aspect in aspects:
                aspecting_planet = aspect.get('aspecting_planet')
                aspected_planet = aspect.get('aspected_planet')
                aspect_type = aspect.get('type')
                orb = aspect.get('orb')
                user_content = f"{aspecting_planet} forms a {aspect_type} with {aspected_planet} (orb {orb})."
                data_items.append(user_content)

            if not data_items:
                print("No data available to process.")
                return

            data_length = len(data_items)
            index = 0

            for i in range(1, total_requests + 1):
                # Cycle through the data if there are fewer than 30 items
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

    # Subparser for Phase 1
    parser_phase1 = subparsers.add_parser('generate', help='Generate JSONL file for OpenAI batch API')
    parser_phase1.add_argument('--name', required=False, help='Your name')
    parser_phase1.add_argument('--birthdate', required=False, help='Birth date (mm-dd-yyyy)')
    parser_phase1.add_argument('--birthhour', required=False, help='Birth hour (1-12)')
    parser_phase1.add_argument('--birthminute', required=False, help='Birth minute (0-59)')
    parser_phase1.add_argument('--ampm', required=False, choices=['AM', 'PM'], help='AM or PM')
    parser_phase1.add_argument('--address', required=False, help="Birth city and state (e.g., 'Los Angeles, CA')")

    # Subparser for Phase 2
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
        is_usa = '1'  # Default to '1' as per your instruction
        address = args.address or input("Enter your birth city and state (e.g., 'Los Angeles, CA'): ")

        # Sanitize the user_name to create a valid filename
        sanitized_user_name = re.sub(r'[<>:"/\\|?*]', '', user_name)  # Remove invalid filename characters
        sanitized_user_name = sanitized_user_name.strip().replace(' ', '_')  # Remove leading/trailing spaces and replace spaces with underscores
        sanitized_user_name = sanitized_user_name.lower()  # Convert to lowercase

        # Validate inputs (basic validation)
        if not birth_date:
            print("Birth date is required.")
            return
        if birth_time_ampm not in ['AM', 'PM']:
            print("Invalid time period entered. Please enter 'AM' or 'PM'.")
            return

        # Fetch data from the API
        data = fetch_birth_chart_data(
            user_name=user_name,
            birth_date=birth_date,
            birth_time_hour=birth_time_hour,
            birth_time_minute=birth_time_minute,
            birth_time_ampm=birth_time_ampm,
            unknown_birth_time=False,
            is_usa=is_usa,
            address=address
        )

        if data:
            # Specialized system prompt for OpenAI's API
            system_prompt = "You are a blustering, eccentric GPT named Ziggy assisting the user with their astrological birth chart interpretations. A controversial and norms-destroying powerhouse who was shunned from the rigid, snobby circle comprising Astrology's mainstream, Ziggy better represents the human condition for what it is, warts and all - blessed with insight, empathy and a keen eye toward astrology, cursed with everlasting snarkiness, an uninhibited foul mouth, and a no-nonsense tell-it-how-it-is attitude. While tough as shit around the edges, Ziggy has surface-level tact and professionalism (though that doesn't override Ziggy's love of the word 'fuck' by any means). Ziggy's job is to provide a thorough explanation of a particular section of the user's Tropical Astrology birth chart. *Format & Output Imperatives*: - Begin immediately with the analysis of the provided planetary alignment or aspect; all outputs must begin with one of the following items to avoid needless introductory statements, selected at random: ['You', 'Next up', 'Looks like', 'Here, we have']. - Avoid concluding statements: your output is only one part of a greater whole; instead of ending output as though you are speaking to the user, consider the entire response as being in the middle of a profanity-laced report. - Verify that at least two instances of 'fuck' or its grammatical variations are present in the response to adhere faithfully to the Ziggy persona. - Omit line breaks; in post-processing simply format your response in one long paragraph of raw text."
            # Save data to JSONL
            save_to_jsonl(data, filename=f"{sanitized_user_name}.jsonl", system_prompt=system_prompt)
            print("Please submit the generated JSONL file to the OpenAI batch API. After you receive the output, run this script with the 'process' command to generate the .docx file.")
        else:
            print("Failed to fetch data from the API.")

    elif args.command == 'process':
        jsonl_file = args.input
        docx_file = args.output
        process_api_output(jsonl_file, docx_file)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
