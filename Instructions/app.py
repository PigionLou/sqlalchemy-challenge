# import dependencies
import numpy as np
import datetime as dt
import pandas as pd

import sqlalchemy
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, func

from flask import Flask, jsonify

# create engine to hawaii.sqlite
engine = create_engine("sqlite:///Resources/hawaii.sqlite")

# reflect an existing database into a new model
db = automap_base()

# reflect the tables
db.prepare(engine, reflect=True)

# Save references to each table
measurement = db.classes.measurement
station = db.classes.station

# Flask set up
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Flask route

# Home route

@app.route("/")
def welcome():
    """List all available api routes."""
    return (
        f"<b>Climate API</b><br/>"
        f"{'-'*66}<br/>"
        f"<b>Available Routes:</b><br/>"
        f"/api/v1.0/precipitation<br/>"
        f"/api/v1.0/stations<br/>"
        f"/api/v1.0/tobs<br/>"
        f"/api/v1.0/start=YYYY-MM-DD<br/>"
        f"/api/v1.0/start=YYYY-MM-DD/end=YYYY-MM-DD<br/>"
        f"{'-'*66}<br/>"
        f"<b>Note:</b><br/>"
        f"* Route <b>tobs</b> shows results of the most active station.<br/>"
        f"* The <b>date format</b> will be YYYY-MM-DD."
    )


# Precipitation route

@ app.route("/api/v1.0/precipitation")
def precipitation():
    # Create our session (link) from Python to the DB
    session = Session(engine)

    """Return a list of all precipitation and date"""
    # Query precipitation data
    results = session.query(measurement.date, measurement.prcp).all()

    session.close()

    # Create a dictionary from the row data and append to a list of all_prpc
    all_prcp = []
    for date, prcp in results:
        prcp_dict = {}
        prcp_dict['Date'] = date
        prcp_dict['Precipitation'] = prcp
        all_prcp.append(prcp_dict)

    return jsonify(all_prcp)


# stations route

@ app.route("/api/v1.0/stations")
def stations():
    # Create our session (link) from Python to the DB
    session = Session(engine)

    """Return a list of all stations"""
    # Query all stations
    results = session.query(measurement.station,
                            station.name,
                            station.latitude,
                            station.longitude,
                            station.elevation,
                            func.min(measurement.prcp),
                            func.max(measurement.prcp),
                            func.avg(measurement.prcp),
                            func.min(measurement.tobs),
                            func.max(measurement.tobs),
                            func.avg(measurement.tobs))\
        .filter(measurement.station == station.station)\
        .group_by(measurement.station).all()

    session.close()

    # Create a dictionary from the row data and append to a list of all_stn
    all_stn = []
    for stn_id, stn_name, stn_lat, stn_lng, stn_elv, stn_pmin, stn_pmax, stn_pavg, stn_tmin, stn_tmax, stn_tavg in results:
        stn_dict = {}
        stn_dict['station ID'] = stn_id
        stn_dict['station Name'] = stn_name
        stn_dict['Location'] = {'Latitude': stn_lat, 'Longitude': stn_lng}
        stn_dict['Elevation'] = stn_elv
        stn_dict['Meteorology'] = {
            'Temperature': {
                'Min': stn_tmin,
                'Max': stn_tmax,
                'Avg': round(stn_tavg, 2)
            },
            'Precipitation': {
                'Min': stn_pmin,
                'Max': stn_pmax,
                'Avg': round(stn_pavg, 2)
            }
        }

        all_stn.append(stn_dict)

    return jsonify(all_stn)


# TOBS route

@ app.route("/api/v1.0/tobs")
def tobs():
    # Create our session (link) from Python to the DB
    session = Session(engine)

    results = session.query(measurement.date,measurement.tobs)\
        .filter(measurement.station == station.station)\
        .group_by(measurement.station).all()

    """Return a list of all TOBS"""
    # Find the most recent date in the data set. 
    date_last_query = session.query(measurement.date).order_by(measurement.date.desc()).first()
    date_last = date_last_query[0]
    date_last = dt.datetime.strptime(date_last, '%Y-%m-%d').date()

    # Calculate the date one year from the last date in data set.
    date_last_yr = date_last - dt.timedelta(days=365)
    date_last_yr = date_last_yr.strftime('%Y-%m-%d')

    # Design a query to find the most active stations (i.e. what stations have the most rows?)
    most_active_station_query = session.query(measurement.station, station.name, func.count(measurement.station))\
        .group_by(measurement.station)\
        .order_by(func.count(measurement.station).desc())\
        .first()

    # Query the last 12 months of temperature observation data for this station
    active_station_12mo = session.query(measurement.tobs)\
        .filter(measurement.date <= date_last)\
        .filter(measurement.date >= date_last_yr)\
        .filter(measurement.station == most_active_station_query[0])\
        .all()

    session.close()

    # Create a dictionary from the row data and append to a list of the most active station
    act_stn = []
    for act_date, act_tobs in results:
        act_stn_dict = {
            'station ID': most_active_station_query[0],
            'station Name': most_active_station_query[1]
        }
        act_stn_dict['Date'] = act_date
        act_stn_dict['TOBS'] = act_tobs
        act_stn.append(act_stn_dict)

    return jsonify(act_stn)


# Start Date route

@app.route("/api/v1.0/start=<start>")
def start_date(start):
    # Create our session (link) from Python to the DB
    session = Session(engine)

    # Query all the data related to the most active station in the past year
    results = session.query(func.min(measurement.tobs),
                            func.max(measurement.tobs),
                            func.avg(measurement.tobs))\
        .filter(measurement.date >= start).all()

    first_date = session.query(measurement.date).order_by(
        measurement.date).first()
    last_date = session.query(measurement.date).order_by(
        measurement.date.desc()).first()

    session.close()

    # Creat a date list of dataset
    date_list = pd.date_range(start=first_date[0], end=last_date[0])

    # Create a dictionary from the row data and append to a list of strt_data
    strt_data = []
    for tmin, tmax, tavg in results:
        strt_data_dict = {
            'Start Date': start,
            'End Date': last_date[0]
        }
        strt_data_dict['T-MIN'] = tmin
        strt_data_dict['T-MAX'] = tmax
        strt_data_dict['T-AVG'] = tavg
        strt_data.append(strt_data_dict)

        # If statement for date input in API search
        if start in date_list:
            return jsonify(strt_data)
        else:
            return jsonify({
                "error": f"Date: {start} not found. Date must be between {first_date[0]} and {last_date[0]}"
            }), 404


# Start and End Date route

@app.route("/api/v1.0/start=<start>/end=<end>")
def period(start, end):
    # Create our session (link) from Python to the DB
    session = Session(engine)

    # Query all the data related to the most active station in the past year
    results = session.query(func.min(measurement.tobs),
                            func.max(measurement.tobs),
                            func.avg(measurement.tobs))\
        .filter(measurement.date >= start)\
        .filter(measurement.date <= end).all()

    first_date = session.query(measurement.date).order_by(
        measurement.date).first()
    last_date = session.query(measurement.date).order_by(
        measurement.date.desc()).first()

    session.close()

    # Create a dictionary from the row data and append to a list of period_data
    date_list = pd.date_range(start=first_date[0], end=last_date[0])

    period_data = []

    for tmin, tmax, tavg in results:
        period_data_dict = {
            'Start Date': start,
            'End Date': end
        }
        period_data_dict['T-MIN'] = tmin
        period_data_dict['T-MAX'] = tmax
        period_data_dict['T-AVG'] = tavg
        period_data.append(period_data_dict)

        # If statement for date input in API search
        if start and end in date_list:
            if start <= end:
                return jsonify(period_data)
            elif start > end:
                return jsonify({
                    "error": f'{start} is greater than {end}'
                })
        else:
            return jsonify({
                "error": f"Date: {start} to {end} not found. Date must be between {first_date[0]} and {last_date[0]}"
            }), 404


# app.run statement
if __name__ == "__main__":
    app.run(debug=True)