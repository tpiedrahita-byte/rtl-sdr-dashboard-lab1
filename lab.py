import numpy as np
from scipy.signal import decimate
from rtlsdr import RtlSdr

import sounddevice as sd

import threading
import queue
import time

from dash import Dash, dcc, html
from dash.dependencies import Input, Output

import plotly.graph_objs as go


# ==========================================================
# CONFIGURACIÓN SDR
# ==========================================================

Fs = 2.4e6
Fc = 98.4e6

N = 262144

AUDIO_FS = 48000

# ==========================================================
# SDR
# ==========================================================

sdr = RtlSdr()

sdr.sample_rate = Fs
sdr.center_freq = Fc
sdr.gain = 'auto'

time.sleep(0.5)

# ==========================================================
# VARIABLES GLOBALES
# ==========================================================

running = False

frequencies = np.zeros(1024)
psd_db = np.zeros(1024)

waterfall_buffer = np.zeros((200, 1024))

fc_estimada = 0
bw_estimado = 0

potencia_inst = 0
potencia_prom = 0

# ==========================================================
# AUDIO QUEUE
# ==========================================================

audio_queue = queue.Queue(maxsize=20)

# ==========================================================
# DEMODULADOR FM
# ==========================================================

def fm_demodulate(samples):

    phase = np.angle(
        samples[1:] * np.conj(samples[:-1])
    )

    audio = decimate(phase, 10)

    audio = audio - np.mean(audio)

    audio = audio / (
        np.max(np.abs(audio)) + 1e-12
    )

    return audio.astype(np.float32)

# ==========================================================
# HILO AUDIO
# ==========================================================

def audio_worker():

    stream = sd.OutputStream(

        samplerate=AUDIO_FS,
        channels=1,
        blocksize=4096

    )

    stream.start()

    while running:

        try:

            audio = audio_queue.get(
                timeout=1
            )

            stream.write(
                audio.reshape(-1,1)
            )

        except:
            pass

# ==========================================================
# HILO SDR
# ==========================================================

def sdr_worker():

    global frequencies
    global psd_db
    global waterfall_buffer

    global fc_estimada
    global bw_estimado

    global potencia_inst
    global potencia_prom

    while running:

        try:

            # ======================================
            # CAPTURA IQ
            # ======================================

            samples = sdr.read_samples(N)

            # ======================================
            # FFT
            # ======================================

            fft_data = np.fft.fftshift(
                np.fft.fft(samples, 1024)
            )

            psd = np.abs(fft_data)**2

            psd = psd / np.max(psd)

            psd_db_local = 10*np.log10(
                psd + 1e-12
            )

            freqs = np.fft.fftshift(
                np.fft.fftfreq(
                    1024,
                    1/Fs
                )
            )

            freqs_abs = (
                freqs + Fc
            ) / 1e6

            frequencies = freqs_abs

            psd_db = psd_db_local

            # ======================================
            # ESTADÍSTICA
            # ======================================

            media = np.mean(
                psd_db_local
            )

            sigma = np.std(
                psd_db_local
            )

            threshold = media + 2*sigma

            indices = np.where(
                psd_db_local > threshold
            )[0]

            if len(indices) > 0:

                fmin = freqs_abs[
                    indices[0]
                ]

                fmax = freqs_abs[
                    indices[-1]
                ]

                bw_estimado = (
                    fmax - fmin
                ) * 1000

                fc_estimada = (
                    fmax + fmin
                ) / 2

            # ======================================
            # POTENCIAS
            # ======================================

            potencia_inst = np.abs(
                samples[-1]
            )**2

            potencia_prom = np.mean(
                np.abs(samples)**2
            )

            # ======================================
            # WATERFALL
            # ======================================

            waterfall_buffer = np.roll(
                waterfall_buffer,
                -1,
                axis=0
            )

            waterfall_buffer[-1,:] = (
                psd_db_local
            )

            # ======================================
            # AUDIO FM
            # ======================================

            audio = fm_demodulate(
                samples
            )

            if not audio_queue.full():

                audio_queue.put(audio)

        except Exception as e:

            print("ERROR:", e)

# ==========================================================
# DASHBOARD
# ==========================================================

app = Dash(__name__)

app.layout = html.Div([

    html.H1(
        "SDR Dashboard - Localización espectral"
    ),

    html.Button(
        "INICIAR SDR",
        id='start-btn',
        n_clicks=0
    ),

    html.Button(
        "DETENER SDR",
        id='stop-btn',
        n_clicks=0
    ),

    html.Button(
        "GUARDAR IQ",
        id='save-btn',
        n_clicks=0
    ),

    html.Div(id='status'),

    html.Br(),

    html.Div(id='fc-text'),
    html.Div(id='bw-text'),

    html.Div(id='pinst-text'),
    html.Div(id='pprom-text'),

    dcc.Graph(id='spectrum'),

    dcc.Graph(id='waterfall'),

    dcc.Interval(
        id='interval',
        interval=300,
        n_intervals=0
    )

])

# ==========================================================
# CONTROL
# ==========================================================

@app.callback(

    Output('status', 'children'),

    Input('start-btn', 'n_clicks'),
    Input('stop-btn', 'n_clicks'),
    Input('save-btn', 'n_clicks')

)

def control(start, stop, save):

    global running

    ctx = app.callback_context

    if not ctx.triggered:

        return "Sistema detenido"

    button_id = ctx.triggered[0]['prop_id']

    # ======================================

    if 'start-btn' in button_id:

        if not running:

            running = True

            threading.Thread(
                target=sdr_worker,
                daemon=True
            ).start()

            threading.Thread(
                target=audio_worker,
                daemon=True
            ).start()

            return "SDR ejecutándose"

        return "SDR ya activo"

    # ======================================

    elif 'stop-btn' in button_id:

        running = False

        return "SDR detenido"

    # ======================================

    elif 'save-btn' in button_id:

        iq = sdr.read_samples(500000)

        np.save(
            "iq_recording.npy",
            iq
        )

        return "IQ guardado"

# ==========================================================
# UPDATE DASHBOARD
# ==========================================================

@app.callback(

    Output('spectrum', 'figure'),
    Output('waterfall', 'figure'),

    Output('fc-text', 'children'),
    Output('bw-text', 'children'),

    Output('pinst-text', 'children'),
    Output('pprom-text', 'children'),

    Input('interval', 'n_intervals')

)

def update_dashboard(_):

    # ======================================
    # ESPECTRO
    # ======================================

    fig_spectrum = go.Figure()

    fig_spectrum.add_trace(

        go.Scatter(

            x=frequencies,
            y=psd_db,

            mode='lines',

            name='PSD'

        )
    )

    fig_spectrum.update_layout(

        title="Espectro SDR",

        xaxis_title="Frecuencia [MHz]",
        yaxis_title="PSD [dB]",

        template='plotly_dark'
    )

    # ======================================
    # WATERFALL
    # ======================================

    fig_waterfall = go.Figure(

        data=go.Heatmap(

            z=waterfall_buffer,

            colorscale='Turbo'

        )
    )

    fig_waterfall.update_layout(

        title="Waterfall SDR",

        template='plotly_dark'
    )

    return (

        fig_spectrum,
        fig_waterfall,

        f"Fc estimada: {fc_estimada:.3f} MHz",

        f"BW estimado: {bw_estimado:.2f} kHz",

        f"Potencia instantánea: {potencia_inst:.6f}",

        f"Potencia promedio: {potencia_prom:.6f}"

    )

# ==========================================================
# RUN
# ==========================================================

if __name__ == '__main__':

    app.run(

        debug=False,

        host='0.0.0.0',

        port=8050

    )