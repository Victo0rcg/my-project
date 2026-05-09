from enum import Enum

class Rol(Enum):
    ADMINISTRADOR = "ADMINISTRADOR"
    CAJERO = "CAJERO"
    AUDITOR = "AUDITOR"

class Operacion(Enum):
    DEPOSITO = "DEPOSITO"
    RETIRO = "RETIRO"
    TRANSFERENCIA = "TRANSFERENCIA"
    CONSULTA = "CONSULTA"