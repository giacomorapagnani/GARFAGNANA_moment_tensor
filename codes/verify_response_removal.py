"""
Verifica della rimozione della risposta strumentale.

Esegui PRIMA di processare tutti i dati.
Testa su UN singolo file waveform e produce 4 plot diagnostici:

  1. Confronto waveform raw vs corretta (time domain)
  2. Confronto spettri raw vs corretta (frequency domain)
  3. Curva di risposta strumentale (modulo) sovrapposta allo spettro raw
  4. Spettrogramma della traccia corretta

Come interpretare i risultati:
  - Lo spettro corretto deve essere PIATTO (±10 dB) nella banda passante del sensore
  - Il rapporto segnale/rumore deve migliorare rispetto al raw
  - Non ci devono essere esplosioni ad alta o bassa frequenza
  - L'ampiezza deve essere fisicamente ragionevole (m/s per VEL)

Utilizzo:
    python verify_response_removal.py
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from obspy import read, read_inventory, UTCDateTime
from obspy.signal.invsim import corn_freq_2_paz
import os

# ─── CONFIGURA QUI ────────────────────────────────────────────────────────────

# Percorso a UN file waveform da testare
WAVEFORM_FILE = '../DATA/garfagnana_2026_03_25_07_13_43/garfagnana_UP_UP01_2026_03_25_07_13_43.mseed'

# Inventory
INVENTORY_FILE = '../META_DATA/stations_garfagnana_INGV_RESIF_UP.xml'

# Parametri rimozione (devono essere IDENTICI a quelli usati nel processing)
OUTPUT     = 'VEL'           # 'VEL' = m/s,  'DISP' = m,  'ACC' = m/s^2
PRE_FILT   = [0.005, 0.01, 45.0, 50.0]
WATER_LEVEL = 60

# ─────────────────────────────────────────────────────────────────────────────

inv = read_inventory(INVENTORY_FILE)

# Leggi e prepara la traccia raw
st_raw = read(WAVEFORM_FILE)
st_raw.merge(method=1, fill_value='interpolate')
tr_raw = st_raw[0].copy()
print(f"Traccia: {tr_raw.id}")
print(f"  SR={tr_raw.stats.sampling_rate} Hz, "
      f"durata={tr_raw.stats.npts/tr_raw.stats.sampling_rate:.1f} s, "
      f"inizio={tr_raw.stats.starttime}")

# Verifica che l'inventory contenga questa stazione
net, sta, loc, cha = tr_raw.id.split('.')
matches = inv.select(network=net, station=sta, location=loc, channel=cha)
if len(matches) == 0:
    print(f"\n*** ATTENZIONE: nessun match nell'inventory per {tr_raw.id} ***")
    print("    Controlla NET/STA/LOC/CHA nel file mseed vs inventory.")
else:
    ch = matches[0][0][0]
    print(f"\n  Match inventory: {net}.{sta}.{loc}.{cha}")
    print(f"  Sensore: {ch.sensor.description if ch.sensor else 'N/A'}")
    if ch.response:
        sens = ch.response.instrument_sensitivity
        print(f"  Sensitivity: {sens.value:.4e} {sens.input_units} -> {sens.output_units} @ {sens.frequency} Hz")
    else:
        print("  *** ATTENZIONE: nessuna risposta trovata per questo canale ***")

# Prepara traccia corretta
st_cor = read(WAVEFORM_FILE)
st_cor.merge(method=1, fill_value='interpolate')
tr_cor = st_cor[0].copy()
tr_cor.detrend('demean')
tr_cor.detrend('linear')
tr_cor.taper(max_percentage=0.05, type='cosine')
tr_cor.remove_response(inventory=inv, output=OUTPUT,
                        pre_filt=PRE_FILT, water_level=WATER_LEVEL)

# ─── PLOT ─────────────────────────────────────────────────────────────────────

fig = plt.figure(figsize=(14, 12))
fig.suptitle(f"Verifica rimozione risposta — {tr_raw.id}", fontsize=13, fontweight='bold')
gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.45, wspace=0.35)

units = {'VEL': 'm/s', 'DISP': 'm', 'ACC': 'm/s²'}[OUTPUT]
sr = tr_raw.stats.sampling_rate

# ── 1. Waveform raw ───────────────────────────────────────────────────────────
ax1 = fig.add_subplot(gs[0, 0])
t = np.arange(tr_raw.stats.npts) / sr
ax1.plot(t, tr_raw.data, lw=0.5, color='steelblue')
ax1.set_title('Raw (counts)', fontsize=10)
ax1.set_xlabel('Tempo (s)')
ax1.set_ylabel('Counts')
ax1.grid(True, alpha=0.3)

# ── 2. Waveform corretta ──────────────────────────────────────────────────────
ax2 = fig.add_subplot(gs[0, 1])
t2 = np.arange(tr_cor.stats.npts) / tr_cor.stats.sampling_rate
ax2.plot(t2, tr_cor.data, lw=0.5, color='firebrick')
ax2.set_title(f'Corretta ({units})', fontsize=10)
ax2.set_xlabel('Tempo (s)')
ax2.set_ylabel(units)
ax2.grid(True, alpha=0.3)
# Controllo ampiezza di picco
peak = np.max(np.abs(tr_cor.data))
ax2.set_title(f'Corretta ({units})  — picco={peak:.2e}', fontsize=10)

# Avviso se ampiezza non fisicamente ragionevole per VEL
if OUTPUT == 'VEL':
    if peak > 1e-1:
        ax2.set_facecolor('#fff0f0')
        ax2.text(0.5, 0.95, '⚠ ampiezza sospetta (>0.1 m/s)',
                 transform=ax2.transAxes, ha='center', va='top',
                 color='red', fontsize=9)
    elif peak < 1e-12:
        ax2.set_facecolor('#fff0f0')
        ax2.text(0.5, 0.95, '⚠ ampiezza sospetta (<1e-12 m/s)',
                 transform=ax2.transAxes, ha='center', va='top',
                 color='red', fontsize=9)
    else:
        ax2.text(0.5, 0.95, '✓ ampiezza fisicamente ragionevole',
                 transform=ax2.transAxes, ha='center', va='top',
                 color='green', fontsize=9)

# ── 3. Spettro raw ────────────────────────────────────────────────────────────
ax3 = fig.add_subplot(gs[1, 0])
nfft = min(tr_raw.stats.npts, 8192)
freq_raw = np.fft.rfftfreq(nfft, d=1.0/sr)
spec_raw = np.abs(np.fft.rfft(tr_raw.data[:nfft]))
ax3.loglog(freq_raw[1:], spec_raw[1:], lw=0.8, color='steelblue', label='Raw')
ax3.set_title('Spettro raw (counts)', fontsize=10)
ax3.set_xlabel('Frequenza (Hz)')
ax3.set_ylabel('Ampiezza')
ax3.grid(True, which='both', alpha=0.3)
ax3.set_xlim([0.005, sr/2])
# Evidenzia banda passante del pre_filt
ax3.axvspan(PRE_FILT[1], PRE_FILT[2], alpha=0.1, color='green', label='Banda utile')
ax3.axvline(PRE_FILT[0], color='orange', lw=0.8, ls='--')
ax3.axvline(PRE_FILT[3], color='orange', lw=0.8, ls='--', label='pre_filt')
ax3.legend(fontsize=8)

# ── 4. Spettro corretto ───────────────────────────────────────────────────────
ax4 = fig.add_subplot(gs[1, 1])
nfft2 = min(tr_cor.stats.npts, 8192)
sr2 = tr_cor.stats.sampling_rate
freq_cor = np.fft.rfftfreq(nfft2, d=1.0/sr2)
spec_cor = np.abs(np.fft.rfft(tr_cor.data[:nfft2]))
ax4.loglog(freq_cor[1:], spec_cor[1:], lw=0.8, color='firebrick', label='Corretta')
ax4.set_title(f'Spettro corretto ({units})', fontsize=10)
ax4.set_xlabel('Frequenza (Hz)')
ax4.set_ylabel(f'Ampiezza ({units})')
ax4.grid(True, which='both', alpha=0.3)
ax4.set_xlim([0.005, sr2/2])
ax4.axvspan(PRE_FILT[1], PRE_FILT[2], alpha=0.1, color='green', label='Banda utile')
ax4.axvline(PRE_FILT[0], color='orange', lw=0.8, ls='--')
ax4.axvline(PRE_FILT[3], color='orange', lw=0.8, ls='--', label='pre_filt')
ax4.legend(fontsize=8)

# ── 5. Curva di risposta strumentale ─────────────────────────────────────────
ax5 = fig.add_subplot(gs[2, 0])
try:
    resp_freqs = np.logspace(np.log10(0.001), np.log10(sr/2), 500)
    resp_vals = matches[0][0][0].response.get_evalresp_response_for_frequencies(
        resp_freqs, output=OUTPUT)
    ax5.loglog(resp_freqs, np.abs(resp_vals), lw=1.5, color='purple')
    ax5.set_title(f'Risposta strumentale ({units}/count)', fontsize=10)
    ax5.set_xlabel('Frequenza (Hz)')
    ax5.set_ylabel(f'{units}/count')
    ax5.grid(True, which='both', alpha=0.3)
    ax5.axvspan(PRE_FILT[1], PRE_FILT[2], alpha=0.1, color='green')
    ax5.axvline(PRE_FILT[0], color='orange', lw=0.8, ls='--')
    ax5.axvline(PRE_FILT[3], color='orange', lw=0.8, ls='--')
except Exception as e:
    ax5.text(0.5, 0.5, f'Curva risposta non disponibile:\n{e}',
             transform=ax5.transAxes, ha='center', va='center', fontsize=9)

# ── 6. Spettrogramma traccia corretta ─────────────────────────────────────────
ax6 = fig.add_subplot(gs[2, 1])
tr_spec = tr_cor.copy()
tr_spec.spectrogram(log=True, axes=ax6, show=False,
                    title=f'Spettrogramma corretta ({units})',
                    samp_rate=tr_cor.stats.sampling_rate)
ax6.set_xlabel('Tempo (s)')
ax6.set_title(f'Spettrogramma ({units})', fontsize=10)

# ─── Stampa sommario numerico ─────────────────────────────────────────────────
print("\n─── Sommario verifica ────────────────────────────────────────────────")
print(f"  Output richiesto    : {OUTPUT} ({units})")
print(f"  pre_filt            : {PRE_FILT}")
print(f"  water_level         : {WATER_LEVEL}")
print(f"  Ampiezza picco raw  : {np.max(np.abs(tr_raw.data)):.4e} counts")
print(f"  Ampiezza picco cor  : {peak:.4e} {units}")
print(f"  Rapporto segnale    : {peak / np.std(tr_cor.data):.1f} (>5 = buono)")

# Controllo piattezza spettro nella banda passante
mask = (freq_cor > PRE_FILT[1]) & (freq_cor < PRE_FILT[2])
if mask.sum() > 10:
    band_spec = spec_cor[mask]
    flatness_db = 20 * np.log10(np.max(band_spec) / (np.min(band_spec) + 1e-30))
    print(f"  Piattezza spettro   : {flatness_db:.1f} dB nella banda "
          f"[{PRE_FILT[1]}-{PRE_FILT[2]} Hz]  (<20 dB = buono)")

plt.tight_layout()
outfile = 'verifica_risposta.png'
plt.savefig(outfile, dpi=150, bbox_inches='tight')
print(f"\n  Plot salvato: {outfile}")
plt.show()
