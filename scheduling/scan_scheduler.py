def scan_scheduling(requests, head_position, direction):
    """
    Implementa el algoritmo de planificación de disco SCAN.

    :param requests: Lista de solicitudes de disco (enteros que representan números de cilindro)
    :param head_position: Posición actual de la cabeza del disco
    :param direction: Dirección inicial, 'up' (hacia números más altos) o 'down' (hacia números más bajos)
    :return: Lista de solicitudes en el orden en que deben ser atendidas
    """
    if not requests:
        return []

    # Eliminar duplicados y ordenar
    sorted_requests = sorted(set(requests))

    if direction == 'up':
        # Atender solicitudes en orden creciente desde la cabeza, luego invertir a menores
        higher_or_equal = [r for r in sorted_requests if r >= head_position]
        lower = [r for r in sorted_requests if r < head_position]
        order = higher_or_equal + list(reversed(lower))
    elif direction == 'down':
        # Atender solicitudes en orden decreciente desde la cabeza, luego invertir a mayores
        lower_or_equal = [r for r in sorted_requests if r <= head_position]
        higher = [r for r in sorted_requests if r > head_position]
        order = list(reversed(lower_or_equal)) + higher
    else:
        raise ValueError("Dirección debe ser 'up' o 'down'")

    return order