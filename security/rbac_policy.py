import logging
from security.roles import Rol, Operacion

class PoliticaRBAC:
    def __init__(self):
        # Matriz de Control de Acceso: Define que rol puede hacer que
        self._permisos = {
            Rol.ADMINISTRADOR: [Operacion.DEPOSITO, Operacion.RETIRO, Operacion.TRANSFERENCIA, Operacion.CONSULTA],
            Rol.CAJERO: [Operacion.DEPOSITO, Operacion.RETIRO, Operacion.CONSULTA],
            Rol.AUDITOR: [Operacion.CONSULTA]
        }

    def verificar_permiso(self, rol_usuario: Rol, operacion_solicitada: Operacion) -> bool:
        """Verifica si un rol tiene permitido ejecutar una operacion."""
        logging.info(f"[RBAC] Verificando permisos - Rol: {rol_usuario.name} | Intenta: {operacion_solicitada.name}")
        
        operaciones_permitidas = self._permisos.get(rol_usuario, [])
        if operacion_solicitada in operaciones_permitidas:
            logging.info("[RBAC] Acceso concedido.")
            return True
            
        logging.error(f"[RBAC] ACCESO DENEGADO: {rol_usuario.name} no tiene privilegios para {operacion_solicitada.name}")
        raise PermissionError(f"Violacion de dominio de proteccion por el rol {rol_usuario.name}.")