import time
import random
import os
import json
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException

# --- Constantes específicas de ScienceDirect ---
BASE_URL = "https://www-sciencedirect-com.crai.referencistas.com/"
SEARCH_TERM = "generative artificial intelligence"

# --- Funciones de ayuda ---

def type_like_human(element, text: str):
    """
    Simula la escritura humana en un elemento web.
    """
    # Limpiar el campo primero
    element.clear()
    time.sleep(0.5)
    
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.1, 0.2))

def wait_for_new_file(download_path, timeout=20):
    """
    Espera a que se complete una nueva descarga.
    """
    print(f"[SD-LOG] Esperando nueva descarga en: {download_path}")
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
                print(f"[SD-LOG] Nuevo archivo detectado y estable: {new_files}")
                return True
        except Exception as e:
            print(f"[SD-LOG] Error verificando descargas: {e}")
    
    return False

# --- Lógica principal del Scraper de ScienceDirect ---

def perform_login(driver, email: str, password: str):
    """
    Realiza el proceso de login en la plataforma ScienceDirect a través del proxy.
    """
    print("[SD-LOG] Iniciando login...")
    print(f"[SD-LOG] Navegando a ScienceDirect: {BASE_URL}")
    driver.get(BASE_URL)

    print("[SD-LOG] Esperando la redirección al portal de login de la universidad...")
    try:
        print("[SD-LOG] Buscando botón de Google...")
        google_button = WebDriverWait(driver, 25).until(
            EC.element_to_be_clickable((By.ID, "btn-google"))
        )
        google_button.click()
        print("[SD-LOG] Clic en el botón de Google.")

        print("[SD-LOG] Ingresando correo electrónico...")
        username_field = WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.ID, "identifierId"))
        )
        type_like_human(username_field, email)
        username_field.send_keys(Keys.RETURN)
        
        time.sleep(random.uniform(2, 4))

        print("[SD-LOG] Ingresando contraseña...")
        password_field = WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.NAME, "Passwd"))
        )
        type_like_human(password_field, password)
        password_field.send_keys(Keys.RETURN)

        print("[SD-LOG] Login exitoso. Esperando a la redirección a ScienceDirect...")
        
        # Esperar múltiples indicadores de que la página principal cargó
        search_field_selectors = [
            (By.ID, "search-input-field"),
            (By.NAME, "qs"),
            (By.CSS_SELECTOR, "input[placeholder*='Search']"),
            (By.CSS_SELECTOR, "input[type='search']"),
            (By.XPATH, "//input[contains(@placeholder, 'Search')]")
        ]
        
        search_field = None
        for selector in search_field_selectors:
            try:
                search_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(selector)
                )
                print(f"[SD-LOG] Campo de búsqueda encontrado con selector: {selector}")
                break
            except:
                continue
        
        if search_field:
            print("[SD-LOG] Redirección a ScienceDirect completada y página principal cargada.")
        else:
            print("[SD-LOG] No se encontró el campo de búsqueda, pero continuando...")

    except TimeoutException:
        print("[SD-LOG] No se completó el flujo de login de Google a tiempo o ya estabas logueado.")
        print("[SD-LOG] Verificando si estamos en la página correcta de ScienceDirect...")
        try:
            # Verificar múltiples selectores posibles
            search_field_found = False
            for selector in search_field_selectors:
                try:
                    WebDriverWait(driver, 5).until(EC.presence_of_element_located(selector))
                    search_field_found = True
                    break
                except:
                    continue
            
            if search_field_found:
                print("[SD-LOG] Verificación exitosa, la página de ScienceDirect ya está cargada.")
            else:
                print("[SD-LOG] No se pudo encontrar el campo de búsqueda con ningún selector.")
                raise Exception("Campo de búsqueda no encontrado")
                
        except Exception as e:
            print(f"[SD-LOG] Error en verificación: {e}")
            raise
    except Exception as e:
        print(f"[SD-LOG] Ocurrió un error inesperado durante el login: {e}")
        raise

def search_and_download(driver, max_pages: int, download_path: str, continue_last: bool):
    """
    Realiza la búsqueda y descarga las citas página por página en ScienceDirect.
    """
    # Cargar el estado de la paginación
    progress_file = os.path.join(download_path, 'sd_scraping_progress.json')
    start_page = 1
    if continue_last and os.path.exists(progress_file):
        with open(progress_file, 'r') as f:
            data = json.load(f)
            start_page = data.get('last_page', 1) + 1
        print(f"[SD-LOG] Reanudando desde la página {start_page}.")

    if start_page > max_pages:
        print("[SD-LOG] Todas las páginas ya han sido procesadas.")
        return

    try:
        print(f'[SD-LOG] Realizando búsqueda del término: "{SEARCH_TERM}"')
        
        # Intentar múltiples selectores para el campo de búsqueda
        search_field_selectors = [
            (By.ID, "search-input-field"),
            (By.NAME, "qs"),
            (By.CSS_SELECTOR, "input[placeholder*='Search']"),
            (By.CSS_SELECTOR, "input[type='search']"),
            (By.XPATH, "//input[contains(@placeholder, 'Search')]"),
            (By.XPATH, "//input[contains(@class, 'search')]"),
            (By.CSS_SELECTOR, ".search-input"),
            (By.CSS_SELECTOR, "#srp-term")
        ]
        
        search_box = None
        for selector in search_field_selectors:
            try:
                print(f"[SD-LOG] Intentando encontrar campo de búsqueda con: {selector}")
                search_box = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable(selector)
                )
                print(f"[SD-LOG] Campo de búsqueda encontrado con selector: {selector}")
                break
            except Exception as e:
                print(f"[SD-LOG] Selector {selector} falló: {e}")
                continue
        
        if not search_box:
            print("[SD-LOG] No se pudo encontrar el campo de búsqueda con ningún selector.")
            print("[SD-LOG] Imprimiendo HTML de la página para diagnóstico...")
            print(driver.page_source[:2000])  # Primeros 2000 caracteres
            raise Exception("Campo de búsqueda no encontrado")
        
        # Asegurarse de que el elemento sea visible y clickeable
        driver.execute_script("arguments[0].scrollIntoView(true);", search_box)
        time.sleep(1)
        
        # Intentar hacer clic para activar el campo
        try:
            search_box.click()
            time.sleep(0.5)
        except:
            driver.execute_script("arguments[0].click();", search_box)
            time.sleep(0.5)
        
        print("[SD-LOG] Escribiendo término de búsqueda...")
        type_like_human(search_box, SEARCH_TERM)
        
        # Intentar múltiples métodos para ejecutar la búsqueda
        search_executed = False
        
        # Método 1: Presionar Enter
        try:
            search_box.send_keys(Keys.ENTER)
            time.sleep(2)
            search_executed = True
            print("[SD-LOG] Búsqueda ejecutada con Enter")
        except:
            pass
        
        # Método 2: Buscar y hacer clic en botón de búsqueda
        if not search_executed:
            search_button_selectors = [
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.XPATH, "//button[contains(@class, 'search')]"),
                (By.XPATH, "//button[contains(text(), 'Search')]"),
                (By.CSS_SELECTOR, ".search-button"),
                (By.ID, "search-button")
            ]
            
            for selector in search_button_selectors:
                try:
                    search_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable(selector)
                    )
                    search_button.click()
                    search_executed = True
                    print(f"[SD-LOG] Búsqueda ejecutada con botón: {selector}")
                    break
                except:
                    continue
        
        # Método 3: Ejecutar búsqueda con JavaScript
        if not search_executed:
            try:
                driver.execute_script("arguments[0].form.submit();", search_box)
                search_executed = True
                print("[SD-LOG] Búsqueda ejecutada con JavaScript")
            except:
                pass
        
        if not search_executed:
            raise Exception("No se pudo ejecutar la búsqueda con ningún método")

        print("[SD-LOG] Esperando que la página de resultados cargue...")
        
        # Esperar múltiples indicadores de resultados
        results_selectors = [
            (By.ID, "srp-results-list"),
            (By.CSS_SELECTOR, "li.ResultItem"),
            (By.CSS_SELECTOR, ".search-result"),
            (By.XPATH, "//div[contains(@class, 'result')]")
        ]
        
        results_found = False
        for selector in results_selectors:
            try:
                WebDriverWait(driver, 30).until(EC.presence_of_element_located(selector))
                results_found = True
                print(f"[SD-LOG] Resultados encontrados con selector: {selector}")
                break
            except:
                continue
        
        if not results_found:
            print("[SD-LOG] No se encontraron resultados con ningún selector")
            print("[SD-LOG] URL actual:", driver.current_url)
            raise Exception("No se encontraron resultados de búsqueda")
            
        print("[SD-LOG] Búsqueda completada.")

    except Exception as e:
        print(f"[SD-LOG] Error al realizar la búsqueda inicial: {e}")
        print(f"[SD-LOG] URL actual: {driver.current_url}")
        print(f"[SD-LOG] Título de la página: {driver.title}")
        raise

    for page_num in range(start_page, max_pages + 1):
        print(f"--- [SD-LOG] Procesando página {page_num} de {max_pages} ---")
        try:
            # Lógica de reintento para procesar la página
            for attempt in range(1, 4):
                try:
                    print(f"[SD-LOG] Intento {attempt}/3 para la página {page_num}.")
                    
                    print("[SD-LOG] Esperando que los resultados se carguen...")
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "li.ResultItem"))
                    )
                    
                    print("[SD-LOG] Esperando el checkbox 'Seleccionar todo'...")
                    
                    # Primero, inspeccionar qué elementos están disponibles
                    print("[SD-LOG] Inspeccionando elementos de la página...")
                    try:
                        # Buscar todos los checkboxes
                        checkboxes = driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
                        print(f"[SD-LOG] Checkboxes encontrados: {len(checkboxes)}")
                        for i, cb in enumerate(checkboxes[:5]):  # Mostrar solo los primeros 5
                            try:
                                print(f"[SD-LOG] Checkbox {i+1}: id='{cb.get_attribute('id')}', class='{cb.get_attribute('class')}', name='{cb.get_attribute('name')}'")
                            except:
                                print(f"[SD-LOG] Checkbox {i+1}: No se pudo obtener información")
                        
                        # Buscar botones que puedan ser de selección
                        select_buttons = driver.find_elements(By.XPATH, "//*[contains(text(), 'Select') or contains(text(), 'select') or contains(text(), 'All') or contains(text(), 'all')]")
                        print(f"[SD-LOG] Botones/elementos con 'Select/All': {len(select_buttons)}")
                        for i, btn in enumerate(select_buttons[:3]):
                            try:
                                print(f"[SD-LOG] Select element {i+1}: tag='{btn.tag_name}', text='{btn.text}', class='{btn.get_attribute('class')}'")
                            except:
                                pass
                    except Exception as e:
                        print(f"[SD-LOG] Error inspeccionando elementos: {e}")
                    
                    select_all_selectors = [
                        # Selectores originales
                        (By.ID, "srp-select-all"),
                        (By.CSS_SELECTOR, "input[type='checkbox'][data-testid='select-all']"),
                        (By.XPATH, "//input[@type='checkbox' and contains(@id, 'select-all')]"),
                        (By.CSS_SELECTOR, ".select-all-checkbox"),
                        
                        # Selectores adicionales más específicos para ScienceDirect
                        (By.XPATH, "//input[@type='checkbox' and contains(@class, 'select-all')]"),
                        (By.XPATH, "//input[@type='checkbox' and @aria-label='Select all']"),
                        (By.CSS_SELECTOR, "input[aria-label*='Select all']"),
                        (By.CSS_SELECTOR, "input[title*='Select all']"),
                        (By.XPATH, "//label[contains(text(), 'Select all')]/input"),
                        (By.XPATH, "//button[contains(text(), 'Select all')]"),
                        (By.CSS_SELECTOR, "button[data-testid*='select-all']"),
                        
                        # Selectores más genéricos
                        (By.XPATH, "//input[@type='checkbox'][1]"),  # Primer checkbox
                        (By.CSS_SELECTOR, ".results-header input[type='checkbox']"),
                        (By.CSS_SELECTOR, ".search-results-header input[type='checkbox']"),
                        (By.XPATH, "//div[contains(@class, 'header')]//input[@type='checkbox']"),
                    ]
                    
                    select_all_checkbox = None
                    for selector in select_all_selectors:
                        try:
                            print(f"[SD-LOG] Probando selector: {selector}")
                            select_all_checkbox = WebDriverWait(driver, 5).until(
                                EC.element_to_be_clickable(selector)
                            )
                            print(f"[SD-LOG] Checkbox encontrado con: {selector}")
                            break
                        except Exception as e:
                            print(f"[SD-LOG] Selector {selector} falló: {e}")
                            continue
                    
                    if not select_all_checkbox:
                        # Última estrategia: buscar cualquier checkbox en la zona de resultados
                        try:
                            print("[SD-LOG] Buscando cualquier checkbox en la zona de resultados...")
                            results_area = driver.find_element(By.ID, "srp-results-list")
                            all_checkboxes = results_area.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
                            if all_checkboxes:
                                select_all_checkbox = all_checkboxes[0]  # Tomar el primer checkbox
                                print(f"[SD-LOG] Usando el primer checkbox encontrado en resultados")
                            else:
                                print("[SD-LOG] No se encontraron checkboxes en el área de resultados")
                        except Exception as e:
                            print(f"[SD-LOG] Error buscando checkboxes en resultados: {e}")
                    
                    if not select_all_checkbox:
                        print("[SD-LOG] No se encontró checkbox 'Seleccionar todo'. Procediendo con selección manual...")
                    
                    # SIEMPRE hacer selección manual para asegurar que se seleccionan todos los elementos
                    print("[SD-LOG] Iniciando selección manual de todos los resultados...")
                    try:
                        # Buscar todos los elementos de resultado
                        result_selectors = [
                            "li.ResultItem",
                            ".search-result-item", 
                            ".result-item",
                            "[data-testid='search-result']",
                            ".search-body .result"
                        ]
                        
                        result_items = []
                        for selector in result_selectors:
                            try:
                                items = driver.find_elements(By.CSS_SELECTOR, selector)
                                if items:
                                    result_items = items
                                    print(f"[SD-LOG] Encontrados {len(items)} resultados con selector: {selector}")
                                    break
                            except:
                                continue
                        
                        if not result_items:
                            print("[SD-LOG] No se encontraron elementos de resultado")
                            raise Exception("No se encontraron elementos de resultado")
                        
                        selected_count = 0
                        checkbox_selectors = [
                            "input[type='checkbox']",
                            ".checkbox input",
                            "[data-testid*='checkbox']",
                            ".result-checkbox input"
                        ]
                        
                        for i, item in enumerate(result_items[:25]):  # Máximo 25 items por página
                            try:
                                print(f"[SD-LOG] Procesando resultado {i+1}/{len(result_items[:25])}")
                                
                                item_checkbox = None
                                for cb_selector in checkbox_selectors:
                                    try:
                                        item_checkbox = item.find_element(By.CSS_SELECTOR, cb_selector)
                                        break
                                    except:
                                        continue
                                
                                if item_checkbox and not item_checkbox.is_selected():
                                    # Hacer scroll al checkbox
                                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", item_checkbox)
                                    time.sleep(0.1)
                                    
                                    # Intentar hacer clic
                                    try:
                                        item_checkbox.click()
                                    except:
                                        driver.execute_script("arguments[0].click();", item_checkbox)
                                    
                                    selected_count += 1
                                    print(f"[SD-LOG] ✓ Seleccionado resultado {i+1}")
                                    time.sleep(0.2)  # Pequeña pausa entre clics
                                elif item_checkbox and item_checkbox.is_selected():
                                    selected_count += 1
                                    print(f"[SD-LOG] ✓ Resultado {i+1} ya estaba seleccionado")
                                else:
                                    print(f"[SD-LOG] ⚠ No se encontró checkbox en resultado {i+1}")
                                    
                            except Exception as item_error:
                                print(f"[SD-LOG] Error procesando resultado {i+1}: {item_error}")
                                continue
                        
                        if selected_count > 0:
                            print(f"[SD-LOG] ✓ Total seleccionados: {selected_count} elementos")
                        else:
                            raise Exception("No se pudo seleccionar ningún elemento")
                            
                    except Exception as manual_error:
                        print(f"[SD-LOG] Error en selección manual: {manual_error}")
                        raise Exception("Falló la selección de elementos")
                    else:
                        driver.execute_script("arguments[0].click();", select_all_checkbox)
                        print("[SD-LOG] Checkbox 'Seleccionar todo' marcado.")
                    
                    time.sleep(random.uniform(2, 4))

                    print("[SD-LOG] Esperando el botón de exportar...")
                    
                    # Primero inspeccionar qué botones hay disponibles
                    try:
                        print("[SD-LOG] Inspeccionando botones disponibles...")
                        all_buttons = driver.find_elements(By.TAG_NAME, "button")
                        print(f"[SD-LOG] Total de botones encontrados: {len(all_buttons)}")
                        
                        export_related_buttons = []
                        for i, btn in enumerate(all_buttons):
                            try:
                                btn_text = btn.text.lower()
                                btn_class = btn.get_attribute('class')
                                if any(word in btn_text for word in ['export', 'download', 'cite', 'citation']):
                                    export_related_buttons.append((i, btn, btn_text, btn_class))
                                    print(f"[SD-LOG] Botón relacionado {i}: '{btn.text}', class='{btn_class}'")
                            except:
                                continue
                        
                        if not export_related_buttons:
                            print("[SD-LOG] No se encontraron botones relacionados con export/download")
                            # Mostrar algunos botones para diagnóstico
                            for i, btn in enumerate(all_buttons[:10]):
                                try:
                                    print(f"[SD-LOG] Botón {i}: '{btn.text}', class='{btn.get_attribute('class')}'")
                                except:
                                    continue
                                    
                    except Exception as e:
                        print(f"[SD-LOG] Error inspeccionando botones: {e}")
                    
                    export_selectors = [
                        # Selectores originales
                        (By.XPATH, "//button[contains(., 'Export')]"),
                        (By.CSS_SELECTOR, "button[data-testid='export']"),
                        (By.XPATH, "//button[contains(@class, 'export')]"),
                        
                        # Selectores adicionales específicos para ScienceDirect
                        (By.XPATH, "//button[contains(text(), 'Export')]"),
                        (By.XPATH, "//button[contains(text(), 'EXPORT')]"),
                        (By.XPATH, "//a[contains(text(), 'Export')]"),
                        (By.CSS_SELECTOR, "button[aria-label*='Export']"),
                        (By.CSS_SELECTOR, "a[aria-label*='Export']"),
                        (By.XPATH, "//button[contains(., 'Download')]"),
                        (By.XPATH, "//a[contains(., 'Download')]"),
                        (By.XPATH, "//button[contains(., 'Citation')]"),
                        (By.XPATH, "//a[contains(., 'Citation')]"),
                        
                        # Selectores por clase común en ScienceDirect
                        (By.CSS_SELECTOR, ".export-button"),
                        (By.CSS_SELECTOR, ".download-button"),
                        (By.CSS_SELECTOR, "button[class*='export']"),
                        (By.CSS_SELECTOR, "a[class*='export']"),
                        
                        # Selectores en áreas específicas
                        (By.XPATH, "//div[contains(@class, 'actions')]//button[contains(., 'Export')]"),
                        (By.XPATH, "//div[contains(@class, 'toolbar')]//button[contains(., 'Export')]"),
                    ]
                    
                    export_button = None
                    for selector in export_selectors:
                        try:
                            print(f"[SD-LOG] Probando selector export: {selector}")
                            export_button = WebDriverWait(driver, 5).until(
                                EC.element_to_be_clickable(selector)
                            )
                            print(f"[SD-LOG] Botón de exportar encontrado con: {selector}")
                            break
                        except Exception as e:
                            print(f"[SD-LOG] Selector export {selector} falló: {e}")
                            continue
                    
                    if not export_button:
                        # Estrategia alternativa: buscar en menús desplegables o acciones
                        try:
                            print("[SD-LOG] Buscando en menús de acciones...")
                            action_menus = driver.find_elements(By.XPATH, "//*[contains(@class, 'action') or contains(@class, 'menu') or contains(@class, 'dropdown')]")
                            for menu in action_menus:
                                try:
                                    menu.click()
                                    time.sleep(1)
                                    export_in_menu = menu.find_element(By.XPATH, ".//button[contains(., 'Export')] | .//a[contains(., 'Export')]")
                                    if export_in_menu:
                                        export_button = export_in_menu
                                        print("[SD-LOG] Botón de exportar encontrado en menú desplegable")
                                        break
                                except:
                                    continue
                        except Exception as e:
                            print(f"[SD-LOG] Error buscando en menús: {e}")
                    
                    if not export_button:
                        print("[SD-LOG] No se encontró botón de exportar con ningún método")
                        raise Exception("No se encontró el botón de exportar")
                    
                    export_button.click()
                    print("[SD-LOG] Botón de exportar presionado.")

                    print("[SD-LOG] Esperando a que aparezca el modal de exportación...")
                    WebDriverWait(driver, 15).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, ".ReactModal__Body--open"))
                    )
                    print("[SD-LOG] Modal de exportación visible.")

                    print("[SD-LOG] Esperando la opción 'Export citation to BibTeX'...")
                    bibtex_export_button = WebDriverWait(driver, 15).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Export citation to BibTeX')]"))
                    )
                    bibtex_export_button.click()
                    print("[SD-LOG] Opción BibTeX seleccionada y descarga iniciada.")

                    # Esperar la descarga
                    if not wait_for_new_file(download_path):
                        print("[SD-LOG] No se detectó la descarga del archivo.")
                        raise Exception("Fallo en la descarga del archivo.")
                    
                    print(f"[SD-LOG] Descarga de la página {page_num} completada con éxito.")
                    
                    # Guardar progreso
                    with open(progress_file, 'w') as f:
                        json.dump({'last_page': page_num, 'timestamp': str(datetime.now())}, f)
                    
                    break # Salir del bucle de reintentos si todo fue exitoso

                except Exception as page_error:
                    print(f"!! [SD-LOG] Error en el intento {attempt} para la página {page_num}: {page_error}")
                    if attempt == 3:
                        raise # Lanzar la excepción final si todos los reintentos fallan
                    driver.refresh()
                    time.sleep(5)
                    continue

            if page_num < max_pages:
                print(f"[SD-LOG] Navegando a la siguiente página ({page_num + 1})...")
                try:
                    next_page_selectors = [
                        # Selector específico encontrado por el usuario
                        (By.CSS_SELECTOR, "li.pagination-link.next-link"),
                        (By.CSS_SELECTOR, "li.pagination-link.next-link a"),
                        (By.XPATH, "//li[contains(@class, 'pagination-link') and contains(@class, 'next-link')]"),
                        (By.XPATH, "//li[contains(@class, 'pagination-link') and contains(@class, 'next-link')]//a"),
                        
                        # Selectores originales como fallback
                        (By.CSS_SELECTOR, "a[data-test-id='next-page']"),
                        (By.XPATH, "//a[contains(@class, 'next-page')]"),
                        (By.XPATH, "//a[contains(text(), 'Next')]"),
                        (By.CSS_SELECTOR, ".pagination-next"),
                        
                        # Selectores adicionales específicos para ScienceDirect
                        (By.XPATH, "//a[contains(@aria-label, 'Next')]"),
                        (By.XPATH, "//a[contains(@title, 'Next')]"),
                        (By.CSS_SELECTOR, "a[aria-label*='Next']"),
                        (By.CSS_SELECTOR, "a[title*='Next']"),
                        
                        # Buscar en la paginación
                        (By.XPATH, "//div[contains(@class, 'pagination')]//a[contains(text(), 'Next')]"),
                        (By.XPATH, "//ul[contains(@class, 'pagination')]//a[contains(text(), 'Next')]"),
                        (By.XPATH, "//nav[contains(@class, 'pagination')]//a[contains(text(), 'Next')]"),
                        
                        # Buscar botones con íconos de flecha
                        (By.XPATH, "//a[contains(@class, 'next') or contains(@class, 'forward')]"),
                        (By.XPATH, "//button[contains(@class, 'next') or contains(@class, 'forward')]"),
                        
                        # Buscar por símbolo de flecha
                        (By.XPATH, "//a[contains(text(), '→') or contains(text(), '>') or contains(text(), '»')]"),
                        
                        # Buscar el número de la siguiente página
                        (By.XPATH, f"//a[contains(text(), '{page_num + 1}')]"),
                    ]
                    
                    print(f"[SD-LOG] Buscando botón de página siguiente ({page_num + 1})...")
                    
                    # Primero, inspeccionar los enlaces de paginación disponibles
                    try:
                        print("[SD-LOG] Inspeccionando elementos de paginación...")
                        pagination_elements = driver.find_elements(By.XPATH, "//li[contains(@class, 'pagination')] | //a[contains(@href, 'page=') or contains(text(), 'Next') or contains(text(), 'next') or contains(@class, 'next') or contains(@class, 'pagination')]")
                        print(f"[SD-LOG] Elementos de paginación encontrados: {len(pagination_elements)}")
                        for i, elem in enumerate(pagination_elements[:10]):  # Mostrar hasta 10 elementos
                            try:
                                print(f"[SD-LOG] Paginación {i+1}: tag='{elem.tag_name}', text='{elem.text}', href='{elem.get_attribute('href')}', class='{elem.get_attribute('class')}'")
                            except:
                                pass
                    except Exception as e:
                        print(f"[SD-LOG] Error inspeccionando paginación: {e}")
                    
                    next_page_button = None
                    for selector in next_page_selectors:
                        try:
                            print(f"[SD-LOG] Probando selector paginación: {selector}")
                            next_page_button = WebDriverWait(driver, 5).until(
                                EC.element_to_be_clickable(selector)
                            )
                            print(f"[SD-LOG] Botón siguiente página encontrado con: {selector}")
                            break
                        except Exception as e:
                            print(f"[SD-LOG] Selector paginación {selector} falló: {e}")
                            continue
                    
                    if not next_page_button:
                        print("[SD-LOG] No se encontró botón de siguiente página con selectores. Intentando navegación directa por URL...")
                        # Estrategia alternativa: modificar URL directamente
                        current_url = driver.current_url
                        print(f"[SD-LOG] URL actual: {current_url}")
                        
                        try:
                            if 'page=' in current_url:
                                new_url = current_url.replace(f'page={page_num}', f'page={page_num + 1}')
                            elif '&start=' in current_url or '?start=' in current_url:
                                # ScienceDirect a veces usa parámetro 'start'
                                start_value = page_num * 25  # Asumiendo 25 resultados por página
                                new_start = (page_num) * 25  # Siguiente página
                                if f'start={start_value}' in current_url:
                                    new_url = current_url.replace(f'start={start_value}', f'start={new_start}')
                                else:
                                    separator = '&' if '?' in current_url else '?'
                                    new_url = f"{current_url}{separator}start={new_start}"
                            else:
                                separator = '&' if '?' in current_url else '?'
                                new_url = f"{current_url}{separator}page={page_num + 1}"
                            
                            print(f"[SD-LOG] Navegando directamente a: {new_url}")
                            driver.get(new_url)
                            time.sleep(5)
                            
                            # Verificar que la nueva página cargó
                            try:
                                WebDriverWait(driver, 15).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, "li.ResultItem"))
                                )
                                print(f"[SD-LOG] Navegación directa a página {page_num + 1} exitosa")
                            except:
                                print("[SD-LOG] La navegación directa no cargó resultados")
                                break
                        except Exception as url_error:
                            print(f"[SD-LOG] Error en navegación directa: {url_error}")
                            break
                    
                    else:
                        # Usar el botón encontrado
                        try:
                            # Hacer scroll al botón
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_page_button)
                            time.sleep(1)
                            
                            # Guardar URL actual para verificar cambio
                            current_url = driver.current_url
                            
                            # Hacer clic en el botón
                            try:
                                next_page_button.click()
                                print("[SD-LOG] Clic en botón de siguiente página exitoso")
                            except:
                                driver.execute_script("arguments[0].click();", next_page_button)
                                print("[SD-LOG] Clic con JavaScript en botón de siguiente página")
                            
                            # Esperar que la página cambie
                            print("[SD-LOG] Esperando que la nueva página cargue...")
                            try:
                                # Esperar que la URL cambie o que el botón se vuelva obsoleto
                                WebDriverWait(driver, 10).until(
                                    lambda x: x.current_url != current_url or EC.staleness_of(next_page_button)(x)
                                )
                                
                                # Esperar que los nuevos resultados aparezcan
                                WebDriverWait(driver, 15).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, "li.ResultItem"))
                                )
                                
                                print(f"[SD-LOG] Navegación a página {page_num + 1} completada exitosamente")
                                print(f"[SD-LOG] Nueva URL: {driver.current_url}")
                                
                            except TimeoutException:
                                print("[SD-LOG] Timeout esperando nueva página - verificando si ya estamos en la nueva página")
                                # Verificar si hay resultados nuevos
                                try:
                                    results = driver.find_elements(By.CSS_SELECTOR, "li.ResultItem")
                                    if results:
                                        print(f"[SD-LOG] Encontrados {len(results)} resultados en la nueva página")
                                    else:
                                        print("[SD-LOG] No se encontraron resultados - posiblemente fin de páginas")
                                        break
                                except:
                                    print("[SD-LOG] Error verificando resultados")
                                    break
                            
                        except Exception as click_error:
                            print(f"[SD-LOG] Error haciendo clic en siguiente página: {click_error}")
                            break
                    
                    time.sleep(random.uniform(4, 6))
                    
                except Exception as nav_error:
                    print(f"[SD-LOG] Error general en navegación: {nav_error}")
                    print("[SD-LOG] No se encontró el botón de 'siguiente página'. Finalizando proceso.")
                    break

        except Exception as e:
            print(f"!! [SD-LOG] No se pudo procesar la página {page_num} después de 3 intentos: {e}")
            print("[SD-LOG] Intentando continuar con la siguiente página...")
            driver.get(driver.current_url) # Refrescar para evitar estados inconsistentes
            time.sleep(6)
            continue