import sys
import subprocess
import argparse

def install_package(package):
	subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Check and install required packages
required_packages = ['plexapi', 'requests', 'fuzzywuzzy', 'colorama', 'python-Levenshtein']
for package in required_packages:
	try:
		__import__(package.replace('-', '_'))  # Replace hyphen with underscore for import
	except ImportError:
		print(f"Installing {package}...")
		install_package(package)

import requests
from plexapi.server import PlexServer
import re
import csv
import time
import os
import configparser
from datetime import datetime
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from colorama import init, Fore, Style

CONFIG_FILE = 'plex_collection_config.ini'

# Initialize colorama
init()

### Plex server details - will be set via args or user input ###
PLEX_URL = ''
PLEX_TOKEN = ''
MOVIE_LIBRARY_NAME = ''
CSV_FILE_PATH = ''
IMDB_COLLECTION_NAME = ''
LOG_FILE_PATH = ''
REPORT_FILE_PATH = ''

# Fuzzy matching thresholds
TITLE_YEAR_MATCH_RATIO = 85  # Minimum match ratio for title + year
TITLE_ONLY_MATCH_RATIO = 90  # Minimum match ratio for title only

def load_config():
	"""Load saved configuration"""
	config = configparser.ConfigParser()
	if os.path.exists(CONFIG_FILE):
		config.read(CONFIG_FILE)
	return config

def save_config(url, token, library):
	"""Save configuration to file"""
	config = configparser.ConfigParser()
	config['DEFAULT'] = {
		'PLEX_URL': url,
		'PLEX_TOKEN': token,
		'MOVIE_LIBRARY_NAME': library
	}
	with open(CONFIG_FILE, 'w') as configfile:
		config.write(configfile)

def display_instructions():
	"""Display instructions for users who need guidance"""
	print(f"\n{Fore.CYAN}=== Instructions ==={Style.RESET_ALL}")
	print(f"{Fore.WHITE}1. Go to an IMDB list and export the list as a .CSV (like https://www.imdb.com/list/ls569744078/)")
	print(f"2. Rename that .CSV file from the IMDB list to something more memorable and friendly")
	print(f"3. Get your Plex token via these instructions: https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/{Style.RESET_ALL}\n")

def get_existing_collections():
	"""Get list of existing collections in the movie library"""
	try:
		plex = PlexServer(PLEX_URL, PLEX_TOKEN)
		movie_library = plex.library.section(MOVIE_LIBRARY_NAME)
		
		# Get all collections from the movie library
		collections = movie_library.collections()
		return [collection.title for collection in collections]
	except Exception as e:
		log_message(f"Error retrieving existing collections: {str(e)}", message_type="ERROR", print_to_console=True)
		return []

def parse_arguments():
	"""Parse command line arguments"""
	parser = argparse.ArgumentParser(description="Plex Collection Creator")
	parser.add_argument('-u', '--url', help='Plex server URL (default: http://127.0.0.1:32400)')
	parser.add_argument('-t', '--token', help='Plex authentication token')
	parser.add_argument('-c', '--csv', help='Path to the CSV file containing the movie list')
	parser.add_argument('-n', '--name', help='Name for the collection to be created or updated')
	parser.add_argument('-l', '--library', help='Plex movie library name (default: Movies)')
	parser.add_argument('-i', '--instructions', action='store_true', help='Display instructions and exit')
	return parser.parse_args()

def initialize_logging():
	"""Create log file with timestamp"""
	global LOG_FILE_PATH, REPORT_FILE_PATH
	timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
	LOG_FILE_PATH = f'plex_collection_log_{IMDB_COLLECTION_NAME}_{timestamp}.txt'
	REPORT_FILE_PATH = f'plex_collection_report_{IMDB_COLLECTION_NAME}_{timestamp}.csv'
	
	with open(LOG_FILE_PATH, 'w', encoding='utf-8') as log_file:
		log_file.write(f"Plex Collection Creation Log - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
		log_file.write(f"Collection Name: {IMDB_COLLECTION_NAME}\n")
		log_file.write(f"CSV File: {CSV_FILE_PATH}\n")
		log_file.write(f"Plex URL: {PLEX_URL}\n")
		log_file.write(f"Plex Library: {MOVIE_LIBRARY_NAME}\n")
		log_file.write("="*50 + "\n\n")

def log_message(message, print_to_console=True, message_type="INFO"):
	"""Log messages to file and optionally print to console with colors"""
	timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
	log_entry = f"[{timestamp}] {message}\n"
	
	with open(LOG_FILE_PATH, 'a', encoding='utf-8') as log_file:
		log_file.write(log_entry)
	
	if print_to_console:
		if message_type == "SUCCESS":
			print(f"{Fore.GREEN}{message}{Style.RESET_ALL}")
		elif message_type == "ERROR":
			print(f"{Fore.RED}{message}{Style.RESET_ALL}")
		elif message_type == "WARNING":
			print(f"{Fore.YELLOW}{message}{Style.RESET_ALL}")
		else:
			print(message)

def add_collection(library_key, rating_key, movie_title):
	"""Add movie to collection and return success status"""
	headers = {"X-Plex-Token": PLEX_TOKEN}
	params = {
		"type": 1,
		"id": rating_key,
		"collection[0].tag.tag": IMDB_COLLECTION_NAME,
		"collection.locked": 1
	}

	url = f"{PLEX_URL}/library/sections/{library_key}/all"
	try:
		response = requests.put(url, headers=headers, params=params)
		return response.status_code == 200
	except Exception as e:
		log_message(f"Error adding collection for {movie_title}: {str(e)}", message_type="ERROR")
		return False

def find_imdb_id(imdb_url):
	"""Extract id from imdb_url"""
	match = re.search(r'(tt\d+)', imdb_url)
	return match.group(0) if match else None

def clean_title(title):
	"""Clean title for better matching"""
	if not title:
		return ""
	return title.lower().replace("the ", "").strip()

def find_movie_by_title_year(movies, title, year, original_title=None):
	"""Find movie by title and year with fuzzy matching"""
	# Try exact match first
	for movie in movies:
		if (movie.title.lower() == title.lower() or 
			(original_title and movie.title.lower() == original_title.lower())):
			if str(movie.year) == str(year):
				return movie
	
	# Try fuzzy matching
	best_match = None
	highest_score = 0
	
	for movie in movies:
		# Compare with main title
		title_score = fuzz.ratio(clean_title(movie.title), clean_title(title))
		
		# Compare with original title if available
		original_score = 0
		if original_title:
			original_score = fuzz.ratio(clean_title(movie.title), clean_title(original_title))
		
		current_score = max(title_score, original_score)
		
		# Only consider if year matches
		if str(movie.year) == str(year) and current_score > highest_score:
			highest_score = current_score
			best_match = movie
	
	if best_match and highest_score >= TITLE_YEAR_MATCH_RATIO:
		log_message(f"Fuzzy matched '{title}' ({year}) to '{best_match.title}' ({best_match.year}) with score {highest_score}", message_type="WARNING")
		return best_match
	
	return None

def find_movie_by_title(movies, title, original_title=None):
	"""Find movie by title only with fuzzy matching"""
	best_match = None
	highest_score = 0
	
	for movie in movies:
		title_score = fuzz.ratio(clean_title(movie.title), clean_title(title))
		
		original_score = 0
		if original_title:
			original_score = fuzz.ratio(clean_title(movie.title), clean_title(original_title))
		
		current_score = max(title_score, original_score)
		
		if current_score > highest_score:
			highest_score = current_score
			best_match = movie
	
	if best_match and highest_score >= TITLE_ONLY_MATCH_RATIO:
		log_message(f"Title-only matched '{title}' to '{best_match.title}' with score {highest_score}", message_type="WARNING")
		return best_match
	
	return None

def find_existing_collection_items(plex, collection_name):
	"""Find all movies that are already in the specified collection"""
	existing_items = {}
	
	# Search all movie sections
	try:
		movie_library = plex.library.section(MOVIE_LIBRARY_NAME)
		collection_items = movie_library.search(collection=collection_name)
		
		# Create a map of both IMDB IDs and rating keys
		for item in collection_items:
			# Add by rating key
			existing_items[item.ratingKey] = item
			
			# Add by IMDB ID if available
			if 'imdb://' in item.guid:
				imdb_id = item.guid.split('imdb://')[1].split('?')[0]
				existing_items[imdb_id] = item
				
		log_message(f"Found {len(collection_items)} movies already in collection '{collection_name}'")
		return existing_items
	except Exception as e:
		log_message(f"Error finding existing collection items: {str(e)}", message_type="ERROR")
		return {}

def generate_report(report_data):
	"""Generate CSV report of processed movies"""
	with open(REPORT_FILE_PATH, 'w', newline='', encoding='utf-8') as csvfile:
		fieldnames = ['Title', 'Year', 'Original Title', 'IMDB_ID', 'Status', 'Match_Method', 'Plex_Title', 'Plex_Year', 'Notes']
		writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
		writer.writeheader()
		
		for item in report_data:
			writer.writerow({
				'Title': item['title'],
				'Year': item['year'],
				'Original Title': item.get('original_title', ''),
				'IMDB_ID': item['imdb_id'],
				'Status': item['status'],
				'Match_Method': item.get('match_method', ''),
				'Plex_Title': item.get('plex_title', ''),
				'Plex_Year': item.get('plex_year', ''),
				'Notes': item.get('notes', '')
			})

def verify_plex_connection():
	"""Verify connection to Plex server"""
	try:
		plex = PlexServer(PLEX_URL, PLEX_TOKEN)
		log_message(f"Connected to Plex server at {PLEX_URL}")
		return plex
	except Exception as e:
		log_message(f"Failed to connect to Plex server: {str(e)}", message_type="ERROR")
		print(f"\n{Fore.RED}Unable to connect to Plex server. Please verify your URL and token.{Style.RESET_ALL}")
		display_instructions()
		return None

def run_imdb_list():
	initialize_logging()
	report_data = []
	
	# Verify Plex connection
	plex = verify_plex_connection()
	if not plex:
		return []

	# Read local CSV file
	log_message(f"Reading IMDB list from: {CSV_FILE_PATH}")
	try:
		with open(CSV_FILE_PATH, mode='r', encoding='utf-8') as csv_file:
			reader = csv.DictReader(csv_file)
			rows = list(reader)
			url_column = 'URL' if 'URL' in reader.fieldnames else 'url'
			
			log_message(f"Found {len(rows)} movies in the CSV file")
	except Exception as e:
		log_message(f"Error reading CSV file: {str(e)}", message_type="ERROR")
		return []

	# Get all movies from Plex library
	log_message(f"Retrieving movies from Plex library: {MOVIE_LIBRARY_NAME}")
	try:
		movie_library = plex.library.section(MOVIE_LIBRARY_NAME)
		all_movies = movie_library.all()
		log_message(f"Found {len(all_movies)} movies in Plex library")
	except Exception as e:
		log_message(f"Error accessing Plex library: {str(e)}", message_type="ERROR")
		print(f"\n{Fore.RED}Error: Library '{MOVIE_LIBRARY_NAME}' not found. Please check your library name.{Style.RESET_ALL}")
		return []

	# Find existing collection items
	existing_collection_items = find_existing_collection_items(plex, IMDB_COLLECTION_NAME)

	# Create IMDB ID to movie mapping
	imdb_map = {}
	for movie in all_movies:
		if 'imdb://' in movie.guid:
			imdb_id = movie.guid.split('imdb://')[1].split('?')[0]
			imdb_map[imdb_id] = movie

	# Process each movie from CSV in order
	log_message(f"\nStarting collection creation/update for {IMDB_COLLECTION_NAME}")
	added_count = 0
	skipped_count = 0
	missing_count = 0
	
	# First pass - find all matches and create ordered list
	ordered_movies = []
	
	for row in rows:
		imdb_url = row.get(url_column, '')
		imdb_id = find_imdb_id(imdb_url)
		title = row.get('Title', 'Unknown')
		original_title = row.get('Original Title', '')
		year = row.get('Year', '')
		
		report_item = {
			'title': title,
			'year': year,
			'original_title': original_title,
			'imdb_id': imdb_id or '',
			'status': '',
			'plex_title': '',
			'plex_year': '',
			'notes': ''
		}

		if not imdb_id:
			status = "ERROR: No IMDB ID found"
			report_item.update({
				'status': status,
				'notes': f'Invalid URL: {imdb_url}'
			})
			log_message(f"{status} - {title} ({year})", message_type="ERROR")
			missing_count += 1
			report_data.append(report_item)
			continue

		# Try to find movie by IMDB ID first
		movie = imdb_map.get(imdb_id)
		match_method = "IMDB ID" if movie else ""
		
		# If not found by IMDB ID, try title + year
		if not movie:
			movie = find_movie_by_title_year(all_movies, title, year, original_title)
			if movie:
				match_method = "Title + Year Fuzzy Match"
		
		# If still not found, try title only
		if not movie:
			movie = find_movie_by_title(all_movies, title, original_title)
			if movie:
				match_method = "Title Only Fuzzy Match"
				# Verify year isn't too different
				if year and abs(int(movie.year) - int(year)) > 2:
					log_message(f"Rejected title-only match for {title} due to year mismatch (Plex: {movie.year}, CSV: {year})", message_type="WARNING")
					movie = None
		
		if not movie:
			status = "MISSING: Not found in Plex library"
			report_item.update({
				'status': status,
				'notes': 'Could not match by IMDB ID, title+year, or title only'
			})
			log_message(f"{status} - {title} ({year})", message_type="ERROR")
			missing_count += 1
			report_data.append(report_item)
			continue

		# Check if the movie is already in the collection
		already_in_collection = False
		if movie.ratingKey in existing_collection_items:
			already_in_collection = True
		elif imdb_id in existing_collection_items:
			already_in_collection = True

		if already_in_collection:
			status = "SKIPPED:"
			report_item.update({
				'status': status,
				'match_method': match_method,
				'plex_title': movie.title,
				'plex_year': movie.year
			})
			log_message(f"{status} {movie.title} ({movie.year})", message_type="INFO")
			skipped_count += 1
			report_data.append(report_item)
			continue

		# Add to our ordered list for movies not in collection
		ordered_movies.append({
			'movie': movie,
			'report_item': report_item,
			'match_method': match_method,
			'original_position': len(ordered_movies)  # Maintain original order
		})

	# Second pass - add to collection in order
	for item in ordered_movies:
		movie = item['movie']
		report_item = item['report_item']
		match_method = item['match_method']
		
		# Try to add to collection
		success = add_collection(movie.librarySectionID, movie.ratingKey, movie.title)
		if success:
			status = "ADDED:"
			report_item.update({
				'status': status,
				'match_method': match_method,
				'plex_title': movie.title,
				'plex_year': movie.year
			})
			message_type = "SUCCESS" if match_method == "IMDB ID" else "WARNING"
			log_message(f"{status} {movie.title} ({movie.year}) - (matched by {match_method})", message_type=message_type)
			added_count += 1
		else:
			status = "ERROR:"
			report_item.update({
				'status': status,
				'match_method': match_method,
				'plex_title': movie.title,
				'plex_year': movie.year,
				'notes': 'Plex API error'
			})
			log_message(f"{status} {movie.title} ({movie.year})", message_type="ERROR")
			missing_count += 1
		
		report_data.append(report_item)

	# Generate reports
	log_message(f"\nProcessing complete: {Fore.GREEN}{added_count} added{Style.RESET_ALL}, {Fore.YELLOW}{skipped_count} already in collection{Style.RESET_ALL}, {Fore.RED}{missing_count} not found/failed{Style.RESET_ALL}.")
	generate_report(report_data)
	log_message(f"Detailed report saved to: {REPORT_FILE_PATH}")
	log_message(f"Full log saved to: {LOG_FILE_PATH}")

	return report_data

def test_plex_connection():
	"""Test connection to Plex server and validate library name"""
	try:
		plex = PlexServer(PLEX_URL, PLEX_TOKEN)
		print(f"{Fore.GREEN}✓ Successfully connected to Plex server{Style.RESET_ALL}")
		
		# Validate library name
		try:
			library = plex.library.section(MOVIE_LIBRARY_NAME)
			print(f"{Fore.GREEN}✓ Successfully found library: {MOVIE_LIBRARY_NAME} (contains {len(library.all())} items){Style.RESET_ALL}")
			return True
		except Exception as e:
			print(f"{Fore.RED}✗ Library '{MOVIE_LIBRARY_NAME}' not found{Style.RESET_ALL}")
			print(f"{Fore.CYAN}Available libraries:{Style.RESET_ALL}")
			for section in plex.library.sections():
				print(f"  - {section.title}")
			return False
			
	except Exception as e:
		print(f"{Fore.RED}✗ Failed to connect to Plex server: {str(e)}{Style.RESET_ALL}")
		return False

def get_user_input():
	"""Get all required parameters from user if not provided via args"""
	global CSV_FILE_PATH, IMDB_COLLECTION_NAME, PLEX_URL, PLEX_TOKEN, MOVIE_LIBRARY_NAME
	
	# Parse command line arguments
	args = parse_arguments()
	
	# Check if the user just wants instructions
	if args.instructions:
		display_instructions()
		sys.exit(0)
	
	# Load saved config
	config = load_config()
	
	# Get Plex URL
	if args.url:
		PLEX_URL = args.url
	else:
		default_url = config.get('DEFAULT', 'PLEX_URL', fallback='http://127.0.0.1:32400')
		PLEX_URL = input(f"Enter your Plex server URL [Press Enter for {default_url}]: ").strip()
		if not PLEX_URL:
			PLEX_URL = default_url
	
	# Make sure URL has proper format
	if not PLEX_URL.startswith("http"):
		PLEX_URL = "http://" + PLEX_URL
	
	# Get Plex token
	if args.token:
		PLEX_TOKEN = args.token
	else:
		default_token = config.get('DEFAULT', 'PLEX_TOKEN', fallback='')
		PLEX_TOKEN = input(f"Enter your Plex authentication token [Press Enter to use saved token]: ").strip()
		if not PLEX_TOKEN:
			PLEX_TOKEN = default_token
		if not PLEX_TOKEN:
			print(f"{Fore.RED}Plex token is required{Style.RESET_ALL}")
			display_instructions()
			sys.exit(1)
	
	# Get Plex library name
	if args.library:
		MOVIE_LIBRARY_NAME = args.library
	else:
		default_library = config.get('DEFAULT', 'MOVIE_LIBRARY_NAME', fallback='Movies')
		MOVIE_LIBRARY_NAME = input(f"Enter your Plex movie library name [Press Enter for {default_library}]: ").strip()
		if not MOVIE_LIBRARY_NAME:
			MOVIE_LIBRARY_NAME = default_library
	
	# Save the current configuration (only if not using command line args)
	if not (args.url or args.token or args.library):
		save_config(PLEX_URL, PLEX_TOKEN, MOVIE_LIBRARY_NAME)
	
	# Test Plex connection
	print(f"\n{Fore.CYAN}Testing Plex connection...{Style.RESET_ALL}")
	if not test_plex_connection():
		retry = input(f"\n{Fore.YELLOW}Would you like to retry with different Plex settings? (y/n): {Style.RESET_ALL}").lower()
		if retry == 'y':
			PLEX_URL = ""
			PLEX_TOKEN = ""
			MOVIE_LIBRARY_NAME = ""
			get_user_input()
			return
		else:
			print(f"{Fore.RED}Exiting due to Plex connection issues.{Style.RESET_ALL}")
			sys.exit(1)
	
	# Get CSV file path
	if args.csv:
		CSV_FILE_PATH = args.csv
	else:
		while not (CSV_FILE_PATH and os.path.isfile(CSV_FILE_PATH)):
			path = input("\nEnter the path to your IMDB CSV file: ")
			if os.path.isfile(path):
				CSV_FILE_PATH = path
			else:
				print(f"{Fore.RED}File not found: {path}{Style.RESET_ALL}")
				print(f"{Fore.YELLOW}Remember to export a list from IMDB as a CSV file first.{Style.RESET_ALL}")
	
	# Prompt for new or existing collection
	if args.name:
		IMDB_COLLECTION_NAME = args.name
	else:
		# Get existing collections to offer as options
		existing_collections = get_existing_collections()
		
		if existing_collections:
			update_existing = input(f"\n{Fore.CYAN}Would you like to update an existing collection? (y/n): {Style.RESET_ALL}").lower() == 'y'
			
			if update_existing:
				print(f"\n{Fore.CYAN}Available collections:{Style.RESET_ALL}")
				for i, collection in enumerate(existing_collections, 1):
					print(f"{i}. {collection}")
				
				while True:
					choice = input(f"\nEnter the number of the collection to update (or 'n' for new collection): ")
					if choice.lower() == 'n':
						break
					try:
						index = int(choice) - 1
						if 0 <= index < len(existing_collections):
							IMDB_COLLECTION_NAME = existing_collections[index]
							print(f"{Fore.GREEN}Selected collection: {IMDB_COLLECTION_NAME}{Style.RESET_ALL}")
							return
						else:
							print(f"{Fore.RED}Invalid selection. Please try again.{Style.RESET_ALL}")
					except ValueError:
						print(f"{Fore.RED}Please enter a valid number or 'n'.{Style.RESET_ALL}")
		
		# Ask for new collection name
		while not IMDB_COLLECTION_NAME:
			name = input("\nEnter the name for your new collection: ")
			if name.strip():
				IMDB_COLLECTION_NAME = name.strip()
			else:
				print(f"{Fore.RED}Collection name cannot be empty{Style.RESET_ALL}")

if __name__ == "__main__":
	print(f"{Fore.CYAN}=== Plex Collection Creator ==={Style.RESET_ALL}")
	
	# Get user input or command line arguments
	get_user_input()
	
	# Run the script
	run_imdb_list()
	
	print(f"\n{Fore.CYAN}Processing complete. Check the log and report files for details.{Style.RESET_ALL}")
