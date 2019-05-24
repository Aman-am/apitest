from flask import Flask,request,jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
import json, decimal
from sqlalchemy import func, INT, TEXT, JSON, Column, and_
from geoalchemy2 import Geometry
from math import radians, cos, sin, asin, sqrt

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

class Boundary(db.Model):
    __tablename__ = 'boundary'

    gid = Column(INT , primary_key=True)
    name = Column(TEXT)
    type = Column(TEXT)
    parent = Column(TEXT)
    geom = Column(Geometry(geometry_type='POLYGON', srid=4326))
    geom = Column(TEXT)

    def __init__(self, gid , geom, properties):
        self.gid = gid
        self.type = type
        self.parent = parent
        self.name = name
        self.geom = geom

    def __repr__(self):
        return "<Places - '%s'>" % (self.name)

class PlacesSchema(ma.ModelSchema):
    class Meta:
        model = Places

class BoundarySchema(ma.ModelSchema):
    class Meta:
        model = Boundary

def alchemyencoder(obj):
    """JSON encoder function for SQLAlchemy special classes."""
    if isinstance(obj, decimal.Decimal):
        return float(obj)


# API to create new location
@app.route("/post_location", methods=["POST"])
def add_location():
    try:
        latitude = request.json['lat']
        longitude = request.json['long']
    except:
        return "Please send Lat and Long"
    address = request.json['address'].split("+")
    if len(address) != 3:
        return "Invalid Address"
    key = address[0]
    place_name = address[1]
    city = address[2]

    exists = db.session.query(Places.key).filter_by(key=key).scalar() is not None
    if exists:
        return "pincode exists"

    exists = db.session.query(Places.key).filter(and_(Places.latitude,latitude, Places.longitude == longitude) ).all()
    if len(exists)>0:
        return "location exists"

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
        lat = float(request.args.get('latitude'))
        long = float(request.args.get('longitude'))
    except:
        return "Please send Lat and Long"

    # SELECT * FROM public.places WHERE earth_box( ll_to_earth(106.332, 106.331), 5000) @> ll_to_earth(places.latitude, places.longitude);
    loc_given = func.earth_box(func.ll_to_earth(lat, long ), 5000)
    loc_test = func.ll_to_earth(Places.latitude, Places.longitude)
    result = Places.query.filter(loc_given.op("@>")(loc_test))
    place_schema = PlacesSchema(many=True)
    output = place_schema.dump(result).data
    output = json.dumps({'place': output}, default=alchemyencoder)
    return (json.dumps(json.loads(output), indent=2))


# API to fetch nearby points using self
@app.route('/get_using_self',methods = ['GET'])
def distance():
    q = db.session.query(Places.key, Places.place_name, Places.latitude, Places.longitude).all()
    try:
        lat1 = float(request.args.get('latitude'))
        long1 = float(request.args.get('longitude'))
    except:
        return 'Please send Latitude and Longitude'
    lat = []
    lon = []
    for i in range(len(q)):
        x = q[i][2]
        y = q[i][3]
        lat.append(alchemyencoder(x))
        lon.append(alchemyencoder(y))
    lat = list(filter(None, lat))
    lon = list(filter(None, lon))
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

    yy = []
    for i in res:
        if i <= radius:
            iy = 'Inside the area'
        else:
            iy = 'Outside the area'

        yy.append(iy)
    res = [lati for a, lati in zip(yy, lat) if a.startswith("Inside")]
    res1 = [lati for a, lati in zip(yy, lon) if a.startswith("Inside")]

    uo = db.session.query(Places).filter(Places.latitude.in_(res), Places.longitude.in_(res1)).all()
    places_schema = PlacesSchema(many=True)
    output = places_schema.dump(uo).data
    output = json.dumps({'place': output}, default=alchemyencoder)
    return (json.dumps(json.loads(output), indent=2))


@app.route('/get_region' ,methods = ['GET'])
def geoj():
    try:
        lat = float(request.args.get('latitude'))
        lon = float(request.args.get('longitude'))
    except:
        return 'Please send Latitude and Longitude'
    Point = 'POINT('+ str(lon) + ' ' +str(lat) + ')'
    query = db.session.query(Boundary.name, Boundary.type, Boundary.parent ).filter(func.ST_Contains(Boundary.geom, func.ST_Transform(func.ST_GeometryFromText(Point,4326), 4326))).all()
    schema = BoundarySchema(many=True)
    output = schema.dump(query).data
    output = json.dumps({'result': output}, default=alchemyencoder)
    return (json.dumps(json.loads(output), indent=2))

@app.route("/")
def home():
    return "Hello World!"

if __name__ == "__main__":
    app.run(debug=True)
