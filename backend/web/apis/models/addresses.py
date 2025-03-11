from flask_jwt_extended import current_user
from sqlalchemy import func
from web.extensions import db

# class Country(db.Model):
#     __tablename__ = 'countries'
#     id = db.Column(db.Integer, primary_key=True)
#     geoname_id = db.Column(db.Integer, unique=True)
#     name = db.Column(db.String(140), nullable=False, unique=True)
#     languages = db.Column(db.String(255))
#     iso_numeric = db.Column(db.String(10), unique=True)
#     code = db.Column(db.String(10), unique=True, nullable=False)
#     currency = db.Column(db.String(50))
#     currency_symbol = db.Column(db.String(10), nullable=True)
#     logo_url = db.Column(db.String(255), nullable=True)
#     flag_url = db.Column(db.String(255), nullable=True)
#     states = db.relationship('State', backref='country', lazy=True)
    
#     created_at = db.Column(db.DateTime, index=True, nullable=False, default=func.now())

#     def get_summary(self, include_states=False):
#         data = {
#             'id': self.id,
#             'name': self.name,
#             'is_selected': True if current_user and self.id == current_user.addresses.city.states.country.id else False, # <-----determine if a user selected this as a country before or not------>
#             'created_at': self.created_at
#         }
#         if include_states:
#             data['states'] = [state.get_summary() for state in self.states]
#         return data

class Country(db.Model):
    __tablename__ = 'countries'
    id = db.Column(db.Integer, primary_key=True)
    geoname_id = db.Column(db.Integer, unique=True)
    name = db.Column(db.String(140), nullable=False, unique=True)
    languages = db.Column(db.String(255))
    iso_numeric = db.Column(db.String(10), unique=True)
    code = db.Column(db.String(10), unique=True, nullable=False)
    currency = db.Column(db.String(50))
    currency_symbol = db.Column(db.String(10), nullable=True)
    logo_url = db.Column(db.String(255), nullable=True)
    flag_url = db.Column(db.String(255), nullable=True)
    states = db.relationship('State', backref='country', lazy=True)
    created_at = db.Column(db.DateTime, index=True, nullable=False, default=func.now())

    def get_summary(self, include_states=False):
        # Determine if the user has selected this country before
        is_selected = False
        if current_user and current_user.addresses:
            for address in current_user.addresses:
                if address.city and address.city.state and address.city.state.country.id == self.id:
                    is_selected = True
                    break

        data = {
            'id': self.id,
            'name': self.name,
            'is_selected': is_selected,
            'created_at': self.created_at
        }
        
        if include_states:
            data['states'] = [state.get_summary() for state in self.states]
        
        return data

class State(db.Model):
    __tablename__ = 'states'

    id = db.Column(db.Integer, primary_key=True)
    geoname_id = db.Column(db.Integer, unique=True)
    name = db.Column(db.String(140), nullable=False)
    country_id = db.Column(db.Integer, db.ForeignKey('countries.id'), nullable=False)
    cities = db.relationship('City', backref='state', lazy=True)

    created_at = db.Column(db.DateTime, index=True, nullable=False, default=func.now())

    def get_summary(self, include_cities=False):
        data = {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at
        }
        if include_cities:
            data['cities'] = [city.get_summary() for city in self.cities]
        return data

class City(db.Model):
    __tablename__ = 'cities'

    id = db.Column(db.Integer, primary_key=True)
    geoname_id = db.Column(db.Integer, unique=True)
    name = db.Column(db.String(140), nullable=False)
    state_id = db.Column(db.Integer, db.ForeignKey('states.id'), nullable=False)

    created_at = db.Column(db.DateTime, index=True, nullable=False, default=func.now())

    def get_summary(self):
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at
        }

class Address(db.Model):
    __tablename__ = 'addresses'

    id = db.Column(db.Integer, primary_key=True)
    
    first_name = db.Column(db.String(140), nullable=False)
    last_name = db.Column(db.String(140))
    street_address = db.Column(db.String(140), nullable=False)
    zip_code = db.Column(db.String(20))
    phone_number = db.Column(db.String(20), nullable=True)
    
    city_id = db.Column(db.Integer, db.ForeignKey('cities.id'), nullable=False)
    city = db.relationship('City', backref='addresses')

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    user = db.relationship('User', backref='addresses')

    is_primary = db.Column(db.Boolean(), nullable=False, default=False)
    is_deleted = db.Column(db.Boolean(), nullable=False, default=False)
    created_at = db.Column(db.DateTime, index=True, nullable=False, default=func.now())
    updated_at = db.Column(db.DateTime, nullable=False, default=func.now(), onupdate=func.now())

    def get_summary(self, include_user=False):
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'is_primary': self.is_primary,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'street_address': self.street_address,
            'zip_code': self.zip_code,
            'city': self.city.name,
            'state': self.city.state.name,
            'country': self.city.state.country.name,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

        if include_user and self.user:
            data['user'] = {'id': self.user_id, 'username': self.user.username}

        return data
