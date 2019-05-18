from flask import Flask,request,jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Football123*@localhost/apitest'
db = SQLAlchemy(app)
ma = Marshmallow(app)


class Places(db.Model):
    """docstring for Place."""
    __tablename__ = 'places'

    key = db.Column(db.String(20), primary_key=True)
    place_name = db.Column(db.String(180))
    admin_name1 = db.Column(db.String(100))
    latitude = db.Column(db.Numeric(9,6))
    longitude = db.Column(db.Numeric(9,6))
    accuracy = db.Column(db.Integer)


    def __init__(self, latitude, longitude,key,place_name,admin_name1):
        # super(Place, self).__init__()
        self.latitude = latitude
        self.longitude = longitude
        self.key = key
        self.place_name = place_name
        self.admin_name1 = admin_name1

# API to create new location
@app.route("/post_location", methods=["POST"])
def add_location():
    latitude = request.json['lat']
    longitude = request.json['long']
    address = request.json['address'].split("+")
    if len(address) != 3:
        return "Invalid Address"
    key = address[0]
    place_name = address[1]
    city = address[2]

    exists = db.session.query(Places.key).filter_by(key=key).scalar() is not None
    if exists:
        return "pincode exists"

    # Check for existing close enough lat+long

    new_location = Places(latitude, longitude, key,place_name,city)

    db.session.add(new_location)
    db.session.commit()

    return jsonify({'key':key,'place_name':place_name,'city':city, 'address':'added'})

# API to fetch nearby points
@app.route("/get_using_postgres", methods=["GET"])
def get_using_postgres():
    latitude = request.json['lat']
    longitude = request.json['long']
    radius = request.json['radius']

    # SELECT events.id, events.name FROM events WHERE earth_box( {current_user_lat}, {current_user_lng}, {radius_in_metres}) @> ll_to_earth(events.lat, events.lng);
    points = db.session.query(places.latitude, Places.longitude).filter_by(earth_box( latitude, longitude, radius) @> ll_to_earth(Places.latitude, Places.longitude))
    return json.dumps(points)


@app.route("/")
def home():
    return "Hello World!"

if __name__ == "__main__":
    app.run(debug=True)
