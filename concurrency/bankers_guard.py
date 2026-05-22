import logging

class GuardiaBanquero:
    def __init__(self, recursos_disponibles, necesidad_maxima, recursos_asignados):
        self.recursos_disponibles = recursos_disponibles
        self.necesidad_maxima = necesidad_maxima
        self.recursos_asignados = recursos_asignados
        self.cantidad_procesos = len(recursos_asignados)
        self.cantidad_recursos = len(recursos_disponibles)
        self.matriz_necesidad = [
            [max_r - asig_r for max_r, asig_r in zip(max_p, asig_p)]
            for max_p, asig_p in zip(necesidad_maxima, recursos_asignados)
        ]

    def es_estado_seguro(self) -> bool:
        recursos_simulados = self.recursos_disponibles.copy()
        procesos_terminados = [False] * self.cantidad_procesos
        secuencia_segura = []
        logging.info("[BANQUERO] Ejecutando simulacion de asignacion para prevencion de interbloqueos...")

        while len(secuencia_segura) < self.cantidad_procesos:
            recursos_asignados_en_esta_ronda = False
            for idx in range(self.cantidad_procesos):
                if not procesos_terminados[idx]:
                    if all(n <= r for n, r in zip(self.matriz_necesidad[idx], recursos_simulados)):
                        for i in range(self.cantidad_recursos):
                            recursos_simulados[i] += self.recursos_asignados[idx][i]
                        procesos_terminados[idx] = True
                        secuencia_segura.append(idx)
                        recursos_asignados_en_esta_ronda = True
                        logging.info(f"    -> [Analisis] Proceso P{idx} puede terminar de forma segura. Disponibles virtuales: {recursos_simulados}")
            if not recursos_asignados_en_esta_ronda:
                logging.warning("[BANQUERO] ESTADO INSEGURO! Posible condicion de bloqueo mutuo detectada.")
                return False

        logging.info(f"[BANQUERO] ESTADO SEGURO. Secuencia optima encontrada: {[f'P{p}' for p in secuencia_segura]}")
        return True

    def _modificar_recursos(self, id_proceso: int, solicitud: list, revertir: bool = False) -> None:
        factor = 1 if revertir else -1
        for i in range(self.cantidad_recursos):
            self.recursos_disponibles[i] += factor * solicitud[i]
            self.recursos_asignados[id_proceso][i] -= factor * solicitud[i]
            self.matriz_necesidad[id_proceso][i] += factor * solicitud[i]

    def solicitar_recursos(self, id_proceso: int, solicitud_recursos: list) -> bool:
        logging.info(f"[BANQUERO] Proceso transaccional P{id_proceso} solicita recursos: {solicitud_recursos}")
        if any(s > n for s, n in zip(solicitud_recursos, self.matriz_necesidad[id_proceso])):
            raise ValueError("La solicitud excede la necesidad declarada.")
        if any(s > d for s, d in zip(solicitud_recursos, self.recursos_disponibles)):
            logging.warning(f"[BANQUERO] Recursos de hardware insuficientes. P{id_proceso} en suspension.")
            return False

        self._modificar_recursos(id_proceso, solicitud_recursos, revertir=False)
        if not self.es_estado_seguro():
            logging.warning(f"[BANQUERO] Solicitud rechazada para P{id_proceso}. Revirtiendo cambios...")
            self._modificar_recursos(id_proceso, solicitud_recursos, revertir=True)
            return False

        logging.info(f"[BANQUERO] Recursos asignados al Proceso P{id_proceso}.")
        return True

    def liberar_recursos(self, id_proceso: int, recursos_a_liberar: list) -> None:
        logging.info(f"[BANQUERO] Proceso P{id_proceso} libera recursos: {recursos_a_liberar}")
        self._modificar_recursos(id_proceso, recursos_a_liberar, revertir=True)