from flask import Flask,request,jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
import json, datetime, decimal
from sqlalchemy import func
from math import radians, cos, sin, asin, sqrt
from functools import partial
from operator import is_not

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


# API to fetch nearby points using postgres
@app.route("/get_using_postgres", methods=["GET"])
def get_using_postgres():
    try:
        lat = request.json['lat']
        long = request.json['long']
    except:
        return "Please send Lat and Long"

    # SELECT * FROM public.places WHERE earth_box( ll_to_earth(106.332, 106.331), 5000) @> ll_to_earth(places.latitude, places.longitude);
    loc_given = func.earth_box(func.ll_to_earth(lat, long ), 5000)
    loc_test = func.ll_to_earth(Places.latitude, Places.longitude)
    result = Places.query.filter(loc_given.op("@>")(loc_test))
    place_schema = PlacesSchema(many=True)
    output = place_schema.dump(result).data
    output = json.dumps({'place': output}, default=alchemyencoder)
    # j = output.replace('"[', '[').replace(']"', ']')

    return (json.dumps(json.loads(output), indent=2))


# API to fetch nearby points using self
@app.route('/get_using_self',methods = ['GET'])
def distance():
    q = db.session.query(Places.key, Places.place_name, Places.latitude, Places.longitude).all()
    try:
        lat1 = float(request.args.get('latitude'))  # 28.616700
        long1 = float(request.args.get('longitude'))  # 77.216700
    except:
        return 'Please send Latitude and Longitude'              #77.216700
    lat = []
    lon = []
    for i in range(len(q)):
        x = q[i][2]
        y = q[i][3]
        lat.append(alchemyencoder(x))
        lon.append(alchemyencoder(y))
    # print lat
    # print lon
    lat = filter(partial(is_not, None), lat)
    lon = filter(partial(is_not, None), lon)
    lat_ = list(map(lambda i: radians(i), lat))
    lon_ = list(map(lambda i: radians(i), lon))
    long1, lat1 = map(radians, [long1, lat1])
    res = []
    for i in range(len(lat_)):
        dlon = long1 - lon_[i]
        dlat = lat1 - lat_[i]
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat_[i]) * sin(dlon / 2) ** 2

        c = 2 * asin(sqrt(a))
        r = 6371.00  # Radius of earth in kilometers.
        y = c * r

        res.append(y)

    radius = 5.00  # kilometers
    # print len(res)
    # print len(lat_), len(lon_)

    # print('Distance (km) : ', res)
    yy = []
    for i in res:
        if i <= radius:
            iy = 'Inside the area'
        else:
            iy = 'Outside the area'

        yy.append(iy)

    res = [lati for a, lati in zip(yy, lat) if a.startswith("Inside")]
    res1 = [lati for a, lati in zip(yy, lon) if a.startswith("Inside")]
    #print len(res), len(res1)

    uo = db.session.query(Places).filter(Places.latitude.in_(res), Places.longitude.in_(res1)).all()
    #print uo
    #print len(uo)
    places_schema = PlacesSchema(many=True)
    # print user_schema
    output = places_schema.dump(uo).data

    output = json.dumps({'place': output}, default=alchemyencoder)
    j = output.replace('"[', '[').replace(']"', ']')

    return (json.dumps(json.loads(j), indent=2))




@app.route("/")
def home():
    return "Hello World!"

if __name__ == "__main__":
    app.run(debug=True)
