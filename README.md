# 🏦 Procesador de Transacciones Bancarias
### Proyecto — Sistemas Operativos

> Simulación de un entorno bancario concurrente que integra sincronización de procesos,
> planificación de disco y control de acceso basado en roles.

---

## 📋 Tabla de contenidos

- [Descripción general](#-descripción-general)
- [Objetivos](#-objetivos)
- [Marco conceptual](#-marco-conceptual)
- [Especificaciones técnicas](#-especificaciones-técnicas)
- [Arquitectura del sistema](#-arquitectura-del-sistema)
- [Plan de trabajo](#-plan-de-trabajo)
- [Flujo de trabajo con Git](#-flujo-de-trabajo-con-git)
- [Cómo ejecutar el proyecto](#-cómo-ejecutar-el-proyecto)
- [Equipo](#-equipo)
- [Referencias](#-referencias)

---

## 📌 Descripción general

Este proyecto simula un **procesador de transacciones bancarias** donde múltiples hilos
de ejecución compiten por el acceso concurrente a cuentas compartidas. El sistema
demuestra de forma práctica los conceptos fundamentales de sistemas operativos a través
de cuatro componentes principales:

| Componente | Concepto de SO aplicado |
|---|---|
| Motor de cuentas y transacciones | Sincronización con mutex y semáforos |
| Subsistema de logging | Planificación de disco con algoritmo SCAN |
| Control de acceso | Seguridad basada en roles (RBAC) |
| Prevención de interbloqueos | Algoritmo del Banquero (ítem adicional) |

---

## 🎯 Objetivos

### Objetivo general

Desarrollar una simulación de un procesador de transacciones bancarias en Python que
integre mecanismos de sincronización concurrente, planificación de operaciones de disco
y control de acceso basado en roles, demostrando la aplicación práctica de los conceptos
fundamentales de los sistemas operativos.

### Objetivos específicos

- Implementar un modelo de concurrencia con `threading.Thread` y exclusión mutua con
  `threading.Lock` que garantice la consistencia del saldo de cada cuenta ante accesos
  simultáneos.
- Simular el algoritmo SCAN aplicado al subsistema de logging, modelando las entradas
  de log como solicitudes con número de bloque ficticio.
- Diseñar e integrar una política RBAC que restrinja las operaciones según el rol
  asignado a cada usuario.
- Implementar el **Algoritmo del Banquero** para prevención de interbloqueos en
  transferencias multi-cuenta.

---

## 📚 Marco conceptual

### Sincronización y condiciones de carrera

Una **condición de carrera** ocurre cuando dos o más hilos acceden simultáneamente a un
recurso compartido y el resultado depende del orden no determinístico de planificación
(Silberschatz et al., 2018). En el contexto bancario, dos operaciones concurrentes sobre
el mismo saldo pueden producir resultados inconsistentes sin exclusión mutua.

El **mutex** (`threading.Lock` en Python, equivalente a `pthread_mutex_t` en C/POSIX)
garantiza que solo un hilo acceda a la sección crítica en un momento dado. Los
**semáforos** (`threading.Semaphore`) extienden este concepto permitiendo controlar el
acceso de hasta N hilos concurrentes a un recurso.

### Patrón productor-consumidor

Estructura el subsistema de logging: los hilos de transacción actúan como
**productores** de entradas de log, y el hilo del planificador SCAN como
**consumidor**. La coordinación se realiza mediante una `queue.Queue` compartida,
que es thread-safe de forma nativa en Python.

### Algoritmo SCAN

También llamado **algoritmo del elevador**, mueve el cabezal del disco en una dirección
atendiendo todas las solicitudes en su camino, hasta llegar al extremo, momento en que
invierte su dirección (Silberschatz et al., 2018). Reduce el tiempo de búsqueda promedio
respecto a FCFS al minimizar el movimiento total del cabezal.

En el proyecto, SCAN se implementa sobre el buffer de logs: cada entrada tiene un
**número de bloque ficticio** y el planificador las ordena y procesa según esta lógica.

### Control de acceso basado en roles (RBAC)

Modelo estandarizado por el NIST (Ferraiolo et al., 2001) que organiza los permisos
alrededor de roles funcionales en lugar de usuarios individuales.

| Rol | Permisos |
|---|---|
| `AUDITOR` | Solo lectura (consulta de saldos) |
| `CAJERO` | Lectura + escritura (depósitos y retiros) |
| `ADMIN` | Acceso completo (incluye transferencias) |

### Algoritmo del Banquero *(componente adicional)*

Propuesto por Dijkstra (1965), evalúa cada solicitud de recursos verificando si su
concesión deja al sistema en un **estado seguro** — es decir, si existe al menos una
secuencia de procesos que pueda completar su ejecución sin generar espera circular
(Tanenbaum y Bos, 2015).

En el proyecto, cada cuenta que puede ser bloqueada simultáneamente se trata como un
recurso. Antes de ejecutar una transferencia multi-cuenta, `BankersGuard` verifica que
la asignación no genere interbloqueo.

---

## ⚙️ Especificaciones técnicas

### Librerías utilizadas

| Librería | Tipo | Uso |
|---|---|---|
| `threading` | Estándar | Hilos, `Lock`, `Semaphore`, `Condition` |
| `queue` | Estándar | Buffer thread-safe para transacciones y logs |
| `logging` | Estándar | Registro estructurado de eventos |
| `json` | Estándar | Persistencia de cuentas y roles |
| `dataclasses` | Estándar | Definición de estructuras con `@dataclass` |
| `enum` | Estándar | Roles RBAC y tipos de operación |
| `abc` | Estándar | Clases abstractas para interfaces |
| `time` / `random` | Estándar | Simulación de latencia y transacciones |
| `pytest` | Externa | Pruebas unitarias y de concurrencia |

> **Instalación:** `pip install pytest` (única dependencia externa)


> **Nota sobre el GIL:** El Global Interpreter Lock de CPython limita el paralelismo
> real sobre CPU, pero no elimina las condiciones de carrera sobre estructuras de datos
> compartidas. Los mecanismos de sincronización son necesarios y conceptualmente
> equivalentes a sus contrapartes POSIX.

---

## 🏗️ Arquitectura del sistema

<pre>
banco-transacciones-so/
│
├── main.py                        # Punto de entrada y orquestador
├── requirements.txt               # Dependencias (pytest)
├── README.md
│
├── core/                          # Módulo 1: Motor de cuentas
│   ├── __init__.py
│   ├── account.py                 # Clase Account con mutex propio
│   ├── transaction.py             # Modelo de datos Transaction
│   └── transaction_engine.py      # Motor productor-consumidor
│
├── scheduling/                    # Módulo 2: Planificador SCAN
│   ├── __init__.py
│   └── scan_scheduler.py          # Hilo consumidor con lógica SCAN
│
├── security/                      # Módulo 3: Control de acceso
│   ├── __init__.py
│   ├── roles.py                   # Enum de roles y permisos
│   └── rbac_policy.py             # Interceptor de operaciones
│
├── concurrency/                   # Módulo 4: Algoritmo del Banquero
│   ├── __init__.py
│   └── bankers_guard.py           # Verificación de estado seguro
│
├── logs/
│   └── transactions.log           # Generado en ejecución
│
└── tests/
    ├── __init__.py
    ├── test_account.py
    ├── test_scan.py
    └── test_rbac.py
</pre>


### Descripción de módulos

#### `core/` — Motor de cuentas y transacciones

- **`Account`**: representa una cuenta bancaria. Cada instancia tiene su propio
  `threading.Lock`. Los métodos `deposit()`, `withdraw()` y `get_balance()` adquieren
  el lock antes de operar, garantizando atomicidad.

- **`Transaction`**: modelo de datos que incluye tipo de operación, cuentas
  involucradas, monto, usuario solicitante y **número de bloque ficticio** para SCAN.

- **`TransactionEngine`**: implementa el patrón productor-consumidor. Los hilos
  productores envían transacciones a una `queue.Queue`; los consumidores las ejecutan
  bajo control del RBAC y el Algoritmo del Banquero. Un `threading.Semaphore` limita
  la concurrencia máxima.

#### `scheduling/` — Planificador SCAN

- **`ScanScheduler`**: hilo independiente que actúa como consumidor del buffer de logs.
  Mantiene estado de posición de cabezal y dirección, ordena las entradas pendientes
  según SCAN y las escribe en `transactions.log`.

#### `security/` — Control de acceso RBAC

- **`roles.py`**: define `Role` y `Permission` como enumeraciones, y la matriz de
  permisos por rol.
- **`RBACPolicy`**: intercepta cada transacción e invoca `authorize()`, que verifica
  que el permiso requerido esté en el conjunto del rol del usuario. Las operaciones no
  autorizadas lanzan `PermissionError` y quedan registradas en el log.

#### `concurrency/` — Algoritmo del Banquero *(adicional)*

- **`BankersGuard`**: antes de ejecutar cualquier transferencia multi-cuenta, simula
  el vector de trabajo (*work*) y el vector de finalización (*finish*) del algoritmo
  de Dijkstra. Solo aprueba la asignación si el estado resultante es seguro.

---

## 📅 Plan de trabajo

### Cronograma — 4 semanas

| Actividad | Sem 1 | Sem 2 | Sem 3 | Sem 4 |
|---|:---:|:---:|:---:|:---:|
| Revisión bibliográfica y conceptual | ✓ | | | |
| Diseño de arquitectura y contratos de módulos | ✓ | | | |
| Configuración del entorno y repositorio | ✓ | | | |
| Implementación Módulo 1 (cuentas y transacciones) | ✓ | ✓ | | |
| Implementación Módulo 2 (SCAN) | | ✓ | | |
| Implementación Módulo 3 (RBAC) | | ✓ | | |
| Implementación Módulo 4 (Algoritmo del Banquero) | | | ✓ | |
| Integración de los cuatro módulos | | | ✓ | |
| Pruebas de concurrencia (10, 30 y 50 hilos) | | | ✓ | ✓ |
| Documentación interna del código (docstrings) | | | | ✓ |
| Elaboración del informe final | | | | ✓ |
| Preparación de la presentación | | | | ✓ |

### Distribución de responsabilidades

| Integrante | Módulo principal | Apoyo |
|---|---|---|
| Integrante 1 | `core/` — Motor de cuentas y transacciones | Integración general y demo |
| Integrante 2 | `scheduling/` — Algoritmo SCAN y logging | Documentación e informe |
| Integrante 3 | `security/` y `concurrency/` — RBAC y Banquero | Pruebas unitarias con pytest |

---

## 🔀 Flujo de trabajo con Git
<pre>
### Ramas del proyecto
main                        ← siempre funcional, solo recibe Pull Requests aprobados
│
├── feature/modulo-cuentas  ← Integrante 1
├── feature/modulo-scan     ← Integrante 2
├── feature/modulo-rbac     ← Integrante 3
├── feature/modulo-banquero ← Integrante 3
└── feature/integracion     ← Todos (semana 3)
</pre>
### Ciclo de trabajo diario

```bash
# 1. Actualizar desde main antes de empezar
git checkout main
git pull origin main

# 2. Moverse a la rama propia
git checkout feature/modulo-cuentas

# 3. Trabajar... y guardar puntos de control
git add .
git commit -m "feat: implementar método deposit con mutex en Account"

# 4. Subir el trabajo
git push origin feature/modulo-cuentas
```

Luego en GitHub: **"Compare & pull request"** → asignar un compañero como revisor →
el compañero aprueba → se fusiona a `main`.

### Convención de mensajes de commit

| Prefijo | Uso |
|---|---|
| `feat:` | Nueva funcionalidad |
| `fix:` | Corrección de bug |
| `test:` | Agregar o modificar pruebas |
| `docs:` | Documentación |
| `refactor:` | Mejora de código sin cambio de comportamiento |

---

## 🚀 Cómo ejecutar el proyecto

### Requisitos previos

```bash
python --version    # Debe ser 3.10 o superior
git --version
```

### Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/usuario/banco-transacciones-so.git
cd banco-transacciones-so

# 2. Crear y activar el entorno virtual
python -m venv venv

# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt
```

### Ejecución

```bash
# Correr la simulación principal
python main.py

# Correr las pruebas unitarias
pytest tests/

# Correr pruebas con reporte de cobertura
pytest tests/ -v
```

### Salida esperada
<pre>
Al ejecutar `main.py` se mostrará en consola el estado en tiempo real:
[HILO-1] Transacción T001 | DEPOSIT     | Cuenta A001 | +$500.00  | ✓ Autorizado (CAJERO)
[HILO-2] Transacción T002 | TRANSFER    | A001 → A002 | $200.00   | ✓ Autorizado (ADMIN)
[HILO-3] Transacción T003 | QUERY       | Cuenta A003 |           | ✗ Denegado   (CAJERO)
[SCAN]   Escribiendo logs en orden de bloque: 12 → 18 → 25 → 34 → 41
[SCAN]   Invirtiendo dirección. Orden: 38 → 29 → 17 → 9
[BANQUERO] Solicitud T004 evaluada → Estado SEGURO ✓
[BANQUERO] Solicitud T005 evaluada → Estado INSEGURO ✗ — operación pospuesta

El archivo `logs/transactions.log` quedará con las entradas ordenadas según SCAN.
</pre>
---

## 👥 Equipo

| Nombre | GitHub | Módulo |
|---|---|---|
| Integrante 1 | Victor Correa | Motor de cuentas (`core/`) |
| Integrante 2 | Ivanna Ramirez | Planificador SCAN (`scheduling/`) |
| Integrante 3 | Santiago Jaramillo | RBAC y Banquero (`security/`, `concurrency/`) |

**Asignatura:** Sistemas Operativos  
**Institución:** Universidad Tecnológica de Pereira  
**Docente:** Juan Andrés Garcia Moreno
**Período:** 2026-1

---

## 📖 Referencias

- Dijkstra, E. W. (1965). Solution of a problem in concurrent programming control.
  *Communications of the ACM, 8*(9), 569. https://doi.org/10.1145/365559.365617

- Dijkstra, E. W. (1968). Cooperating sequential processes. En F. Genuys (Ed.),
  *Programming Languages* (pp. 43-112). Academic Press.

- Ferraiolo, D. F., Sandhu, R., Gavrila, S., Kuhn, D. R., y Chandramouli, R. (2001).
  Proposed NIST standard for role-based access control. *ACM Transactions on Information
  and System Security, 4*(3), 224-274. https://doi.org/10.1145/501978.501980

- Silberschatz, A., Galvin, P. B., y Gagne, G. (2018). *Operating system concepts*
  (10.a ed.). John Wiley & Sons.

- Tanenbaum, A. S., y Bos, H. (2015). *Modern operating systems* (4.a ed.).
  Pearson Education.

---

<div align="center">
  <sub>Proyecto académico — Sistemas Operativos · 2026</sub>
</div>