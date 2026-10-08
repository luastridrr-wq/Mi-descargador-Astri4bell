

import os
import secrets
from flask import Flask, render_template, request, send_file, after_this_request
import yt_dlp

app = Flask(__name__)

# Carpeta temporal donde se procesarán las descargas en el servidor
CARPETA_DESCARGAS = os.path.join(os.getcwd(), 'descargas_temporales')
os.makedirs(CARPETA_DESCARGAS, exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form.get('url')
        formato = request.form.get('formato') # Puede ser 'mp4' o 'mp3'
        
        if not url:
            return "Por favor, introduce una URL válida.", 400

        # Generamos un nombre único temporal para evitar conflictos de archivos en el servidor
        nombre_unico = secrets.token_hex(8)
        
        # CONFIGURACIÓN DEFINITIVA Y ROBUSTA PARA EVITAR ERRORES DE FORMATO
        if formato == 'mp3':
            opciones = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(CARPETA_DESCARGAS, f'{nombre_unico}.%(ext)s'),
                'cookiefile': 'www.youtube.com_cookies.txt',  # Autenticación con cookies contra bloqueos
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }
            extension_final = 'mp3'
        else:  # CONFIGURACIÓN MP4 UNIVERSAL
            opciones = {
                # Descarga la máxima calidad absoluta de video y audio que tenga YouTube, sin importar su formato de origen
                'format': 'bestvideo+bestaudio/best',
                'cookiefile': 'www.youtube.com_cookies.txt',  # Autenticación con cookies contra bloqueos
                # Fuerza a FFmpeg a fusionar y re-codificar los flujos directamente a un contenedor MP4 compatible
                'merge_output_format': 'mp4',
                'outtmpl': os.path.join(CARPETA_DESCARGAS, f'{nombre_unico}.%(ext)s'),
            }
            extension_final = 'mp4'

        try:
            # Descarga y procesamiento del archivo en el servidor
            with yt_dlp.YoutubeDL(opciones) as ydl:
                info = ydl.extract_info(url, download=True)
                # Obtenemos el título original del video
                titulo_video = info.get('title', 'video_descargado')
                # Limpiamos caracteres extraños del título para que no rompa el sistema de descargas
                titulo_limpio = "".join(c for c in titulo_video if c.isalnum() or c in (' ', '_', '-')).strip()

            archivo_servidor = os.path.join(CARPETA_DESCARGAS, f'{nombre_unico}.{extension_final}')
            nombre_descarga_usuario = f'{titulo_limpio}.{extension_final}'

            # Función de seguridad para borrar el archivo del servidor INMEDIATAMENTE después de enviarlo al usuario
            @after_this_request
            def eliminar_archivo_temporal(response):
                try:
                    if os.path.exists(archivo_servidor):
                        os.remove(archivo_servidor)
                except Exception as e:
                    print(f"Error al eliminar archivo temporal: {e}")
                return response

            # Envía el archivo forzando la descarga directa e ignorando la previsualización del navegador
            return send_file(
                archivo_servidor, 
                as_attachment=True, 
                download_name=nombre_descarga_usuario,
                mimetype='application/octet-stream'
            )

        except Exception as e:
            return f"Ocurrió un error en la conversión: {e}", 500

    return render_template('index.html')

if __name__ == '__main__':
    # Configuración de puerto dinámica requerida por plataformas de hosting como Render
    puerto = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=puerto)
