import os
import requests
from flask import Flask, render_template, request, send_file, after_this_request
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, USLT
from mutagen.flac import FLAC
from mutagen.easyid3 import EasyID3

app = Flask(__name__)

# Configuración de carpeta temporal de trabajo
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_metadata(file_path):
    """Extrae metadatos internos del archivo de audio."""
    artist, title, album = None, None, None
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == '.mp3':
            audio = EasyID3(file_path)
            artist = audio.get('artist', [None])[0]
            title = audio.get('title', [None])[0]
            album = audio.get('album', [None])[0]
        elif ext == '.flac':
            audio = FLAC(file_path)
            artist = audio.get('artist', [None])[0]
            title = audio.get('title', [None])[0]
            album = audio.get('album', [None])[0]
    except Exception as e:
        print(f"Error leyendo metadatos: {e}")
    return artist, title, album

def get_lyrics(artist, title, album=None):
    """Busca letras en la API de LRCLIB priorizando las sincronizadas."""
    if not artist or not title:
        return None
    url = f"https://lrclib.net/api/get?artist_name={artist}&track_name={title}"
    if album:
        url += f"&album_name={album}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            # Prioridad: Letras sincronizadas > Letras planas
            return data.get('syncedLyrics') or data.get('plainLyrics')
    except Exception as e:
        print(f"Error en la API de letras: {e}")
        return None
    return None

def embed_lyrics(file_path, lyrics):
    """Inyecta las letras en los metadatos del archivo físico."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.mp3':
        audio = MP3(file_path, ID3=ID3)
        if audio.tags is None:
            audio.add_tags()
        # USLT es el estándar para letras en ID3 (MP3)
        audio.tags.add(USLT(encoding=3, lang='eng', desc='Lyrics', text=lyrics))
        audio.save()
    elif ext == '.flac':
        audio = FLAC(file_path)
        audio["LYRICS"] = lyrics
        audio.save()

@app.route('/')
def index():
    """Carga la página principal."""
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    """Ruta principal de procesamiento de archivos."""
    file = request.files.get('file')
    if not file:
        return "Error: No se subió ningún archivo", 400
    
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)
    
    # 1. Obtener metadatos automáticos
    m_artist, m_title, m_album = get_metadata(file_path)
    
    # 2. Preferencia: Datos del formulario > Metadatos > Nombre de archivo
    artist = request.form.get('artist') or m_artist
    title = request.form.get('title') or m_title
    album = request.form.get('album') or m_album
    
    if not title:
        title = os.path.splitext(file.filename)[0]
    
    # 3. Obtener letras (Manual o vía API)
    manual_lyrics = request.form.get('manual_lyrics')
    lyrics = manual_lyrics if manual_lyrics and manual_lyrics.strip() else get_lyrics(artist, title, album)

    # 4. Función de limpieza (Borra el archivo después de enviarlo)
    @after_this_request
    def remove_file(response):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            app.logger.error(f"Error eliminando archivo temporal: {e}")
        return response

    # 5. Respuesta al usuario
    if lyrics:
        embed_lyrics(file_path, lyrics)
        return send_file(file_path, as_attachment=True, download_name=file.filename)
    
    return "No se encontraron letras para esta canción. Intenta ingresando los datos manualmente.", 404

# --- CONFIGURACIÓN PARA DESPLIEGUE (RENDER / LOCAL) ---
if __name__ == '__main__':
    # Render asigna un puerto automáticamente en la variable de entorno PORT
    port = int(os.environ.get("PORT", 5001))
    # host='0.0.0.0' permite que el servicio sea accesible externamente
    app.run(host='0.0.0.0', port=port, debug=False)