from flask import Flask, request
import datetime
import pytz
import json
import uuid
from pymongo import MongoClient
from utils import get_city_by_coordinates, get_covid_cases, get_date

app = Flask(__name__)
# for local debug
# client = MongoClient()

# production on MongoDB Atlas
client = MongoClient("YOUR-MONGODB-ADDRESS-HERE")
db = client.curfewlog

@app.route('/ping')
def ping():
	return 'PONG'

@app.route('/v1/get-summary', methods=['GET'])
def get_date_and_covid_cases():
	return json.dumps({'date': get_date(), 'covid_cases': get_covid_cases()})

@app.route('/v1/add-user', methods=['POST'])
def add_new_user():
	email = request.json['email']
	name = request.json['name']

	if db.users.find({'email': email}).count() == 0:
		user_id = get_unique_user_id()
		# adding user to db
		result = db.users.insert({'user_id': user_id, 'email': email, 'name': name})
		if result is not None:
			return json.dumps({'status': 'success'})
		else:
			return json.dumps({'status': 'error'})
	else:
		return json.dumps({'status': 'success'})

@app.route('/v1/get-user-requests', methods=['POST'])
def get_requests_by_email():
	email = request.json['email']
	user = db.users.find_one({'email': email})
	if user is None: 
		return json.dumps({'status': 'error'})
	else:

		user_id = user['user_id']
		# getting requests by userid
		visit_requests = db.requests.find({'user_id': user_id})
		if visit_requests is None:
			visit_requests = []
		else:
			visit_requests = list(visit_requests)
		
		# checking for active and recent visits
		date_now = datetime.datetime.now(pytz.timezone('Asia/Kolkata'))
		date_tomorrow = date_now + datetime.timedelta(days=1)
		today_date = datetime.datetime(date_now.year, date_now.month, date_now.day)
		tomorrow_date = datetime.datetime(date_tomorrow.year, date_tomorrow.month, date_tomorrow.day)

		active_visit = None
		past_visits = []
		for visit in reversed(visit_requests):
			del visit['_id']  # cannot serialize this
			visit_date = datetime.datetime.strptime(visit['visit_date'], '%d/%m/%Y')
			# creating date object
			visit['visit_date'] = {'day': visit_date.day, 'month': visit_date.strftime('%B'), 'year': visit_date.year}
			# checking if active visit
			if visit_date >= today_date and active_visit is None:

				# creating active visit item
				active_visit = visit
				# getting visit day of week
				if visit_date == today_date:
					visit_day = 'Today'
				elif visit_date == tomorrow_date:
					visit_day = 'Tomorrow'
				else:
					visit_day = visit_date.strftime('%A')
				active_visit['visit_date']['weekday'] = visit_day

			# getting past visits
			elif visit_date <= today_date:
				# getting days ago
				diff = today_date - visit_date
				visit['days_ago'] = diff.days
				past_visits.append(visit)

		past_visits = sorted(past_visits, key=lambda k: k['days_ago'])

		return json.dumps({'status': 'success', 'active_request': active_visit, 'past_requests': past_visits})

@app.route('/v1/get-city-requests', methods=['POST'])
def get_requests_by_location():
	coordinates = request.json['coordinates']
	request_lat = coordinates[0]
	request_long = coordinates[1]
	city = get_city_by_coordinates(request_lat, request_long)
	# getting all requests in the location
	visit_requests = db.requests.find({'city': city, 'status': 'pending'})

	if visit_requests is None:
		visit_requests = []
	else:
		visit_requests = list(visit_requests)
	
	# checking for active and recent visits
	date_now = datetime.datetime.now(pytz.timezone('Asia/Kolkata'))
	date_tomorrow = date_now + datetime.timedelta(days=1)
	today_date = datetime.datetime(date_now.year, date_now.month, date_now.day)
	tomorrow_date = datetime.datetime(date_tomorrow.year, date_tomorrow.month, date_tomorrow.day)

	active_visits = []
	for visit in reversed(visit_requests):
		visit_date = datetime.datetime.strptime(visit['visit_date'], '%d/%m/%Y')
		# creating date object
		visit['visit_date'] = {'day': visit_date.day, 'month': visit_date.strftime('%B'), 'year': visit_date.year}

		last_user_request = list(db.requests.find({'user_id': visit['user_id']}))[-1]

		# checking if active visit
		if visit_date >= today_date and visit['request_id'] == last_user_request['request_id']:
			# getting visit day of week
			if visit_date == today_date:
				visit_day = 'Today'
			elif visit_date == tomorrow_date:
				visit_day = 'Tomorrow'
			else:
				visit_day = visit_date.strftime('%A')
			visit['visit_date']['weekday'] = visit_day
			# getting user details
			user = db.users.find_one({'user_id': visit['user_id']})
			visit['user'] = {'name': user['name'], 'email': user['email']}
			# adding visit
			del visit['_id']
			active_visits.append(visit)
		
	return json.dumps({'status': 'success', 'active_requests': active_visits})


@app.route('/v1/new-request', methods=['POST'])
def create_new_request():
	# creating request id
	request_id = get_unique_request_id()
	# getting params from request
	email = request.json['email']
	visit_day = request.json['visit_day']
	visit_place = request.json['visit_place']
	note = request.json['note']
	purpose = request.json['purpose']
	coordinates = request.json['coordinates']
	request_lat = coordinates[0]
	request_long = coordinates[1]
	city = get_city_by_coordinates(request_lat, request_long)
	created_at = datetime.datetime.now(pytz.timezone('Asia/Kolkata')).timestamp()

	# getting actual date
	today = datetime.datetime.now(pytz.timezone('Asia/Kolkata'))
	if visit_day.lower() == 'today':
		date = today.strftime('%d/%m/%Y')
	else:
		tomorrow = today + datetime.timedelta(days=1)
		date = tomorrow.strftime('%d/%m/%Y')

	if not note or note is None:
		note = '---'

	# getting userId
	user = db.users.find_one({'email': email})
	if user is None: 
		return json.dumps({'status': 'error'})
	else:
		user_id = user['user_id']

		# inserting request to db
		new_request = db.requests.insert_one({
			'request_id': request_id,
			'user_id': user_id,
			'status': 'pending',
			'visit_date': date,
			'visit_place': visit_place,
			'purpose': purpose,
			'note': note,
			'coordinates': coordinates,
			'city': city,
			'created_at': created_at
		})

		if new_request is not None:
			return json.dumps({'status': 'success'})
		else:
			return json.dumps({'status': 'error'})

@app.route('/v1/update-request', methods=['POST'])
def change_request_status():
	request_id = request.json['request_id']
	status = request.json['status'].lower()

	task = db.requests.update_one({'request_id': request_id}, {'$set': {'status': status}})
	if task is not None:
		return json.dumps({'status': 'success'})
	else:
		return json.dumps({'status': 'error'})


# id functions

def get_unique_user_id():
	user_id = uuid.uuid4().hex
	if db.users.find({'user_id': user_id}).count() > 0:
		return get_unique_user_id()
	else:
		return user_id

def get_unique_request_id():
	request_id = uuid.uuid4().hex
	if db.requests.find({'request_id': request_id}).count() > 0:
		get_unique_request_id()
	else:
		return request_id


if __name__ == '__main__':
		app.run(debug=True)
