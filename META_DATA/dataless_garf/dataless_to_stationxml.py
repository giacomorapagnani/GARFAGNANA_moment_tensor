"""
Conversione di file dataless SEED in un unico StationXML (FDSN)
usando obspy.

- Filtra solo i canali AHZ, AHN, AHE
- Collassa tutte le location code in '' (stringa vuota)
- Mantiene una sola epoca per canale (la prima disponibile)
- Rinomina AHZ->HHZ, AHN->HHN, AHE->HHE
- Corregge SampleRate=0 -> 120.0
- Consolida tutto in UN SOLO blocco <Network code="UP">
- Preserva poli, zeri e risposta strumentale completa

Requisiti:
    pip install obspy

Utilizzo:
    python dataless_to_stationxml.py
"""

from pathlib import Path
from obspy import read_inventory
from obspy.core.inventory import Inventory, Network

# ─── Configurazione ───────────────────────────────────────────────────────────

DATALESS_DIR  = Path(".")
OUTPUT_FILE   = Path("stations_garfagnana_UP.xml")
FILE_PATTERN  = "*.dataless"
SAMPLE_RATE   = 120.0   # Hz effettivi dei canali AH Guralp

CHANNEL_RENAME = {"AHZ": "HHZ", "AHN": "HHN", "AHE": "HHE"}

# ─── Lettura e unione dei dataless ───────────────────────────────────────────

dataless_files = sorted(DATALESS_DIR.glob(FILE_PATTERN))
if not dataless_files:
    raise FileNotFoundError(
        f"Nessun file '{FILE_PATTERN}' trovato in: {DATALESS_DIR.resolve()}"
    )

print(f"Trovati {len(dataless_files)} file dataless:")
for f in dataless_files:
    print(f"  {f.name}")

combined = read_inventory(str(dataless_files[0]))
for path in dataless_files[1:]:
    combined += read_inventory(str(path))
    print(f"Aggiunto: {path.name}")

# ─── Filtro canali ────────────────────────────────────────────────────────────

filtered = (
    combined.select(channel="AHZ") +
    combined.select(channel="AHN") +
    combined.select(channel="AHE")
)

# ─── Raccolta stazioni con deduplicazione ─────────────────────────────────────
# obspy crea un Network separato per ogni epoca/location trovata nel dataless.
# Qui consolidiamo tutto in un unico Network "UP".

stations_dict = {}   # sta_code -> Station object (con canali deduplicati)

for net in filtered:
    for sta in net:
        sta_code = sta.code
        if sta_code not in stations_dict:
            # Prima volta: copia la stazione senza canali
            from copy import deepcopy
            sta_clean = deepcopy(sta)
            sta_clean.channels = []
            stations_dict[sta_code] = {'sta': sta_clean, 'seen_channels': set()}

        for ch in sta.channels:
            ch_code = ch.code
            if ch_code not in stations_dict[sta_code]['seen_channels']:
                stations_dict[sta_code]['seen_channels'].add(ch_code)
                ch_copy = deepcopy(ch)
                ch_copy.location_code = ""
                ch_copy.code = CHANNEL_RENAME.get(ch_copy.code, ch_copy.code)
                if ch_copy.sample_rate == 0.0:
                    ch_copy.sample_rate = SAMPLE_RATE
                stations_dict[sta_code]['sta'].channels.append(ch_copy)

# ─── Costruzione inventory con singolo Network UP ─────────────────────────────

stations_list = [v['sta'] for k, v in sorted(stations_dict.items())]

single_network = Network(
    code="UP",
    stations=stations_list,
    description="UniPi Seismic Network",
    start_date=min(s.start_date for s in stations_list if s.start_date)
)

final_inventory = Inventory(networks=[single_network])

# ─── Riepilogo ────────────────────────────────────────────────────────────────

print("\n─── Riepilogo inventory finale ────────────────────────────────────────")
for net in final_inventory:
    print(f"Network: {net.code}  ({len(net)} stazioni)")
    for sta in net:
        ch_list = ", ".join(ch.code for ch in sorted(sta.channels, key=lambda c: c.code))
        resp_ok = all(ch.response is not None for ch in sta.channels)
        print(f"  {sta.code:5s}  lat={sta.latitude:.4f}  lon={sta.longitude:.4f}  "
              f"elev={sta.elevation:.1f} m  [{ch_list}]  "
              f"risposta={'OK' if resp_ok else 'MANCANTE'}")

total_ch = sum(len(sta.channels) for net in final_inventory for sta in net)
print(f"\nTotale stazioni: {len(stations_list)}")
print(f"Totale canali  : {total_ch}")

# ─── Scrittura e verifica ─────────────────────────────────────────────────────

final_inventory.write(str(OUTPUT_FILE), format="STATIONXML")
print(f"\nFile scritto: {OUTPUT_FILE.resolve()}")

verify = read_inventory(str(OUTPUT_FILE))
nets = [net.code for net in verify]
print(f"Verifica OK — reti: {nets}, canali: {[ch.code for net in verify for sta in net for ch in sta][:6]}...")
