### Download waveforms with obspy from station.xml and catalogue.pf
# %% lib
from pyrocko import util, model, io, trace, moment_tensor, gmtpy
from pyrocko import pz
from pyrocko import orthodrome as od
from pyrocko.io import quakeml
from pyrocko.io import stationxml as fdsn
from pyrocko.client import catalog
from pyrocko.automap import Map
import pyrocko.moment_tensor as pmt
from seiscloud import plot as scp
from seiscloud import cluster as scc
import numpy as num
import os, sys, re, math, shutil
import matplotlib.pyplot as plt
from matplotlib import collections  as mc
from matplotlib import dates
import datetime
import urllib.request
from pyrocko.plot.gmtpy import GMT
from zoneinfo import ZoneInfo


#obspy
from obspy import read_inventory
from obspy.core.stream import Stream
from obspy.clients.fdsn.client import Client
from obspy import UTCDateTime
import pytz

# %% code


tshifth_1=300 #s 
tshifth_2=300 #s


workdir='../'
catdir =  os.path.join(workdir,'CAT')
meta_datadir=os.path.join(workdir,'META_DATA')
datadir=os.path.join(workdir,'DATA')

catname = os.path.join(catdir, 'catalogue_garfagnana_test.pf')           #CHANGE 

cat = model.load_events(catname)
print('Number of events:', len(cat))

clients_names = {                   #CHANGE clients and networks to match the stationxml used
 'IV': "INGV",
 'GU': "INGV",
 'FR': "RESIF"
}

# 

stations_name=os.path.join(meta_datadir, 'stations_garfagnana_INGV_RESIF.xml')     #CHANGE 
xml_file=read_inventory(stations_name)                                 

#print(stations)

################################################################################
########## DO NOT USE !!!datetime.datetime.fromtimestamp(ev.time)!!! ##########
################################################################################

################################################################################
#################### USE INSTEAD util.time_to_str(ev.time) ####################
################################################################################

# download waveforms strarting from this data:
date_start_download='2025-01-01 00:00:00.000'                               #CHANGE
sec_start_download=util.str_to_time(date_start_download)
date_end_download='2027-01-01 00:00:00.000'                               #CHANGE
sec_end_download=util.str_to_time(date_end_download)

count=1
for ev in cat:
    if ev.time>=sec_start_download and ev.time<=sec_end_download:
        evID=ev.name
        wave_name1, wave_name2 = evID.split('_')[0], '_'.join(evID.split('_')[1:])
        #transform UTC time
        t = util.time_to_str(ev.time)

        print('\nevent number:',count)
        print('origin UTC time event:',t)

        event_start = UTCDateTime(t) - tshifth_1             
        #print('event starts at:',event_start)

        event_end=UTCDateTime(t) + tshifth_2                
        #print('event ends at:',event_end)

        # delete old directory and create new one for each event
        waveletdir=os.path.join(datadir,evID)
        if os.path.isdir(waveletdir):
            shutil.rmtree(waveletdir)
        os.mkdir(waveletdir)

        waves=Stream()
        #for client, networks in clients_networks.items():
        #    for net in networks:

        for network in xml_file:
            client= Client(clients_names[network.code])
            for  station in network.stations:
                try:
                    wave = Stream()
                    print( f'Dowloading traces for {network.code} {station.code} station')
                    wave= client.get_waveforms(starttime=event_start,endtime=event_end,
                                        network=network.code,station=station.code,
                                        location='*', channel='HH?',
                                        attach_response=True)
                    
                    wave_name =  f'{wave_name1}_{network.code}_{station.code}_' + wave_name2 + '.mseed'
                    # save wavelet separated for each station
                    wavelet_name= os.path.join(waveletdir,wave_name) 
                    wave.write(wavelet_name,format='MSEED')

                    waves += wave
                except:
                    print( f'Warning:{network.code} {station.code} not recording\n')
                    continue
        
        ntr= len(waves.traces)
        print('Total traces found:',ntr) 

        if ntr == 0:
            print(f'WARNING: no traces found for {evID}\nNo wavalet saved.')
        else:
            print('Wavelet dowloaded and saved!')
        count+=1