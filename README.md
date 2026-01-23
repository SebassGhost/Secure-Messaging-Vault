# Secure Messaging Vault

Secure Messaging Vault es un proyecto experimental de **mensajería segura** diseñado bajo principios de **Zero Trust**.  
El sistema asume que **ningún componente es confiable por defecto**, ni siquiera el servidor o la base de datos.

El objetivo es aprender y demostrar cómo diseñar una arquitectura donde:
- Los datos siempre estén cifrados
- La identidad sea verificable criptográficamente
- La manipulación de información sea detectable
- El backend funcione como almacenamiento, no como autoridad

---

## Filosofía de Seguridad

Este proyecto sigue estos principios:

- **Zero Trust real**: todo se valida, siempre.
- **Cifrado end-to-end**: los mensajes se cifran en el cliente.
- **Identidad criptográfica**: cada usuario se identifica mediante claves.
- **Servidor no confiable**: la base de datos nunca ve datos en claro.
- **Auditoría posible**: cualquier alteración rompe la verificación.

No es una herramienta ofensiva ni un sistema de evasión.
Es un **laboratorio de aprendizaje** en criptografía y arquitectura segura.

---

## Requisitos

- Python 3.10+
- Docker Desktop (Windows / Linux)
- Docker Compose
- Git

---

## Base de Datos (PostgreSQL con Docker)

Desde la carpeta `secure_vault/`:

bash:
docker compose up -d

Verifica que esté corriendo:

docker compose ps

La base de datos se expone en:

Host: localhost

Puerto: 5432

### Generación de Identidad

Desde secure_vault/:

python client/identity.py


Esto genera:

Clave privada (local, nunca se comparte)

Clave pública (usada para verificación)

### Cifrado de Mensajes

python client/crypto.py


Este módulo se encarga de:

Cifrar mensajes

Firmarlos

Prepararlos para almacenamiento seguro

### Esquema de Base de Datos

El archivo db/schema.sql define tablas pensadas para:

Almacenar mensajes cifrados

Guardar claves públicas

Mantener trazabilidad sin comprometer privacidad

La base de datos nunca almacena texto plano.

# Estado del Proyecto

·En desarrollo
·Enfocado en aprendizaje y experimentación
·No listo para producción

# Nota Final

Este proyecto no busca ser “una app de chat más”.
Busca responder una pregunta más interesante:

¿Qué pasaría si asumimos que todo el sistema puede estar comprometido… y aún así seguimos siendo seguros?

