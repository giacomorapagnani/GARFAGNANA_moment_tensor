### REMOVE INSTRUMENTAL RESPONSE FROM DOWNLOADED WAVEFORMS WITH STATION.XML
### AND SAVE NEW-WAVEFORMS IN NEW DIRECTORY 

import matplotlib.pyplot as plt
import numpy as num

from pyrocko import util, model, io, trace, moment_tensor, gmtpy
from pyrocko import pz
from pyrocko import orthodrome as od
from pyrocko.io import quakeml
from pyrocko.io import stationxml as fdsn
from pyrocko.client import catalog
from pyrocko.automap import Map

from obspy.clients.fdsn.client import Client
from obspy import UTCDateTime
from obspy.core.event import Catalog
from obspy.core.stream import Stream
from obspy.core.event import Event
from obspy.core.event import Origin
from obspy.core.event import Magnitude
from obspy import read
from obspy import read_events
from obspy import read_inventory
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import os
import pickle

import geopy.distance

workdir='../'

datadir=os.path.join(workdir,'DATA')
newdatadir=os.path.join(workdir,'DATA_response')

###################################
meta_datadir=os.path.join(workdir,'META_DATA')

stations_name=os.path.join(meta_datadir, 'stations_garfagnana_INGV_RESIF_UP.xml')
stations=read_inventory(stations_name)                             

#print(stations)

for eventdir in os.listdir(datadir):
    # select event
    ev_name = os.fsdecode(eventdir)
    
    if ev_name.startswith('.'): 
        continue

    else:
        ev_path=os.path.join(datadir,ev_name)
        new_eventpath=os.path.join(newdatadir,ev_name)

        if os.path.isdir(new_eventpath): # check if file already exist
            print('\nINFO: Event already exists, skipping:',ev_name)
            continue

        else:
            os.mkdir(new_eventpath) # create new directory for event
            print('\n\nRemoving response from event:',ev_name)
            for tr_file in os.listdir(ev_path):
                # select trace
                tr_name = os.fsdecode(tr_file)
                if tr_name.startswith('.'): 
                    continue
                else:
                    tr_path=os.path.join(ev_path,tr_name)
                    new_tr_path= os.path.join(new_eventpath,tr_name)  
            
                    # select wavelet (obspy)  
                    w=read(tr_path)
                    print('loading trace:',tr_path.split('/')[-1])

                    #wave.merge(fill_value=0)
                    # trim over the [t1, t2] interval
                    #wave.trim(starttime=event_start, endtime=event_end, pad=True, fill_value=0)

                    # remove trend
                    w.detrend("demean")

                    # pre filter
                    pre_filt = [0.005, 0.01, 45,50]       # for big eq

                    # remove instrumental response
                    w.remove_response(inventory=stations, output='DISP', pre_filt=pre_filt)

                    w.write(new_tr_path,format='MSEED')
            print('Response removed and wavelets saved!')
