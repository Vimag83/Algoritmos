import time
import random
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains

# --- Constantes específicas de SAGE ---
BASE_URL = "https://journals-sagepub-com.crai.referencistas.com/"
SEARCH_TERM = "generative artificial intelligence"
MAX_RETRIES = 3
WAIT_TIME = 10

def escribir_como_humano(elemento, texto):
    """
    Simula escritura humana.
    """
    for caracter in texto:
        elemento.send_keys(caracter)
        time.sleep(random.uniform(0.1, 0.3))

def wait_for_new_file(download_path, timeout=20):
    """
    Espera a que se complete una nueva descarga.
    """
    print(f"[SAGE-LOG] Esperando nueva descarga en: {download_path}")
    start_time = time.time()
    initial_files = set(os.listdir(download_path)) if os.path.exists(download_path) else set()
    
    while time.time() - start_time < timeout:
        time.sleep(1)
        try:
            current_files = set(os.listdir(download_path))
            new_files = current_files - initial_files
            if new_files:
                newest_file = max([os.path.join(download_path, f) for f in new_files], key=os.path.getctime)
                # Esperar a que el archivo termine de escribirse
                last_size = -1
                while last_size != os.path.getsize(newest_file):
                    last_size = os.path.getsize(newest_file)
                    time.sleep(0.5)
                print(f"[SAGE-LOG] Nuevo archivo detectado y estable: {new_files}")
                return True
        except Exception as e:
            print(f"[SAGE-LOG] Error verificando descargas: {e}")
    
    return False

def process_page(driver, page_num, download_path):
    """
    Procesa una página individual.
    """
    try:
        # Primero, intentar remover elementos que puedan interferir
        driver.execute_script("""
            var entries = document.getElementsByClassName('csl-entry');
            for(var i=0; i<entries.length; i++) {
                entries[i].style.pointerEvents = 'none';
            }
        """)

        # Hacer scroll hasta el checkbox y esperar un momento
        select_all_checkbox = WebDriverWait(driver, WAIT_TIME).until(
            EC.presence_of_element_located((By.ID, "action-bar-select-all"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", select_all_checkbox)
        time.sleep(2)

        # Intentar diferentes métodos para hacer clic en el checkbox
        try:
            # Método 1: Clic directo
            select_all_checkbox.click()
        except:
            try:
                # Método 2: Clic con JavaScript
                driver.execute_script("arguments[0].click();", select_all_checkbox)
            except:
                # Método 3: Forzar el estado del checkbox
                driver.execute_script("""
                    var checkbox = document.getElementById('action-bar-select-all');
                    checkbox.checked = true;
                    checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                """)

        time.sleep(2)
        time.sleep(1)


        # Verificar que el checkbox está marcado
        if not select_all_checkbox.is_selected():
            print("[SAGE-LOG] El checkbox no se marcó correctamente.")
            return False

        # Exportar
        export_button = WebDriverWait(driver, WAIT_TIME).until(
            EC.element_to_be_clickable((By.XPATH, "//a[@data-id='srp-export-citations']"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", export_button)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", export_button)

        # Seleccionar formato BibTeX
        select_element = WebDriverWait(driver, WAIT_TIME).until(
            EC.element_to_be_clickable((By.ID, "citation-format"))
        )
        Select(select_element).select_by_value("bibtex")
        time.sleep(2)

        # Verificar que se seleccionó BibTeX
        if select_element.get_attribute("value") != "bibtex":
            print("[SAGE-LOG] No se pudo seleccionar el formato BibTeX.")
            return False

        # Descargar
        download_button = WebDriverWait(driver, WAIT_TIME).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'download__btn')]"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", download_button)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", download_button)

        # Esperar la descarga
        if not wait_for_new_file(download_path):
            print("[SAGE-LOG] No se detectó la descarga del archivo.")
            return False

        # Cerrar modal
        try:
            close_button = WebDriverWait(driver, WAIT_TIME).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@data-dismiss='modal']"))
            )
            driver.execute_script("arguments[0].click();", close_button)
            time.sleep(2)
        except:
            # Si no se puede cerrar el modal normalmente, intentar forzar el cierre
            try:
                driver.execute_script("""
                    document.body.classList.remove('modal-open');
                    var modals = document.getElementsByClassName('modal');
                    for(var i=0; i<modals.length; i++) {
                        modals[i].remove();
                    }
                    var modalBackdrops = document.getElementsByClassName('modal-backdrop');
                    for(var i=0; i<modalBackdrops.length; i++) {
                        modalBackdrops[i].remove();
                    }
                """)
                print("[SAGE-LOG] Modal cerrado forzadamente.")
            except:
                print("[SAGE-LOG] No se pudo cerrar el modal, pero la descarga fue exitosa.")

        return True

    except Exception as e:
        print(f"Error procesando página {page_num}: {e}")
        return False

def navigate_to_next_page(driver, current_page):
    """
    Navega a la siguiente página con múltiples estrategias de fallback.
    """
    try:
        print(f"[SAGE-LOG] Intentando navegar de página {current_page} a {current_page + 1}...")
        
        # Primero, hacer scroll hacia arriba para asegurar que la paginación sea visible
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        
        # Estrategia 1: Buscar el botón "Next" específico
        next_selectors = [
            "//li[contains(@class, 'page-item__arrow--next')]/a[not(contains(@class, 'disabled'))]",
            "//a[contains(@class, 'page-link') and contains(@aria-label, 'Next')]",
            "//a[contains(text(), 'Next')]",
            "//li[contains(@class, 'next')]/a",
            f"//a[contains(@href, 'page={current_page + 1}')]"
        ]
        
        next_button = None
        for selector in next_selectors:
            try:
                next_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                print(f"[SAGE-LOG] Botón 'Next' encontrado con selector: {selector}")
                break
            except:
                continue
        
        if not next_button:
            print("[SAGE-LOG] No se encontró botón 'Next'. Intentando navegación directa por URL...")
            # Estrategia 2: Navegación directa modificando la URL
            current_url = driver.current_url
            if 'page=' in current_url:
                new_url = current_url.replace(f'page={current_page}', f'page={current_page + 1}')
            else:
                # Si no hay parámetro page, agregarlo
                separator = '&' if '?' in current_url else '?'
                new_url = f"{current_url}{separator}page={current_page + 1}"
            
            print(f"[SAGE-LOG] Navegando directamente a: {new_url}")
            driver.get(new_url)
            time.sleep(3)
            
        else:
            # Usar el botón encontrado
            current_url = driver.current_url
            
            # Hacer scroll al botón y asegurar que sea visible
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", next_button)
            time.sleep(1)
            
            # Intentar diferentes métodos de clic
            try:
                # Método 1: Clic directo
                next_button.click()
                print("[SAGE-LOG] Clic directo en botón 'Next' exitoso")
            except Exception as e:
                print(f"[SAGE-LOG] Clic directo falló: {e}. Intentando con JavaScript...")
                try:
                    # Método 2: Clic con JavaScript
                    driver.execute_script("arguments[0].click();", next_button)
                    print("[SAGE-LOG] Clic con JavaScript exitoso")
                except Exception as e2:
                    print(f"[SAGE-LOG] Clic con JavaScript falló: {e2}")
                    return False
            
            time.sleep(3)
        
        # Verificar que la página cambió
        max_wait = 10
        wait_count = 0
        while wait_count < max_wait:
            current_new_url = driver.current_url
            if current_new_url != current_url:
                print(f"[SAGE-LOG] URL cambió exitosamente a: {current_new_url}")
                break
            time.sleep(1)
            wait_count += 1
        
        if wait_count >= max_wait:
            print("[SAGE-LOG] La URL no cambió después de hacer clic. Verificando contenido...")
            
        # Verificar que los elementos de la nueva página están presentes
        try:
            # Esperar a que aparezca el checkbox de seleccionar todo
            WebDriverWait(driver, WAIT_TIME).until(
                EC.presence_of_element_located((By.ID, "action-bar-select-all"))
            )
            
            # Verificar que hay resultados en la nueva página
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "search-result"))
            )
            
            print(f"[SAGE-LOG] Navegación exitosa a página {current_page + 1}")
            return True
            
        except TimeoutException:
            print("[SAGE-LOG] No se encontraron elementos esperados en la nueva página")
            
            # Verificar si llegamos al final de las páginas
            try:
                # Buscar indicadores de que no hay más páginas
                no_more_pages_indicators = [
                    "//li[contains(@class, 'page-item__arrow--next') and contains(@class, 'disabled')]",
                    "//span[contains(text(), 'No more results')]",
                    "//div[contains(text(), 'End of results')]"
                ]
                
                for indicator in no_more_pages_indicators:
                    if driver.find_elements(By.XPATH, indicator):
                        print("[SAGE-LOG] Se alcanzó el final de los resultados")
                        return False
                        
            except:
                pass
                
            return False
        
    except Exception as e:
        print(f"[SAGE-LOG] Error durante navegación: {e}")
        import traceback
        traceback.print_exc()
        return False
    
def perform_login(driver, email: str, password: str):
    """
    Realiza el proceso de login en la plataforma SAGE.
    """
    print("[SAGE-LOG] Iniciando login...")
    print(f"[SAGE-LOG] Navegando a SAGE: {BASE_URL}")
    driver.get(BASE_URL)

    try:
        print("[SAGE-LOG] Esperando el botón de inicio de sesión de Google...")
        google_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, "btn-google"))
        )
        print("[SAGE-LOG] Botón de Google encontrado. Haciendo clic...")
        google_button.click()

        print("[SAGE-LOG] Buscando el campo de correo electrónico...")
        username_field = WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.ID, "identifierId"))
        )
        print("[SAGE-LOG] Campo de correo encontrado. Escribiendo email...")
        escribir_como_humano(username_field, email)
        username_field.send_keys(Keys.RETURN)
        time.sleep(2)

        print("[SAGE-LOG] Buscando el campo de contraseña...")
        password_field = WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.NAME, "Passwd"))
        )
        print("[SAGE-LOG] Campo de contraseña encontrado. Escribiendo contraseña...")
        escribir_como_humano(password_field, password)
        password_field.send_keys(Keys.RETURN)
        time.sleep(5)

        # Aceptar cookies si aparecen
        try:
            cookie_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept')]"))
            )
            cookie_button.click()
            print("[SAGE-LOG] Cookies aceptadas.")
        except:
            print("[SAGE-LOG] No se encontró botón de cookies o ya estaban aceptadas.")

        print("[SAGE-LOG] Login completado exitosamente.")

    except Exception as e:
        print(f"[SAGE-LOG] Error durante el login: {e}")
        raise

def search_and_download(driver, max_pages: int, download_path: str, continue_last: bool = True):
    """
    Versión mejorada de búsqueda y descarga con mejor manejo de navegación.
    """
    try:
        # Realizar búsqueda
        print(f'[SAGE-LOG] Realizando búsqueda del término: "{SEARCH_TERM}"')
        search_box = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "AllField35ea26a9-ec16-4bde-9652-17b798d5b6750"))
        )
        escribir_como_humano(search_box, SEARCH_TERM)
        search_box.send_keys(Keys.RETURN)
        time.sleep(5)  # Aumentar tiempo de espera después de la búsqueda

        # Aceptar cookies si aparecen después de la búsqueda
        try:
            cookie_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept')]"))
            )
            cookie_button.click()
            print("[SAGE-LOG] Cookies post-búsqueda aceptadas.")
        except:
            pass

        # Verificar cuántas páginas hay disponibles
        try:
            # Buscar información de paginación
            pagination_info = driver.find_elements(By.XPATH, "//span[contains(@class, 'pagination-info')]")
            if pagination_info:
                print(f"[SAGE-LOG] Información de paginación: {pagination_info[0].text}")
        except:
            pass

        # Procesar páginas
        current_page = 1
        while current_page <= max_pages:
            print(f"\n--- [SAGE-LOG] Procesando página {current_page} de {max_pages} ---")
            
            # Verificar que estamos en la página correcta
            current_url = driver.current_url
            print(f"[SAGE-LOG] URL actual: {current_url}")
            
            retry_count = 0
            page_success = False
            
            while retry_count < MAX_RETRIES and not page_success:
                try:
                    if process_page(driver, current_page, download_path):
                        page_success = True
                        print(f"[SAGE-LOG] Página {current_page} procesada exitosamente.")
                    else:
                        retry_count += 1
                        if retry_count < MAX_RETRIES:
                            print(f"[SAGE-LOG] Reintentando página {current_page} (intento {retry_count + 1}/{MAX_RETRIES})...")
                            time.sleep(3)
                        else:
                            print(f"[SAGE-LOG] No se pudo procesar la página {current_page} después de {MAX_RETRIES} intentos.")
                            return
                except Exception as e:
                    print(f"[SAGE-LOG] Error procesando página {current_page}: {e}")
                    retry_count += 1
                    if retry_count < MAX_RETRIES:
                        time.sleep(3)
                    else:
                        print(f"[SAGE-LOG] Demasiados errores en página {current_page}. Deteniendo proceso.")
                        return

            if page_success and current_page < max_pages:
                print(f"[SAGE-LOG] Intentando navegar a la página {current_page + 1}...")
                if navigate_to_next_page(driver, current_page):
                    current_page += 1
                    time.sleep(3)  # Tiempo adicional para cargar la nueva página
                else:
                    print("[SAGE-LOG] No se pudo navegar a la siguiente página. Deteniendo proceso.")
                    break
            else:
                break

        print("\n[SAGE-LOG] Proceso de descarga completado.")

    except Exception as e:
        print(f"[SAGE-LOG] Error durante la búsqueda y descarga: {e}")
        import traceback
        traceback.print_exc()
        raise