import traceback
from flask import jsonify, request
from flask_jwt_extended import current_user, jwt_required
import requests
from sqlalchemy import desc
from web.extensions import db
from web.apis import api_bp as address_bp
from web.apis.models.addresses import Country, State, City, Address
from web.apis.utils.serializers import PageSerializer, success_response, error_response
from web.apis.schemas.address import country_schema, state_schema, city_schema, address_schema
from web.extensions import limiter
from jsonschema import validate, ValidationError

# Address API

@address_bp.route('/addresses/<int:address_id>', methods=['GET'])
@address_bp.route('/addresses', methods=['GET'])
@jwt_required()
@limiter.exempt
def list_addresses(address_id=None):
    """List all addresses for the authenticated user or return a specific address."""
    try:
        if address_id is not None:
            # Fetch a single address
            address = Address.query.filter_by(id=address_id, user_id=current_user.id).first()
            if address is None:
                return error_response("Address not found", status_code=404)
            data = address.get_summary(include_user=False)
            return success_response("Address fetched successfully", data=data)

        # Fetch multiple addresses with pagination
        page_size = request.args.get('page_size', 5, type=int)
        page = request.args.get('page', 1, type=int)

        addresses = Address.query.filter_by(user_id=current_user.id).order_by(desc(Address.created_at)).paginate(page=page, per_page=page_size)
        data = PageSerializer(pagination_obj=addresses, resource_name="addresses", include_user=False).get_data()
        return success_response("Addresses fetched successfully", data=data, status_code=201)

    except Exception as e:
        traceback.print_exc()
        return error_response(f"Unexpected error: {str(e)}", status_code=500)

@address_bp.route('/addresses', methods=['POST'])
@jwt_required()
@limiter.exempt
def create_address():
    """Create a new address for the authenticated user."""
    try:
        data = request.json
        validate(instance=data, schema=address_schema)  # Validate the data using JSON schema

        address = Address(
            first_name=data.get('first_name', current_user.name),
            last_name=data.get('last_name', None),
            is_primary=data.get('is_primary') == 'on',  # Correctly handle checkbox input
            zip_code=data.get('zip_code'),
            phone_number=data.get('phone_number'),
            street_address=data.get('address'),
            city_id=data.get('city'),
            user_id=current_user.id
        )

        # Add the address to the session and commit
        db.session.add(address)
        db.session.commit()
        return success_response("Address created successfully.", data=address.get_summary(), status_code=201)

    except ValidationError as e:
        return error_response(f"Validation error: {e.message}", status_code=400)
    except Exception as e:
        return error_response(f"Unexpected error: {str(e)}", status_code=500)

@address_bp.route('/addresses/<int:address_id>', methods=['PUT'])
@jwt_required()
def update_address(address_id):
    """Update an existing address for the authenticated user."""
    try:
        address = Address.query.get_or_404(address_id)

        if address.user_id != current_user.id:
            return error_response("Access forbidden: insufficient permissions.", status_code=403)

        data = request.json
        validate(instance=data, schema=address_schema)

        address.first_name = data.get('first_name', address.first_name)
        address.last_name = data.get('last_name', address.last_name)
        address.zip_code = data.get('zip_code', address.zip_code)
        address.phone_number = data.get('phone_number', address.phone_number)
        address.street_address = data.get('address', address.street_address)
        address.city_id = data.get('city', address.city_id)
        db.session.commit()

        return success_response("Address updated successfully.", data=address.get_summary())

    except ValidationError as e:
        db.session.rollback()
        traceback.print_exc()
        return error_response(f"Validation error: {e.message}", status_code=400)
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return error_response(f"Unexpected error: {str(e)}", status_code=500)

@address_bp.route('/addresses/<int:address_id>', methods=['DELETE'])
@jwt_required(optional=True)
def delete_address(address_id):
    """Delete an existing address for the authenticated user."""
    try:
        address = Address.query.get_or_404(address_id)

        if address.user_id != current_user.id:
            return error_response("Access forbidden: insufficient permissions.", status_code=403)

        db.session.delete(address)
        db.session.commit()
        return success_response("Address deleted successfully.")

    except Exception as e:
        return error_response(f"Unexpected error: {str(e)}", status_code=500)

# Country API

@address_bp.route('/countries', methods=['GET'])
@address_bp.route('/countries/<int:country_id>', methods=['GET'])
@jwt_required(optional=True)
@limiter.exempt
def list_countries(country_id=None):
    """List all countries with pagination."""
    try:
        
        if country_id is not None:
            # Fetch a single country
            country = Country.query.filter_by(id=country_id, user_id=current_user.id).first()
            if country is None:
                return error_response("Address not found", status_code=404)
            data = country.get_summary(include_user=False)
            return success_response("Country fetched successfully", data=data)

        page_size = request.args.get('page_size', 500, type=int)
        page = request.args.get('page', 1, type=int)

        # Fetch countries with pagination
        countries = Country.query.order_by(Country.name).paginate(page=page, per_page=page_size)
        data = PageSerializer(pagination_obj=countries, resource_name="countries").get_data()

        return success_response("Countries fetched successfully.", data=data)

    except Exception as e:
        traceback.print_exc()
        return error_response(f"Unexpected error: {str(e)}", status_code=500)

@address_bp.route('/countries', methods=['POST'])
@jwt_required()
def create_country():
    """Create a new country."""
    try:
        data = request.json
        validate(instance=data, schema=country_schema)

        country = Country(name=data['name'])
        db.session.add(country)
        db.session.commit()
        return success_response("Country created successfully.", data=country.get_summary(), status_code=201)

    except ValidationError as e:
        return error_response(f"Validation error: {e.message}", status_code=400)
    except Exception as e:
        return error_response(f"Unexpected error: {str(e)}", status_code=500)

@address_bp.route('/countries/<int:country_id>', methods=['PUT'])
@jwt_required()
def update_country(country_id):
    """Update an existing country."""
    try:
        country = Country.query.get_or_404(country_id)

        data = request.json
        validate(instance=data, schema=country_schema)

        country.name = data.get('name', country.name)
        db.session.commit()

        return success_response("Country updated successfully.", data=country.get_summary())

    except ValidationError as e:
        return error_response(f"Validation error: {e.message}", status_code=400)
    except Exception as e:
        return error_response(f"Unexpected error: {str(e)}", status_code=500)

@address_bp.route('/countries/<int:country_id>', methods=['DELETE'])
@jwt_required()
def delete_country(country_id):
    """Delete an existing country."""
    try:
        country = Country.query.get_or_404(country_id)
        db.session.delete(country)
        db.session.commit()
        return success_response("Country deleted successfully.")

    except Exception as e:
        return error_response(f"Unexpected error: {str(e)}", status_code=500)

# State API
@address_bp.route('/states/<int:country_id>/countries', methods=['GET'])
@jwt_required(optional=True)
@limiter.exempt
def states_by_country(country_id):
    """List all states by country with pagination."""
    try:
        
        if country_id is not None:

            page_size = request.args.get('page_size', 50, type=int)
            page = request.args.get('page', 1, type=int)

            # Fetch states with pagination
            # states = State.query.order_by(State.name).paginate(page=page, per_page=page_size)
            states = State.query.filter_by(country_id=country_id).order_by(State.name).paginate(page=page, per_page=page_size)
            if states is None:
                return error_response(f"No state(s) found for {country_id}", status_code=404)
            data = PageSerializer(items=states.items, resource_name="states").get_data()
            # data = PageSerializer(pagination_obj=states, resource_name="states", context_id=country_id).get_data()

            return success_response(f"States fetched for {country_id} successfully.", data=data)
        
        return error_response("Country ID required to fetch it's states.")

    except Exception as e:
        traceback.print_exc()
        return error_response(f"err > {str(e)}", status_code=500)

@address_bp.route('/states', methods=['GET'])
@jwt_required()
def list_states():
    """List all states."""
    try:
        states = State.query.all()
        data = [state.get_summary() for state in states]
        return success_response("States fetched successfully.", data=data)

    except Exception as e:
        return error_response(f"Unexpected error: {str(e)}", status_code=500)

@address_bp.route('/states', methods=['POST'])
@jwt_required()
def create_state():
    """Create a new state."""
    try:
        data = request.json
        validate(instance=data, schema=state_schema)

        state = State(name=data['name'], country_id=data['country_id'])
        db.session.add(state)
        db.session.commit()
        return success_response("State created successfully.", data=state.get_summary(), status_code=201)

    except ValidationError as e:
        return error_response(f"Validation error: {e.message}", status_code=400)
    except Exception as e:
        return error_response(f"Unexpected error: {str(e)}", status_code=500)

@address_bp.route('/states/<int:state_id>', methods=['PUT'])
@jwt_required()
def update_state(state_id):
    """Update an existing state."""
    try:
        state = State.query.get_or_404(state_id)

        data = request.json
        validate(instance=data, schema=state_schema)

        state.name = data.get('name', state.name)
        state.country_id = data.get('country_id', state.country_id)
        db.session.commit()

        return success_response("State updated successfully.", data=state.get_summary())

    except ValidationError as e:
        return error_response(f"Validation error: {e.message}", status_code=400)
    except Exception as e:
        return error_response(f"Unexpected error: {str(e)}", status_code=500)

@address_bp.route('/states/<int:state_id>', methods=['DELETE'])
@jwt_required()
def delete_state(state_id):
    """Delete an existing state."""
    try:
        state = State.query.get_or_404(state_id)
        db.session.delete(state)
        db.session.commit()
        return success_response("State deleted successfully.")

    except Exception as e:
        return error_response(f"Unexpected error: {str(e)}", status_code=500)

# City API
@address_bp.route('/cities/<int:state_id>/states', methods=['GET'])
@jwt_required(optional=True)
@limiter.exempt
def cities_by_states(state_id):
    """List all ctities by state with pagination."""
    try:
        
        if state_id is not None:

            page_size = request.args.get('page_size', 50, type=int)
            page = request.args.get('page', 1, type=int)

            # Fetch cities by state id with pagination
            cities = City.query.filter_by(state_id=state_id).order_by(City.name).paginate(page=page, per_page=page_size)
            if cities is None:
                return error_response(f"No state(s) found for {state_id}", status_code=404)
            data = PageSerializer(items=cities.items, resource_name="cities").get_data()
            
            return success_response(f"Cities fetched for {state_id} successfully.", data=data)
        
        return error_response("State ID required to fetch it's cities.")

    except Exception as e:
        traceback.print_exc()
        return error_response(f"err > {str(e)}", status_code=500)


@address_bp.route('/cities', methods=['GET'])
@jwt_required()
def list_cities():
    """List all cities."""
    try:
        cities = City.query.all()
        data = [city.get_summary() for city in cities]
        return success_response("Cities fetched successfully.", data=data)

    except Exception as e:
        return error_response(f"Unexpected error: {str(e)}", status_code=500)

@address_bp.route('/cities', methods=['POST'])
@jwt_required()
def create_city():
    """Create a new city."""
    try:
        data = request.json
        validate(instance=data, schema=city_schema)

        city = City(name=data['name'], state_id=data['state_id'])
        db.session.add(city)
        db.session.commit()
        return success_response("City created successfully.", data=city.get_summary(), status_code=201)

    except ValidationError as e:
        return error_response(f"Validation error: {e.message}", status_code=400)
    except Exception as e:
        return error_response(f"Unexpected error: {str(e)}", status_code=500)

@address_bp.route('/cities/<int:city_id>', methods=['PUT'])
@jwt_required()
def update_city(city_id):
    """Update an existing city."""
    try:
        city = City.query.get_or_404(city_id)

        data = request.json
        validate(instance=data, schema=city_schema)

        city.name = data.get('name', city.name)
        city.state_id = data.get('state_id', city.state_id)
        db.session.commit()

        return success_response("City updated successfully.", data=city.get_summary())

    except ValidationError as e:
        return error_response(f"Validation error: {e.message}", status_code=400)
    except Exception as e:
        return error_response(f"Unexpected error: {str(e)}", status_code=500)

@address_bp.route('/cities/<int:city_id>', methods=['DELETE'])
@jwt_required()
def delete_city(city_id):
    """Delete an existing city."""
    try:
        city = City.query.get_or_404(city_id)
        db.session.delete(city)
        db.session.commit()
        return success_response("City deleted successfully.")

    except Exception as e:
        return error_response(f"Unexpected error: {str(e)}", status_code=500)

#
# @address_bp.route('/fetch_data', methods=['GET'])
# def fetch_data():
#     try:
#         # Fetch country data
#         country_response = requests.get('https://restcountries.com/v3.1/all')
#         countries = country_response.json()

#         for country in countries:
#             country_instance = Country(
#                 name=country['name']['common'],
#                 code=country['cca2'],
#                 currency=country['currencies'][list(country['currencies'].keys())[0]]['name'],
#                 currency_symbol=country['currencies'][list(country['currencies'].keys())[0]]['symbol'],
#                 logo_url=country['flags']['png'],
#                 flag_url=country['flags']['svg']
#             )
#             db.session.add(country_instance)
#             db.session.commit()

#             # Fetch states and cities (assuming you have a state API)
#             state_response = requests.get(f'https://api.example.com/states?country_code={country["cca2"]}')
#             states = state_response.json()

#             for state in states:
#                 state_instance = State(
#                     name=state['name'],
#                     country_id=country_instance.id
#                 )
#                 db.session.add(state_instance)
#                 db.session.commit()

#                 # Fetch cities for the state (assuming you have a city API)
#                 city_response = requests.get(f'https://api.example.com/cities?state_id={state["id"]}')
#                 cities = city_response.json()

#                 for city in cities:
#                     city_instance = City(
#                         name=city['name'],
#                         state_id=state_instance.id
#                     )
#                     db.session.add(city_instance)

#             db.session.commit()

#         return success_response("Data fetched and stored successfully!")

#     except Exception as e:
#         db.session.rollback()
#         return error_response(str(e))


# @address_bp.route('/fetch_data', methods=['GET'])
# def fetch_data():
#     try:
#         # Fetch country data
#         country_response = requests.get('https://restcountries.com/v3.1/all')
#         countries = country_response.json()

#         for country in countries:
#             # Check if the country already exists
#             existing_country = Country.query.filter_by(name=country['name']['common']).first()
#             if existing_country:
#                 continue  # Skip if the country already exists

#             country_instance = Country(
#                 name=country['name']['common'],
#                 code=country['cca2'],
#                 currency=country['currencies'][list(country['currencies'].keys())[0]]['name'],
#                 currency_symbol=country['currencies'][list(country['currencies'].keys())[0]]['symbol'],
#                 logo_url=country['flags']['png'],
#                 flag_url=country['flags']['svg']
#             )
#             db.session.add(country_instance)
#             db.session.commit()

#             # Fetch states for the country from GeoNames
#             state_response = requests.get(f'http://api.geonames.org/childrenJSON?geonameId={country["geonameId"]}&username=edet')
#             states = state_response.json().get('geonames', [])

#             for state in states:
#                 state_instance = State(
#                     name=state['name'],
#                     country_id=country_instance.id
#                 )
#                 db.session.add(state_instance)
#                 db.session.commit()

#                 # Fetch cities for the state from GeoNames
#                 city_response = requests.get(f'http://api.geonames.org/childrenJSON?geonameId={state["geonameId"]}&username=edet')
#                 cities = city_response.json().get('geonames', [])

#                 for city in cities:
#                     city_instance = City(
#                         name=city['name'],
#                         state_id=state_instance.id
#                     )
#                     db.session.add(city_instance)

#             db.session.commit()

#         return jsonify({"message": "Data fetched and stored successfully!"}), 200

#     except Exception as e:
#         db.session.rollback()
#         return jsonify({"error": str(e)}), 500

# import requests

# @address_bp.route('/fetch_data', methods=['GET'])
# def fetch_data():
#     try:
#         # Fetch countries from GeoNames
#         country_response = requests.get('http://api.geonames.org/countryInfoJSON?username=edet')
#         countries = country_response.json().get('geonames', [])

#         for country in countries:
#             existing_country = Country.query.filter_by(name=country['countryName']).first()
#             if existing_country:
#                 continue  # Skip if the country already exists

#             country_instance = Country(
#                 name=country['countryName'],
#                 geoname_id=country['geonameId'],
#                 code=country['countryCode'],
#                 languages=country['languages'],
#                 iso_numeric=country['isoNumeric'],
#                 # currency=country['currency'],
#                 currency_symbol=country['currencySymbol'],  # Adjust as needed
#                 logo_url=f"https://flagcdn.com/w320/{country['countryCode'].lower()}.png",
#                 flag_url=f"https://flagcdn.com/{country['countryCode'].lower()}.svg"
#             )
#             db.session.add(country_instance)
#             db.session.commit()

#             # Fetch states for the country
#             state_response = requests.get(f'http://api.geonames.org/childrenJSON?geonameId={country["geonameId"]}&username=edet')
#             states = state_response.json().get('geonames', [])

#             for state in states:
#                 state_instance = State(
#                     name=state['name'],
#                     country_id=country_instance.id
#                 )
#                 db.session.add(state_instance)
#                 db.session.commit()

#                 # Fetch cities for the state
#                 city_response = requests.get(f'http://api.geonames.org/childrenJSON?geonameId={state["geonameId"]}&username=edet')
#                 cities = city_response.json().get('geonames', [])

#                 for city in cities:
#                     city_instance = City(
#                         name=city['name'],
#                         state_id=state_instance.id
#                     )
#                     db.session.add(city_instance)

#             db.session.commit()

#         return jsonify({"message": "Data fetched and stored successfully!"}), 200

#     except Exception as e:
#         db.session.rollback()
#         traceback.print_exc()
#         return jsonify({"error": str(e)}), 500


import requests
@address_bp.route('/fetch_data', methods=['GET'])
def fetch_data():
    try:
        # Fetch countries from GeoNames
        country_response = requests.get('http://api.geonames.org/countryInfoJSON?username=EDET')
        countries = country_response.json().get('geonames', [])

        for country in countries:
            existing_country = Country.query.filter_by(name=country['countryName']).first()
            if existing_country:
                continue  # Skip if the country already exists

            # Get currency and handle missing key
            currency = country.get('currency', 'N/A')  # Default value if currency not found
            currency_symbol = country.get('currencyCode', 'N/A')  # Default value if currency symbol not found

            country_instance = Country(
                name=country['countryName'],
                geoname_id=country['geonameId'],
                code=country['countryCode'],
                languages=country['languages'],
                iso_numeric=country['isoNumeric'],
                currency=currency,
                currency_symbol=currency_symbol,
                logo_url=f"https://flagcdn.com/w320/{country['countryCode'].lower()}.png",
                flag_url=f"https://flagcdn.com/{country['countryCode'].lower()}.svg"
            )

            db.session.add(country_instance)
            db.session.commit()

            # Fetch states for the country
            state_response = requests.get(f'http://api.geonames.org/childrenJSON?geonameId={country["geonameId"]}&username=EDET')
            states = state_response.json().get('geonames', [])

            for state in states:
                state_instance = State(
                    name=state['name'],
                    country_id=country_instance.id
                )
                db.session.add(state_instance)
                db.session.commit()

                # Fetch cities for the state
                city_response = requests.get(f'http://api.geonames.org/childrenJSON?geonameId={state["geonameId"]}&username=EDET')
                cities = city_response.json().get('geonames', [])

                for city in cities:
                    city_instance = City(
                        name=city['name'],
                        state_id=state_instance.id
                    )
                    db.session.add(city_instance)

            db.session.commit()

        return jsonify({"message": "Data fetched and stored successfully!"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# 

# Fetch States
# def fetch_states(country_geoname_id):
#     url = f"http://api.geonames.org/childrenJSON?geonameId={country_geoname_id}&username=edet"
#     response = requests.get(url)
#     if response.status_code == 200:
#         return response.json().get('geonames', [])
#     return []

# # Save States
# def save_states(country_id, states):
#     for state in states:
#         existing_state = State.query.filter_by(geoname_id=state['geonameId']).first()
#         if existing_state:
#             continue  # Skip if the state already exists
#         new_state = State(
#             name=state['name'],
#             country_id=country_id,
#             geoname_id=state['geonameId']
#         )
#         db.session.add(new_state)
#     db.session.commit()

# # Fetch Cities
# def fetch_cities(state_geoname_id):
#     url = f"http://api.geonames.org/childrenJSON?geonameId={state_geoname_id}&username=edet"
#     response = requests.get(url)
#     if response.status_code == 200:
#         return response.json().get('geonames', [])
#     return []

# # Save Cities
# def save_cities(state_id, cities):
#     for city in cities:
#         existing_city = City.query.filter_by(geoname_id=city['geonameId']).first()
#         if existing_city:
#             continue  # Skip if the city already exists
#         new_city = City(
#             name=city['name'],
#             state_id=state_id,
#             geoname_id=city['geonameId']
#         )
#         db.session.add(new_city)
#     db.session.commit()

# # Automate Population
# def automate_population():
#     countries = Country.query.all()
#     for country in countries:
#         states = fetch_states(country.geoname_id)
#         save_states(country.id, states)
        
#         for state in states:
#             cities = fetch_cities(state['geonameId'])
#             save_cities(state['id'], cities)

# @app.route('/populate', methods=['POST'])
# def populate():
#     automate_population()
#     return jsonify({"message": "Population of states and cities completed."})

# 

import requests

# Fetch states by country's Geoname ID
def fetch_states(country_geoname_id):
    url = f"http://api.geonames.org/childrenJSON?geonameId={country_geoname_id}&username=edet"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('geonames', [])
    return []

# Fetch cities by state's Geoname ID
def fetch_cities(state_geoname_id):
    url = f"http://api.geonames.org/childrenJSON?geonameId={state_geoname_id}&username=edet"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('geonames', [])
    return []

# Save states with their Geoname IDs, avoiding duplicates
def save_states(country_id, states):
    for state in states:
        existing_state = State.query.filter_by(name=state['name'], country_id=country_id).first()
        if existing_state:
            # Update geoname_id if it is missing
            if not existing_state.geoname_id:
                existing_state.geoname_id = state['geonameId']
            continue  # Skip if the state already exists
        new_state = State(
            name=state['name'],
            country_id=country_id,
            geoname_id=state['geonameId']
        )
        db.session.add(new_state)
    db.session.commit()

# Save cities with their Geoname IDs, avoiding duplicates
def save_cities(state_id, cities):
    for city in cities:
        existing_city = City.query.filter_by(name=city['name'], state_id=state_id).first()
        if existing_city:
            # Update geoname_id if it is missing
            if not existing_city.geoname_id:
                existing_city.geoname_id = city['geonameId']
            continue  # Skip if the city already exists
        new_city = City(
            name=city['name'],
            state_id=state_id,
            geoname_id=city['geonameId']
        )
        db.session.add(new_city)
    db.session.commit()

# # Automate the population of states and cities
# def automate_population():
#     countries = Country.query.all()
#     for country in countries:
#         states = fetch_states(country.geoname_id)
#         save_states(country.id, states)
        
#         for state in states:
#             cities = fetch_cities(state['geonameId'])
#             save_cities(state['id'], cities)

def automate_population():
    countries = Country.query.all()
    for country in countries:
        states = fetch_states(country.geoname_id)
        save_states(country.id, states)
        
        for state in states:
            # Assuming you've saved the state and can query it back
            existing_state = State.query.filter_by(name=state['name'], country_id=country.id).first()
            if existing_state:
                cities = fetch_cities(state['geonameId'])
                save_cities(existing_state.id, cities)


@address_bp.route('/populate', methods=['GET'])
def populate():
    automate_population()
    return jsonify({"message": "Population of states and cities completed."})
