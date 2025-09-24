import os
import bibtexparser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bparser import BibTexParser

def unificar_y_deduplicar(directorio_descargas, archivo_unicos, archivo_duplicados):
    """
    Esta función lee todos los archivos .bib de un directorio, los unifica,
    elimina las entradas duplicadas basadas en el título y guarda las entradas
    únicas y duplicadas en archivos separados.

    Args:
        directorio_descargas (str): La ruta al directorio que contiene los archivos .bib descargados.
        archivo_unicos (str): La ruta al archivo donde se guardarán las entradas únicas.
        archivo_duplicados (str): La ruta al archivo donde se guardarán las entradas duplicadas.
    """
    
    # --- 1. Leer y combinar todos los archivos .bib ---
    # Se crea un parser de BibTeX para poder leer los archivos.
    # Se especifica que ignore los errores de parsing para que el proceso no se detenga
    # si un archivo tiene un formato ligeramente incorrecto.
    parser = BibTexParser(common_strings=False)
    parser.ignore_errors = True
    
    # Se crea una base de datos BibTeX vacía para almacenar todas las entradas.
    db_combinada = bibtexparser.bibdatabase.BibDatabase()
    
    # Se itera sobre cada archivo en el directorio de descargas.
    for nombre_archivo in os.listdir(directorio_descargas):
        if nombre_archivo.endswith(".bib"):
            ruta_archivo = os.path.join(directorio_descargas, nombre_archivo)
            print(f"Procesando archivo: {nombre_archivo}...")
            
            # Se abre y se parsea cada archivo .bib.
            with open(ruta_archivo, 'r', encoding='utf-8') as bibtex_file:
                db = bibtexparser.load(bibtex_file, parser=parser)
                # Se añaden las entradas del archivo a la base de datos combinada.
                db_combinada.entries.extend(db.entries)
    
    print(f"\nSe encontraron un total de {len(db_combinada.entries)} entradas en todos los archivos.")

    # --- 2. Identificar y separar duplicados ---
    # Se utilizan un diccionario y un conjunto para rastrear los títulos que ya se han visto.
    titulos_vistos = set()
    entradas_unicas = []
    entradas_duplicadas = []
    
    # Se itera sobre cada entrada en la base de datos combinada.
    for entrada in db_combinada.entries:
        # Se extrae el título, se convierte a minúsculas y se eliminan espacios
        # para una comparación más robusta.
        if 'title' in entrada:
            titulo = entrada['title'].strip().lower()
            
            # Si el título no se ha visto antes, se considera una entrada única.
            if titulo not in titulos_vistos:
                titulos_vistos.add(titulo)
                entradas_unicas.append(entrada)
            else:
                # Si el título ya se ha visto, se marca como duplicado.
                entradas_duplicadas.append(entrada)
        else:
            # Si una entrada no tiene título, se considera única para no perderla,
            # aunque podría ser un dato incompleto.
            entradas_unicas.append(entrada)

    print(f"Proceso de deduplicación completado.")
    print(f" - Entradas únicas encontradas: {len(entradas_unicas)}")
    print(f" - Entradas duplicadas encontradas: {len(entradas_duplicadas)}")

    # --- 3. Guardar los resultados en archivos separados ---
    # Se configura un escritor de BibTeX para guardar los archivos de salida.
    writer = BibTexWriter()
    writer.indent = '    '  # Se usan 4 espacios para la indentación.
    writer.comma_first = False  # El formato es: "campo = {valor},"

    # Se guardan las entradas únicas.
    db_unicas = bibtexparser.bibdatabase.BibDatabase()
    db_unicas.entries = entradas_unicas
    with open(archivo_unicos, 'w', encoding='utf-8') as bibfile:
        bibfile.write(writer.write(db_unicas))
    print(f"\nArchivo de entradas únicas guardado en: {archivo_unicos}")

    # Se guardan las entradas duplicadas.
    db_duplicadas = bibtexparser.bibdatabase.BibDatabase()
    db_duplicadas.entries = entradas_duplicadas
    with open(archivo_duplicados, 'w', encoding='utf-8') as bibfile:
        bibfile.write(writer.write(db_duplicadas))
    print(f"Archivo de entradas duplicadas guardado en: {archivo_duplicados}")


# --- Punto de entrada del script ---
if __name__ == '__main__':
    # Se definen las rutas relativas para los directorios de datos.
    # Esto hace que el script sea más portable y no dependa de rutas absolutas.
    directorio_base = os.path.join('..', 'datos')
    directorio_descargas = os.path.join(directorio_base, 'descargas')
    directorio_procesados = os.path.join(directorio_base, 'procesados')
    
    # Se crean los directorios si no existen.
    os.makedirs(directorio_descargas, exist_ok=True)
    os.makedirs(directorio_procesados, exist_ok=True)
    
    # Se definen los nombres de los archivos de salida.
    archivo_unicos = os.path.join(directorio_procesados, 'articulos_unicos.bib')
    archivo_duplicados = os.path.join(directorio_procesados, 'articulos_duplicados.bib')
    
    # Se llama a la función principal con las rutas definidas.
    unificar_y_deduplicar(directorio_descargas, archivo_unicos, archivo_duplicados)
