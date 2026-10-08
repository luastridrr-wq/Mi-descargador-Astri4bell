

import os
import secrets

from flask import Flask, render_template, request, send_file, after_this_request
import yt_dlp


app = Flask(__name__)


# ============================================================
# CARPETA TEMPORAL
# ============================================================

CARPETA_DESCARGAS = os.path.join(
    os.getcwd(),
    "descargas_temporales"
)

os.makedirs(CARPETA_DESCARGAS, exist_ok=True)


# ============================================================
# LIMPIAR NOMBRE DEL ARCHIVO
# ============================================================

def limpiar_nombre(nombre):
    """
    Limpia el título del video para utilizarlo como
    nombre del archivo descargado.
    """

    nombre = "".join(
        c for c in nombre
        if c.isalnum() or c in (" ", "_", "-")
    )

    nombre = nombre.strip()

    if not nombre:
        nombre = "video_descargado"

    return nombre


# ============================================================
# PÁGINA PRINCIPAL
# ============================================================

@app.route("/", methods=["GET", "POST"])
def index():

    if request.method == "POST":

        url = request.form.get("url", "").strip()
        formato = request.form.get("formato", "mp4").lower()

        if not url:
            return "Por favor, introduce una URL válida.", 400

        if formato not in ("mp4", "mp3"):
            return "Formato no válido.", 400


        # ====================================================
        # NOMBRE TEMPORAL ÚNICO
        # ====================================================

        nombre_unico = secrets.token_hex(8)


        # ====================================================
        # MP3
        # ====================================================

        if formato == "mp3":

            opciones = {

                # Mejor audio disponible
                "format": "bestaudio/best",

                "outtmpl": os.path.join(
                    CARPETA_DESCARGAS,
                    f"{nombre_unico}.%(ext)s"
                ),

                # Cookies de YouTube
                "cookiefile": "www.youtube.com_cookies.txt",

                # Convertir a MP3
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],

                "noplaylist": True,

                "quiet": False,
                "no_warnings": False,
            }

            extension_final = "mp3"


        # ====================================================
        # MP4
        # ====================================================

        else:

            opciones = {

                # ------------------------------------------------
                # ORDEN DE FORMATOS
                #
                # 1. Mejor video MP4 + mejor audio M4A
                #
                # 2. Mejor archivo MP4 ya combinado
                #
                # 3. Mejor video + mejor audio disponibles,
                #    aunque sean WebM/Opus/etc.
                #
                # 4. Cualquier mejor formato disponible
                # ------------------------------------------------

                "format": (
                    "bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
                    "best[ext=mp4]/"
                    "bestvideo+bestaudio/"
                    "best"
                ),

                "outtmpl": os.path.join(
                    CARPETA_DESCARGAS,
                    f"{nombre_unico}.%(ext)s"
                ),

                # Fuerza el contenedor final a MP4 cuando
                # sea posible mediante FFmpeg.
                "merge_output_format": "mp4",

                # Cookies
                "cookiefile": "www.youtube.com_cookies.txt",

                # No descargar listas de reproducción
                "noplaylist": True,

                "quiet": False,
                "no_warnings": False,
            }

            extension_final = "mp4"


        # ====================================================
        # DESCARGA
        # ====================================================

        try:

            with yt_dlp.YoutubeDL(opciones) as ydl:

                info = ydl.extract_info(
                    url,
                    download=True
                )

                if not info:
                    return (
                        "No se pudo obtener información del video.",
                        500
                    )

                titulo_video = info.get(
                    "title",
                    "video_descargado"
                )

                titulo_limpio = limpiar_nombre(
                    titulo_video
                )


            # =================================================
            # BUSCAR EL ARCHIVO MP4 ESPERADO
            # =================================================

            archivo_servidor = os.path.join(
                CARPETA_DESCARGAS,
                f"{nombre_unico}.{extension_final}"
            )


            # =================================================
            # SI NO EXISTE, BUSCAR CUALQUIER ARCHIVO GENERADO
            # =================================================

            if not os.path.exists(archivo_servidor):

                archivos_encontrados = []

                for archivo in os.listdir(CARPETA_DESCARGAS):

                    if archivo.startswith(nombre_unico + "."):

                        ruta = os.path.join(
                            CARPETA_DESCARGAS,
                            archivo
                        )

                        if os.path.isfile(ruta):
                            archivos_encontrados.append(ruta)


                if not archivos_encontrados:

                    return (
                        "La descarga terminó, pero no se "
                        "encontró el archivo generado. "
                        "Comprueba que FFmpeg esté instalado "
                        "correctamente.",
                        500
                    )


                # Si por alguna razón no quedó como MP4,
                # utilizamos el archivo encontrado.
                archivo_servidor = archivos_encontrados[0]


            # =================================================
            # NOMBRE FINAL
            # =================================================

            nombre_descarga_usuario = (
                f"{titulo_limpio}.{extension_final}"
            )


            # =================================================
            # BORRAR ARCHIVO DESPUÉS DE ENVIARLO
            # =================================================

            @after_this_request
            def eliminar_archivo_temporal(response):

                try:

                    if os.path.exists(archivo_servidor):
                        os.remove(archivo_servidor)

                except Exception as e:

                    print(
                        "Error al eliminar archivo temporal:",
                        e
                    )

                return response


            # =================================================
            # ENVIAR ARCHIVO AL USUARIO
            # =================================================

            return send_file(

                archivo_servidor,

                as_attachment=True,

                download_name=nombre_descarga_usuario,

                mimetype=(
                    "audio/mpeg"
                    if formato == "mp3"
                    else "video/mp4"
                )
            )


        # ====================================================
        # ERROR ESPECÍFICO DE YT-DLP
        # ====================================================

        except yt_dlp.utils.DownloadError as e:

            print("\n========== ERROR YT-DLP ==========")
            print(e)
            print("==================================\n")

            return (
                "No se pudo descargar este video.<br><br>"
                f"<strong>Detalles:</strong><br>{e}",
                500
            )


        # ====================================================
        # OTROS ERRORES
        # ====================================================

        except Exception as e:

            print("\n========== ERROR ==========")
            print(e)
            print("===========================\n")

            return (
                "Ocurrió un error durante la "
                f"descarga/conversión:<br><br>{e}",
                500
            )


    # ========================================================
    # MOSTRAR PÁGINA
    # ========================================================

    return render_template("index.html")


# ============================================================
# INICIAR SERVIDOR
# ============================================================

if __name__ == "__main__":

    puerto = int(
        os.environ.get("PORT", 5000)
    )

    app.run(
        host="0.0.0.0",
        port=puerto
    )
