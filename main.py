import sys
import logging
import time

# ==========================================
# CONFIGURACION Y LOGGING
# ==========================================
def configurar_logger():
    """Configura el formato base para la salida en consola."""
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(message)s',
        datefmt='%H:%M:%S',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

# ==========================================
# IMPORTACION DE MODULOS DEL SISTEMA
# ==========================================
# Carga de los componentes principales de la arquitectura.
try:
    from security.roles import Rol, Operacion
    from security.rbac_policy import PoliticaRBAC
    from concurrency.bankers_guard import GuardiaBanquero
    # Se iran descomentando a medida que se integren:
    # from core.transaction_engine import MotorTransacciones
    # from scheduling.scan_scheduler import PlanificadorSCAN
    MODULOS_LISTOS = True
except ImportError as error_importacion:
    MODULOS_LISTOS = False
    print(f"Atencion: Faltan modulos por integrar ({error_importacion}).")

# ==========================================
# ESCENARIOS DE PRUEBA
# ==========================================

def escenario_concurrencia():
    """Prueba de estres para el motor de transacciones."""
    print("\n--- INICIANDO PRUEBA DE ESTRES (50 HILOS) ---")
    print(">> Aqui se instanciara el motor principal y se lanzaran los hilos concurrentes.")
    # TODO: Importar e instanciar el motor de transacciones.
    # TODO: Crear bucle para instanciar e iniciar multiples hilos.
    # TODO: Esperar a los hilos con join() y mostrar resultados.
    pass

def escenario_control_acceso():
    """Prueba de dominios de proteccion."""
    print("\n--- INICIANDO TEST DE DOMINIOS Y PERMISOS (RBAC) ---")
    if not MODULOS_LISTOS:
        print("[Error] Los modulos de seguridad no estan listos o hay un error de importacion.")
        return

    politica_seguridad = PoliticaRBAC()
    
    # Prueba 1: Exito
    print(">> CASO 1: Operacion Permitida (ADMINISTRADOR intentando TRANSFERENCIA)")
    time.sleep(1)
    try:
        politica_seguridad.verificar_permiso(Rol.ADMINISTRADOR, Operacion.TRANSFERENCIA)
        print(">> Resultado: Transaccion de transferencia autorizada. Continuara a los hilos.\n")
    except PermissionError as error_permiso:
        print(f">> Error inesperado: {error_permiso}\n")

    # Prueba 2: Fallo intencional
    print(">> CASO 2: Operacion Denegada (AUDITOR intentando RETIRO)")
    time.sleep(1)
    try:
        politica_seguridad.verificar_permiso(Rol.AUDITOR, Operacion.RETIRO)
        print(">> Resultado: Transaccion de retiro continuara (ESTO NO DEBERIA PASAR).")
    except PermissionError as error_permiso:
        print(f">> PROCESO ABORTADO CORRECTAMENTE: {error_permiso}\n")

def escenario_prevencion_interbloqueos():
    """Prueba de prevencion de interbloqueos."""
    print("\n--- INICIANDO TEST DE INTERBLOQUEOS (ALGORITMO BANQUERO) ---")
    if not MODULOS_LISTOS:
        print("[Error] Los modulos de concurrencia no estan listos o hay un error de importacion.")
        return

    # Escenario inicial del sistema (Matriz clasica de Dijkstra)
    recursos_disponibles = [3, 3, 2] # Instancias de [Recurso A, Recurso B, Recurso C]
    necesidad_maxima = [
        [7, 5, 3], # Proceso 0
        [3, 2, 2], # Proceso 1
        [9, 0, 2], # Proceso 2
        [2, 2, 2]  # Proceso 3
    ]
    asignacion_actual = [
        [0, 1, 0], # Proceso 0
        [2, 0, 0], # Proceso 1
        [3, 0, 2], # Proceso 2
        [2, 1, 1]  # Proceso 3
    ]
    
    print(">> Inicializando estado del sistema con 4 procesos y 3 tipos de recursos...")
    time.sleep(1.5)
    guardia_recursos = GuardiaBanquero(recursos_disponibles, necesidad_maxima, asignacion_actual)
    
    # Simulamos que el Proceso 1 pide recursos que mantienen el sistema seguro
    print("\n>> CASO 1: Peticion Segura (Proceso 1 solicita [1, 0, 2])")
    time.sleep(1)
    guardia_recursos.solicitar_recursos(id_proceso=1, solicitud_recursos=[1, 0, 2])
    
    # Simulamos que el Proceso 0 pide recursos que generarian Deadlock
    print("\n>> CASO 2: Peticion Insegura provocando posible Deadlock (Proceso 0 solicita [0, 2, 0])")
    time.sleep(1)
    guardia_recursos.solicitar_recursos(id_proceso=0, solicitud_recursos=[0, 2, 0])

def escenario_planificacion_disco():
    """Prueba de planificacion de I/O."""
    print("\n--- INICIANDO VOLCADO DE LOGS A DISCO (ALGORITMO SCAN) ---")
    print(">> Aqui se enviara el array de cilindros al planificador de disco.")
    # TODO: Importar e instanciar el planificador SCAN.
    # TODO: Enviar un array de peticiones de cilindros desordenadas.
    # TODO: Mostrar el recorrido del cabezal ordenado.
    pass

def escenario_manejo_interrupciones():
    """Simulacion de interrupciones de Hardware y Software."""
    print("\n--- INICIANDO SIMULACION DE INTERRUPCIONES (TRAPS & HARDWARE) ---")
    print(">> Aqui se simulara como el SO maneja excepciones criticas.")
    
    time.sleep(1)
    print("\n[Simulando Interrupcion de Software...]")
    logging.warning("[TRAP] Excepcion detectada: Intento de division por cero en calculo de divisas.")
    logging.info("[Manejador SO] Abortando proceso defectuoso. Volcando memoria (Core Dump)... OK.")
    
    time.sleep(1.5)
    print("\n[Simulando Interrupcion de Hardware...]")
    logging.error("[IRQ 12] Alerta de Hardware: Conexion perdida con el Cajero Automatico 04.")
    logging.info("[Manejador SO] Pausando transacciones del Cajero 04. Guardando estado en bloque de control de proceso (PCB)... OK.")
    
    print("\n>> Manejo de interrupciones ejecutado. El sistema sigue estable.")

# ==========================================
# INTERFAZ PRINCIPAL
# ==========================================
def mostrar_menu():
    print("\n" + "="*65)
    print(" SIMULADOR DE TRANSACCIONES - SISTEMAS OPERATIVOS")
    print("="*65)
    print(" Seleccione el escenario de evaluacion:")
    print(" 1. [Concurrencia] Prueba de estres (50 hilos)")
    print(" 2. [Seguridad] Validar dominios de proteccion (RBAC)")
    print(" 3. [Interbloqueos] Forzar escenario de interbloqueo (Banquero)")
    print(" 4. [Planificacion] Procesar cola de I/O en disco (SCAN)")
    print(" 5. [Interrupciones] Forzar fallos de Hardware/Software")
    print(" 6. Salir del simulador")
    print("="*65)

def main():
    configurar_logger()

    while True:
        mostrar_menu()
        opcion_seleccionada = input(">> Opcion [1-6]: ").strip()

        if opcion_seleccionada == '1':
            escenario_concurrencia()
        elif opcion_seleccionada == '2':
            escenario_control_acceso()
        elif opcion_seleccionada == '3':
            escenario_prevencion_interbloqueos()
        elif opcion_seleccionada == '4':
            escenario_planificacion_disco()
        elif opcion_seleccionada == '5':
            escenario_manejo_interrupciones()
        elif opcion_seleccionada == '6':
            print("\nFinalizando procesos y cerrando simulador.")
            sys.exit(0)
        else:
            print("\nError: Ingrese un comando valido.")
        
        input("\n[Presione ENTER para continuar...]")

main()