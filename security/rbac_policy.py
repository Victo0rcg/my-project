import logging
from security.roles import Rol, Operacion

class PoliticaRBAC:
    def __init__(self):
        self._permisos = {
            Rol.ADMINISTRADOR: [Operacion.DEPOSITO, Operacion.RETIRO, Operacion.TRANSFERENCIA, Operacion.CONSULTA],
            Rol.CAJERO: [Operacion.DEPOSITO, Operacion.RETIRO, Operacion.CONSULTA],
            Rol.AUDITOR: [Operacion.CONSULTA]
        }

    def verificar_permiso(self, rol_usuario: Rol, operacion_solicitada: Operacion) -> bool:
        logging.info(f"[RBAC] Validando seguridad de archivos para el Rol: '{rol_usuario.name}' -> Operacion: '{operacion_solicitada.name}'")
        operaciones_permitidas = self._permisos.get(rol_usuario, [])
        if operacion_solicitada in operaciones_permitidas:
            logging.info(f"[RBAC] Acceso PERMITIDO al archivo de la cuenta para {rol_usuario.name}.")
            return True
        logging.warning(f"[RBAC] Acceso DENEGADO al archivo. Privilegios insuficientes para {rol_usuario.name}.")
        return False