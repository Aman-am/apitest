from flask import Flask,request,jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
import json, datetime, decimal
from sqlalchemy import func

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:qwerty*@localhost/apitest'
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

    def __repr__(self):
        """"""
        return "<Place - '%s': '%s' - '%s'>" % (self.key, self.place_name, self.admin_name1)


class PlacesSchema(ma.ModelSchema):
    class Meta:
        model = Places


def alchemyencoder(obj):
    """JSON encoder function for SQLAlchemy special classes."""
    if isinstance(obj, datetime.date):
        return obj.isoformat()
    elif isinstance(obj, decimal.Decimal):
        return float(obj)


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

    new_framework = db.session.query(Places).filter_by(key =new_location.key, place_name = new_location.place_name, admin_name1 = new_location.admin_name1 ).all()
    places_schema = PlacesSchema(many= True)
    #print schema
    output = places_schema.dump(new_framework).data
    output = json.dumps({'Place': output}, default=alchemyencoder)
    j = output.replace('"[', '[').replace(']"', ']')

    return (json.dumps(json.loads(j), indent=2))


# API to fetch nearby points
@app.route("/get_using_postgres", methods=["GET"])
def get_using_postgres():
    try:
        lat = request.json['lat']
        long = request.json['long']
        radius = request.json['radius']
    except:
        return "Please send Lat, Long and Radius"

    # SELECT * FROM public.places WHERE earth_box( ll_to_earth(106.332, 106.331), 5000) @> ll_to_earth(places.latitude, places.longitude);
    loc_given = func.earth_box(func.ll_to_earth(lat, long ), radius)
    loc_test = func.ll_to_earth(Places.latitude, Places.longitude)
    result = Places.query.filter(loc_given.op("@>")(loc_test))
    place_schema = PlacesSchema(many=True)
    output = place_schema.dump(result).data
    output = json.dumps({'place': output}, default=alchemyencoder)
    # j = output.replace('"[', '[').replace(']"', ']')

    return (json.dumps(json.loads(output), indent=2))

@app.route("/")
def home():
    return "Hello World!"

if __name__ == "__main__":
    app.run(debug=True)
