import os
import secrets
from flask import Flask, render_template, request, send_file, after_this_request
import yt_dlp

app = Flask(__name__)

# Carpeta temporal donde se procesarán las descargas
CARPETA_DESCARGAS = os.path.join(os.getcwd(), 'descargas_temporales')
os.makedirs(CARPETA_DESCARGAS, exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form.get('url')
        formato = request.form.get('formato') # Puede ser 'mp4' o 'mp3'
        
        if not url:
            return "Por favor, introduce una URL válida.", 400

        # Generamos un nombre único temporal para evitar conflictos entre usuarios
        nombre_unico = secrets.token_hex(8)
        
        # Configuración base de yt-dlp según la elección del usuario
        if formato == 'mp3':
            opciones = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(CARPETA_DESCARGAS, f'{nombre_unico}.%(ext)s'),
                'cookiefile': 'www.youtube.com_cookies.txt',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }
            extension_final = 'mp3'
        else: # MP4 por defecto (REGLA FLEXIBLE INCLUIDA AQUÍ)
            opciones = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'cookiefile': 'www.youtube.com_cookies.txt',
                'merge_output_format': 'mp4',
                'outtmpl': os.path.join(CARPETA_DESCARGAS, f'{nombre_unico}.%(ext)s'),
            }
            extension_final = 'mp4'

        try:
            # Descarga del archivo en el servidor
            with yt_dlp.YoutubeDL(opciones) as ydl:
                info = ydl.extract_info(url, download=True)
                # Obtenemos el título original del video para el usuario
                titulo_video = info.get('title', 'video_descargado')
                # Limpiamos caracteres raros del título para evitar errores de descarga
                titulo_limpio = "".join(c for c in titulo_video if c.isalnum() or c in (' ', '_', '-')).strip()

            archivo_servidor = os.path.join(CARPETA_DESCARGAS, f'{nombre_unico}.{extension_final}')
            nombre_descarga_usuario = f'{titulo_limpio}.{extension_final}'

            # Función para borrar el archivo del servidor INMEDIATAMENTE después de enviarlo
            @after_this_request
            def eliminar_archivo_temporal(response):
                try:
                    if os.path.exists(archivo_servidor):
                        os.remove(archivo_servidor)
                except Exception as e:
                    print(f"Error al eliminar archivo temporal: {e}")
                return response

            # Envía el archivo forzando la descarga directa para que no falle el MP4
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
    puerto = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=puerto)
