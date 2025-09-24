import bibtexparser
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# --- Constantes ---
# Se calcula la ruta raíz del proyecto para que funcione independientemente de dónde se ejecute
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
BIB_FILE_PATH = os.path.join(ROOT_DIR, 'datos', 'procesados', 'articulos_unicos.bib')

# --- Funciones de Lógica Principal ---

def cargar_articulos():
    """
    Carga los artículos desde el archivo .bib unificado.
    """
    if not os.path.exists(BIB_FILE_PATH):
        print(f"[ERROR] El archivo no se encuentra en: {BIB_FILE_PATH}")
        return []

    with open(BIB_FILE_PATH, 'r', encoding='utf-8') as bibtex_file:
        parser = bibtexparser.bparser.BibTexParser(common_strings=True)
        bib_database = bibtexparser.load(bibtex_file, parser=parser)
    
    print(f"[INFO] Se cargaron {len(bib_database.entries)} artículos.")
    return bib_database.entries

def calcular_distancia_levenshtein(s1, s2):
    """
    Calcula la distancia de Levenshtein entre dos strings.
    """
    if len(s1) < len(s2):
        return calcular_distancia_levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def analizar_similitud_levenshtein(articulos, id1, id2):
    """
    Encuentra dos artículos y calcula la similitud de sus abstracts usando Levenshtein.
    """
    articulo1 = next((a for a in articulos if a.get('ID') == id1), None)
    articulo2 = next((a for a in articulos if a.get('ID') == id2), None)

    if not articulo1 or not articulo2:
        return {"error": "No se encontró uno o ambos artículos."}
    abstract1 = articulo1.get('abstract', '')
    abstract2 = articulo2.get('abstract', '')
    if not abstract1 or not abstract2:
        return {"error": "Uno o ambos artículos no tienen abstract."}

    distancia = calcular_distancia_levenshtein(abstract1, abstract2)
    longitud_max = max(len(abstract1), len(abstract2))
    similitud = 1 - (distancia / longitud_max) if longitud_max > 0 else 1.0

    return {
        "articulo1_id": id1,
        "articulo2_id": id2,
        "algoritmo": "Distancia de Levenshtein",
        "distancia": distancia,
        "similitud": round(similitud, 4)
    }

def analizar_similitud_coseno(articulos, id1, id2):
    """
    Encuentra dos artículos y calcula la similitud de sus abstracts usando Similitud de Coseno con TF-IDF.
    """
    articulo1 = next((a for a in articulos if a.get('ID') == id1), None)
    articulo2 = next((a for a in articulos if a.get('ID') == id2), None)

    if not articulo1 or not articulo2:
        return {"error": "No se encontró uno o ambos artículos."}
    abstract1 = articulo1.get('abstract', '')
    abstract2 = articulo2.get('abstract', '')
    if not abstract1 or not abstract2:
        return {"error": "Uno o ambos artículos no tienen abstract."}

    # Vectorizar los textos
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([abstract1, abstract2])
    
    # Calcular la similitud de coseno
    similitud = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
    
    return {
        "articulo1_id": id1,
        "articulo2_id": id2,
        "algoritmo": "Similitud de Coseno (TF-IDF)",
        "similitud": round(similitud[0][0], 4)
    }

def analizar_similitud_jaccard(articulos, id1, id2):
    """
    Encuentra dos artículos y calcula la similitud de sus abstracts usando el índice de Jaccard.
    """
    articulo1 = next((a for a in articulos if a.get('ID') == id1), None)
    articulo2 = next((a for a in articulos if a.get('ID') == id2), None)

    if not articulo1 or not articulo2:
        return {"error": "No se encontró uno o ambos artículos."}
    abstract1 = articulo1.get('abstract', '')
    abstract2 = articulo2.get('abstract', '')
    if not abstract1 or not abstract2:
        return {"error": "Uno o ambos artículos no tienen abstract."}

    # Tokenización simple: convertir a minúsculas y dividir por espacios
    a = set(abstract1.lower().split())
    b = set(abstract2.lower().split())
    
    interseccion = len(a.intersection(b))
    union = len(a.union(b))
    
    similitud = interseccion / union if union != 0 else 0
    
    return {
        "articulo1_id": id1,
        "articulo2_id": id2,
        "algoritmo": "Índice de Jaccard",
        "similitud": round(similitud, 4)
    }

# --- Ejemplo de uso (para pruebas) ---
if __name__ == '__main__':
    lista_articulos = cargar_articulos()
    if lista_articulos and len(lista_articulos) >= 2:
        id_articulo_1 = lista_articulos[0].get('ID')
        id_articulo_2 = lista_articulos[1].get('ID')

        print(f"\nComparando artículo {id_articulo_1} y {id_articulo_2}")

        resultado_lev = analizar_similitud_levenshtein(lista_articulos, id_articulo_1, id_articulo_2)
        print("\n--- Resultado con Levenshtein ---")
        print(resultado_lev)

        resultado_cos = analizar_similitud_coseno(lista_articulos, id_articulo_1, id_articulo_2)
        print("\n--- Resultado con Similitud de Coseno ---")
        print(resultado_cos)

        resultado_jac = analizar_similitud_jaccard(lista_articulos, id_articulo_1, id_articulo_2)
        print("\n--- Resultado con Índice de Jaccard ---")
        print(resultado_jac)
