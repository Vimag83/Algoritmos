
import os
import bibtexparser
import re
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from bibtexparser.bparser import BibTexParser

# --- Funciones Auxiliares (copiadas de analizador_similitud.py) ---

def cargar_base_de_datos(ruta_archivo_bib):
    """Carga una base de datos BibTeX desde un archivo."""
    if not os.path.exists(ruta_archivo_bib):
        print(f"Error: El archivo {ruta_archivo_bib} no fue encontrado.")
        return None
    with open(ruta_archivo_bib, 'r', encoding='utf-8') as bibtex_file:
        parser = BibTexParser(common_strings=False)
        parser.ignore_errors = True
        return bibtexparser.load(bibtex_file, parser=parser)

def encontrar_articulos_con_abstract(db):
    """Encuentra y devuelve una lista de artículos que tienen un abstract."""
    return [entrada for entrada in db.entries if 'abstract' in entrada and entrada['abstract'].strip()]

# --- Requerimiento 3: Funciones Principales ---

def calcular_frecuencia_palabras_dadas(abstracts, palabras_clave):
    """
    Parte 1: Calcula la frecuencia de aparición de una lista dada de palabras clave.
    """
    # Se combinan todos los abstracts en un solo texto en minúsculas.
    texto_completo = ' '.join(abstracts).lower()
    
    frecuencias = {}
    # Para cada palabra clave, se cuentan sus apariciones en el texto completo.
    for palabra in palabras_clave:
        # Se usa re.findall para contar solapamientos y asegurar que se cuenten palabras completas.
        frecuencias[palabra] = len(re.findall(r'\b' + re.escape(palabra.lower()) + r'\b', texto_completo))
    
    return frecuencias

def generar_nuevas_palabras_clave(abstracts, num_palabras=15):
    """
    Parte 2: Analiza todos los abstracts y genera un listado de nuevas palabras asociadas.
    Se utiliza el algoritmo TF-IDF para encontrar los términos más significativos.
    """
    # Se configura el vectorizador TF-IDF, indicando que use stop words en inglés.
    # Las stop words son palabras comunes como 'the', 'a', 'is' que no aportan significado.
    vectorizer = TfidfVectorizer(stop_words='english', max_features=num_palabras)
    
    # Se ajusta el modelo a los abstracts.
    vectorizer.fit_transform(abstracts)
    
    # Se obtienen los nombres de las características (las palabras clave generadas).
    palabras_generadas = vectorizer.get_feature_names_out()
    
    return list(palabras_generadas)

def calcular_precision_nuevas_palabras(palabras_generadas, palabras_originales):
    """
    Parte 3: Determina qué tan precisas son las nuevas palabras generadas.
    La precisión se calcula como la proporción de palabras generadas que estaban en la lista original.
    """
    # Se convierten ambas listas a conjuntos para una comparación eficiente.
    set_generadas = set(palabras_generadas)
    set_originales = set(palabra.lower() for palabra in palabras_originales)
    
    # Se encuentra la intersección (palabras en común).
    palabras_comunes = set_generadas.intersection(set_originales)
    
    # Se calcula la precisión.
    precision = len(palabras_comunes) / len(palabras_generadas) if len(palabras_generadas) > 0 else 0
    
    return precision, list(palabras_comunes)

# --- Punto de Entrada del Script ---

if __name__ == '__main__':
    # --- Configuración Inicial ---
    ruta_bib = os.path.join('..', 'datos', 'procesados', 'articulos_unicos.bib')
    db = cargar_base_de_datos(ruta_bib)

    # Palabras clave dadas en el requerimiento.
    palabras_clave_dadas = [
        "Generative models", "Prompting", "Machine learning", "Multimodality", 
        "Fine-tuning", "Training data", "Algorithmic bias", "Explainability", 
        "Transparency", "Ethics", "Privacy", "Personalization", 
        "Human-AI interaction", "AI literacy", "Co-creation"
    ]

    if db:
        articulos_con_abstract = encontrar_articulos_con_abstract(db)
        if articulos_con_abstract:
            abstracts = [entry['abstract'] for entry in articulos_con_abstract]

            # --- Ejecución y Resultados ---
            print("--- Requerimiento 3: Análisis de Frecuencia de Palabras ---")

            # 1. Calcular frecuencia de palabras dadas
            frecuencias = calcular_frecuencia_palabras_dadas(abstracts, palabras_clave_dadas)
            print("\n1. Frecuencia de palabras clave dadas en todos los resúmenes:")
            for palabra, freq in frecuencias.items():
                print(f"  - {palabra}: {freq}")

            # 2. Generar nuevas palabras clave
            palabras_generadas = generar_nuevas_palabras_clave(abstracts, num_palabras=15)
            print("\n2. Nuevas palabras clave generadas con TF-IDF (Top 15):")
            print(f"  {palabras_generadas}")

            # 3. Calcular precisión de las nuevas palabras
            precision, comunes = calcular_precision_nuevas_palabras(palabras_generadas, palabras_clave_dadas)
            print("\n3. Precisión de las palabras generadas:")
            print(f"   - Precisión: {precision:.2%}")
            print(f"   - Palabras comunes encontradas: {comunes}")

        else:
            print("No se encontraron artículos con resúmenes en la base de datos.")
