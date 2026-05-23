# RTL-SDR Dashboard en tiempo real

Proyecto de laboratorio para recepción con antena RTL-SDR, visualización de PSD, waterfall y audio FM en tiempo real.

## Entregables

- **Video de funcionamiento:** https://youtu.be/i_AMY168LBk?feature=shared
- **Código RTL-SDR:** integrado en `lab.py`, sección `SDR`, `HILO SDR` y `DEMODULADOR FM`.
- **Código Dashboard:** integrado en `lab.py`, sección `DASHBOARD`, `CONTROL` y `UPDATE DASHBOARD`.
- **Cuaderno GitHub:** `cuaderno_rtl_sdr_dashboard.ipynb`.

## Organización según la imagen de clase

```text
backend  -> lógica SDR: adquisición IQ, demodulación FM, PSD, potencia y ancho de banda.
frontend -> interfaz Dash: botones, gráficas PSD/waterfall y visualización de parámetros.
scripts  -> archivo ejecutable principal lab.py con código de adquisición, demodulación y dashboard.
```

En este ejercicio el backend y el frontend están en un solo archivo (`lab.py`) para facilitar la ejecución.

## Instalación Ubuntu/WSL

```bash
sudo apt update
sudo apt install -y rtl-sdr librtlsdr-dev python3-tk python3-venv usbutils
```

En PowerShell administrador, si se usa WSL:

```powershell
usbipd list
usbipd bind --busid 2-2
usbipd attach --wsl --busid 2-2
```

Cambiar `2-2` por el BUSID real de la RTL-SDR.

## Verificación

```bash
lsusb
rtl_test
```

Debe aparecer el dispositivo `0bda:2838`.

## Ejecución

```bash
cd ~/lab_sdr
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python lab.py
```

Abrir:

```text
http://127.0.0.1:8050
```
