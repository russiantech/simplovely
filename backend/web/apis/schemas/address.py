address_schema = {
    "type": "object",
    "properties": {
      "first_name": { "type": "string" },
      "last_name": { "type": "string" },
      "zip_code": { "type": "string" },
      "phone_number": { "type": "string" },
      "address": { "type": "string" },
      "city": { "type": "string" },
      "country": { "type": "string" }
    },
    
    "required": ["zip_code", "address", "city"]
    # "required": ["first_name", "last_name", "zip_code", "phone_number", "address", "city", "country"]
  }

country_schema = {
    "type": "object",
    "properties": {
        "geoname_id": { "type": "integer" },
        "name": { "type": "string" },
        "languages": { "type": "string" },
        "iso_numeric": { "type": "string" },
        "code": { "type": "string" },
        "currency": { "type": "string" },
        "currency_symbol": { "type": "string" },
        "logo_url": { "type": "string" },
        "flag_url": { "type": "string" }
    },
    "required": ["geoname_id", "name", "code"]
}

state_schema = {
    "type": "object",
    "properties": {
        "geoname_id": { "type": "integer" },
        "name": { "type": "string" },
        "country_id": { "type": "integer" }
    },
    "required": ["geoname_id", "name", "country_id"]
}

city_schema = {
    "type": "object",
    "properties": {
        "geoname_id": { "type": "integer" },
        "name": { "type": "string" },
        "state_id": { "type": "integer" }
    },
    "required": ["geoname_id", "name", "state_id"]
}
