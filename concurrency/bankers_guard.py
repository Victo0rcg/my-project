import logging

class GuardiaBanquero:
    def __init__(self, recursos_disponibles, necesidad_maxima, recursos_asignados):
        """
        Inicializa el estado del sistema para el Algoritmo del Banquero.
        recursos_disponibles: Lista de recursos disponibles [A, B, C]
        necesidad_maxima: Matriz de maxima necesidad por proceso
        recursos_asignados: Matriz de recursos actualmente asignados
        """
        self.recursos_disponibles = recursos_disponibles
        self.necesidad_maxima = necesidad_maxima
        self.recursos_asignados = recursos_asignados
        self.cantidad_procesos = len(recursos_asignados)
        self.cantidad_recursos = len(recursos_disponibles)
        
        # Calcular la matriz de Necesidad (Necesidad = Maxima - Asignada)
        self.matriz_necesidad = []
        for indice_proceso in range(self.cantidad_procesos):
            necesidad_proceso = [
                self.necesidad_maxima[indice_proceso][indice_recurso] - self.recursos_asignados[indice_proceso][indice_recurso] 
                for indice_recurso in range(self.cantidad_recursos)
            ]
            self.matriz_necesidad.append(necesidad_proceso)

    def es_estado_seguro(self) -> bool:
        """Verifica si el estado actual del sistema es seguro."""
        recursos_simulados = self.recursos_disponibles.copy()
        procesos_terminados = [False] * self.cantidad_procesos
        secuencia_segura = []

        logging.info("[BANQUERO] Iniciando calculo de secuencia segura...")
        
        while len(secuencia_segura) < self.cantidad_procesos:
            recursos_asignados_en_esta_ronda = False
            for indice_proceso in range(self.cantidad_procesos):
                if not procesos_terminados[indice_proceso]:
                    # Verificar si la necesidad del proceso puede ser satisfecha con los recursos simulados
                    if all(self.matriz_necesidad[indice_proceso][indice_recurso] <= recursos_simulados[indice_recurso] for indice_recurso in range(self.cantidad_recursos)):
                        # Simular ejecucion y liberacion de recursos
                        for indice_recurso in range(self.cantidad_recursos):
                            recursos_simulados[indice_recurso] += self.recursos_asignados[indice_proceso][indice_recurso]
                        procesos_terminados[indice_proceso] = True
                        secuencia_segura.append(indice_proceso)
                        recursos_asignados_en_esta_ronda = True
                        logging.info(f"  -> Proceso P{indice_proceso} puede finalizar. Vector de trabajo actualizado: {recursos_simulados}")
            
            # Si dimos una vuelta completa a los procesos y no asignamos nada, hay interbloqueo
            if not recursos_asignados_en_esta_ronda:
                logging.warning("[BANQUERO] ESTADO INSEGURO DETECTADO. Riesgo de Deadlock.")
                return False

        logging.info(f"[BANQUERO] ESTADO SEGURO. Secuencia de ejecucion: {[f'P{proceso}' for proceso in secuencia_segura]}")
        return True

    def solicitar_recursos(self, id_proceso: int, solicitud_recursos: list) -> bool:
        """Simula una peticion de recursos y decide si otorgarlos."""
        logging.info(f"\n[BANQUERO] P{id_proceso} solicita recursos: {solicitud_recursos}")
        
        # 1. Verificar si la peticion supera la necesidad maxima declarada
        if any(solicitud_recursos[indice_recurso] > self.matriz_necesidad[id_proceso][indice_recurso] for indice_recurso in range(self.cantidad_recursos)):
            raise ValueError("Error: El proceso supero su reclamo maximo.")
            
        # 2. Verificar si hay recursos disponibles
        if any(solicitud_recursos[indice_recurso] > self.recursos_disponibles[indice_recurso] for indice_recurso in range(self.cantidad_recursos)):
            logging.info("[BANQUERO] Recursos insuficientes, el proceso debe esperar.")
            return False

        # 3. Simular la asignacion temporal
        for indice_recurso in range(self.cantidad_recursos):
            self.recursos_disponibles[indice_recurso] -= solicitud_recursos[indice_recurso]
            self.recursos_asignados[id_proceso][indice_recurso] += solicitud_recursos[indice_recurso]
            self.matriz_necesidad[id_proceso][indice_recurso] -= solicitud_recursos[indice_recurso]

        # 4. Verificar si el nuevo estado es seguro
        es_seguro = self.es_estado_seguro()

        # 5. Si no es seguro, deshacer los cambios (Rollback)
        if not es_seguro:
            logging.warning(f"[BANQUERO] Peticion denegada para P{id_proceso}. Deshaciendo asignacion (Rollback).")
            for indice_recurso in range(self.cantidad_recursos):
                self.recursos_disponibles[indice_recurso] += solicitud_recursos[indice_recurso]
                self.recursos_asignados[id_proceso][indice_recurso] -= solicitud_recursos[indice_recurso]
                self.matriz_necesidad[id_proceso][indice_recurso] += solicitud_recursos[indice_recurso]
            return False

        logging.info(f"[BANQUERO] Peticion concedida a P{id_proceso}.")
        return True