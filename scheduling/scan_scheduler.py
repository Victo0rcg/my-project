import logging

def scan_scheduling(requests, head_position, direction):
    logging.info(f"[SCAN] Planificador de E/S de disco activado.")
    logging.info(f"[SCAN] Peticiones en cola sectorial: {requests} | Posicion cabeza: {head_position} | Direccion: {direction.upper()}")
    if not requests:
        return []

    sorted_requests = sorted(set(requests))
    superiores = [r for r in sorted_requests if r >= head_position]
    inferiores = [r for r in sorted_requests if r < head_position]

    if direction == 'up':
        resultado = superiores + inferiores[::-1]
        logging.info(f"[SCAN] -> Trayectoria del brazo optimizada (UP): {resultado}")
        return resultado
    elif direction == 'down':
        superiores_estrictos = [r for r in sorted_requests if r > head_position]
        inferiores_o_igual = [r for r in sorted_requests if r <= head_position]
        resultado = inferiores_o_igual[::-1] + superiores_estrictos
        logging.info(f"[SCAN] -> Trayectoria del brazo optimizada (DOWN): {resultado}")
        return resultado
    raise ValueError("Direccion invalida.")