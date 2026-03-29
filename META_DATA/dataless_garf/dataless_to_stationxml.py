"""
Conversione di file dataless SEED in un unico StationXML (FDSN)
usando obspy.

- Filtra solo i canali AHZ, AHN, AHE
- Collassa tutte le location code in '' (stringa vuota)
- Mantiene una sola epoca per canale (la prima disponibile)
- Rinomina AHZ -> HHZ, AHN -> HHN, AHE -> HHE
- Preserva poli, zeri e risposta strumentale completa


Utilizzo:
    Metti questo script nella stessa cartella dei file .dataless e lancia:
    python dataless_to_stationxml.py
"""

from pathlib import Path
from obspy import read_inventory

# ─── Configurazione ───────────────────────────────────────────────────────────

DATALESS_DIR = Path(".")
OUTPUT_FILE  = Path("stations_garfagnana_UP.xml")
FILE_PATTERN = "*.dataless"

CHANNEL_RENAME = {
    "AHZ": "HHZ",
    "AHN": "HHN",
    "AHE": "HHE",
}

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
print(f"\nCaricato: {dataless_files[0].name}")
for path in dataless_files[1:]:
    combined += read_inventory(str(path))
    print(f"Aggiunto:  {path.name}")

# ─── Filtro: solo AHZ, AHN, AHE ──────────────────────────────────────────────

filtered = (
    combined.select(channel="AHZ") +
    combined.select(channel="AHN") +
    combined.select(channel="AHE")
)

# ─── Per ogni stazione: una sola epoca per canale, location='', rinomina ──────

for net in filtered:
    for sta in net:
        seen_channels = set()
        channels_to_keep = []

        for ch in sta.channels:
            key = ch.code  # e.g. 'AHZ'
            if key not in seen_channels:
                seen_channels.add(key)
                # Azzera location code
                ch.location_code = ""
                # Rinomina AH? -> HH?
                ch.code = CHANNEL_RENAME.get(ch.code, ch.code)
                channels_to_keep.append(ch)
            # Le epoche duplicate vengono semplicemente scartate

        sta.channels = channels_to_keep

# ─── Riepilogo ────────────────────────────────────────────────────────────────

print("\n─── Riepilogo inventory finale ────────────────────────────────────────")
for net in filtered:
    for sta in net:
        ch_list = ", ".join(ch.code for ch in sorted(sta.channels, key=lambda c: c.code))
        resp_ok = all(ch.response is not None for ch in sta.channels)
        print(f"  {net.code}.{sta.code:5s}  "
              f"lat={sta.latitude:.4f}  lon={sta.longitude:.4f}  "
              f"elev={sta.elevation:.1f} m  "
              f"canali=[{ch_list}]  risposta={'OK' if resp_ok else 'MANCANTE'}")

total_ch = sum(len(sta.channels) for net in filtered for sta in net)
print(f"\nTotale stazioni : {sum(len(net) for net in filtered)}")
print(f"Totale canali   : {total_ch}")

# ─── Scrittura XML ────────────────────────────────────────────────────────────

filtered.write(str(OUTPUT_FILE), format="STATIONXML")
print(f"\nFile scritto: {OUTPUT_FILE.resolve()}")

# ─── Verifica rapida ──────────────────────────────────────────────────────────

verify = read_inventory(str(OUTPUT_FILE))
ch_codes = sorted({ch.code for net in verify for sta in net for ch in sta})
print(f"Verifica lettura OK — canali presenti: {ch_codes}")
