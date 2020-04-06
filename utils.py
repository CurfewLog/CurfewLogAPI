import requests
from datetime import datetime, timedelta
import pytz
import json
from bs4 import BeautifulSoup

covid_data = None

def get_city_by_coordinates(lat, lng):
	url = 'https://nominatim.openstreetmap.org/reverse'
	params = {'lat': lat, 'lon': lng, 'format': 'json'}
	# sending reverse geocoding request
	request = requests.get(url=url, params=params)
	result = request.json()
	# getting city
	address = result['address']
	if address['country_code'] == 'in':
		city = address['state_district']
	else:
		city = address['city']

	return city

def get_date():
	date_now = datetime.now(pytz.timezone('Asia/Kolkata'))
	today = date_now.strftime('%A')
	return {'day': date_now.day, 'month': date_now.strftime('%B'), 'year': date_now.year, 'weekday': today}

def get_covid_cases():
	global covid_data
	if covid_data is not None and \
		covid_data['last_update_time'] > datetime.now() - timedelta(hours=1):
		# don't think it changes to often , could change the timedelta to be shorter or longer if needed
		return covid_data['data']
	# scraping from mohfw
	url = 'https://www.mohfw.gov.in/'
	page = requests.get(url)
	soup = BeautifulSoup(page.content, 'html.parser')
	# getting the correct elements
	div = soup.find('div', attrs={'class': 'site-stats-count'})
	stats = div.findAll('strong')
	# getting no of cases
	active_cases = stats[0].string
	recovered_cases = stats[1].string
	deceased_cases = stats[2].string
	data = {"active": active_cases, "recovered": recovered_cases, "deceased": deceased_cases}
	covid_data = { 'data': data, "last_update_time": datetime.now() }
	return data
