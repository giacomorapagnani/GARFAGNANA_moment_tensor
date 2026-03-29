from obspy import read, UTCDateTime, read_inventory
from obspy.signal import PPSD
from obspy.io.xseed import Parser

stazione='UP02'
path= '../META_DATA/metadati_garf'
# Path to your dataless SEED file
dataless_file = path+'/'+stazione+'.dataless'

# Read the dataless file
parser = Parser(dataless_file)

# Write as StationXML
parser.write_xseed(path+'/'+stazione+'.xml')

