# Azure Functions

Este repositorio contiene funciones serverless desarrolladas con **Azure Functions** en Python.

## ¿Qué son las Azure Functions?

**Azure Functions** es un servicio de computación serverless de Microsoft Azure que permite ejecutar código bajo demanda sin necesidad de aprovisionar ni administrar infraestructura. Solo pagas por el tiempo de ejecución real de tu código.

### Características principales

- **Serverless**: No es necesario gestionar servidores ni infraestructura.
- **Escalado automático**: Azure escala las instancias de forma automática según la demanda.
- **Orientadas a eventos**: Se activan mediante distintos desencadenadores (triggers).
- **Multi-lenguaje**: Compatibles con Python, JavaScript, C#, Java, PowerShell, entre otros.
- **Integración nativa**: Se integran fácilmente con otros servicios de Azure (Storage, Event Hubs, Cosmos DB, etc.).

### Tipos de desencadenadores (Triggers)

| Trigger         | Descripción                                              |
|-----------------|----------------------------------------------------------|
| **HTTP**        | Se activa mediante una petición HTTP (GET, POST, etc.)   |
| **Timer**       | Se ejecuta en un intervalo de tiempo definido (cron)     |
| **Blob Storage**| Se activa al subir o modificar un archivo en Blob Storage|
| **Queue**       | Se dispara cuando hay mensajes en una cola               |
| **Event Hub**   | Reacciona a eventos en tiempo real                       |
| **Cosmos DB**   | Se activa ante cambios en una base de datos Cosmos DB    |

### Niveles de autenticación HTTP

| Nivel        | Descripción                                                  |
|--------------|--------------------------------------------------------------|
| `Anonymous`  | No requiere clave; cualquiera puede llamar a la función      |
| `Function`   | Requiere una clave de función específica                     |
| `Admin`      | Requiere la clave maestra del host                           |

## Estructura del repositorio

```
AZ-Functions/
│
└── NormalizarFecha/          # Función para normalizar fechas en distintos formatos
    ├── function_app.py       # Código principal de la función
    ├── host.json             # Configuración global del host de Azure Functions
    ├── local.settings.json   # Variables de entorno para desarrollo local
    ├── requirements.txt      # Dependencias de Python
    └── README.md             # Documentación específica de la función
```

## Requisitos previos

- [Python 3.10+](https://www.python.org/)
- [Azure Functions Core Tools v4](https://learn.microsoft.com/es-es/azure/azure-functions/functions-run-local)
- [Azure CLI](https://learn.microsoft.com/es-es/cli/azure/install-azure-cli)
- Una cuenta activa en [Azure](https://azure.microsoft.com/)

## Ejecución local

```bash
# Crear y activar entorno virtual
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows (PowerShell)

# Instalar dependencias
pip install -r requirements.txt

# Iniciar el host de funciones
func start
```

## Despliegue en Azure

```bash
# Iniciar sesión en Azure
az login

# Crear un Function App (si no existe)
az functionapp create --resource-group <grupo> --consumption-plan-location <región> \
  --runtime python --runtime-version 3.10 --functions-version 4 \
  --name <nombre-app> --storage-account <cuenta-storage>

# Desplegar
func azure functionapp publish <nombre-app>
```

---

> Desarrollado con Azure Functions v4 · Python 3.10+
