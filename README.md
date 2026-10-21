# Host Manager

Aplicación de escritorio para Windows que permite **ver y editar el archivo `hosts`** sin abrir el Bloc de notas como administrador. Muestra cada entrada en una tabla y deja activarla, desactivarla o borrarla con un clic.

## Funcionalidades

- Lista todas las entradas de `C:\Windows\System32\drivers\etc\hosts` con **IP, nombre de host, estado y descripción** (el comentario al final de la línea).
- Reconoce también las entradas comentadas con `#` y las muestra como desactivadas.
- **Activar / desactivar / eliminar** varias entradas a la vez.
- **Añadir host** con validación de la IP.
- **Copia de seguridad** automática antes de cada cambio (`hosts.backup_AAAAMMDD_HHMMSS`, junto al original) y también bajo demanda.
- Si la escritura falla, restaura el contenido original desde la copia.
- Pide permisos de administrador al arrancar si no los tiene.

## Tecnologías

- Python 3 con Tkinter (interfaz) y `ctypes` (elevación de permisos en Windows).
- PyInstaller para generar el `.exe`.

## Uso

### Desde el código

```bash
python main.py
```

### Crear el ejecutable

```bash
pip install -r requirements.txt
python create_exe.py
```

El ejecutable queda en `dist/HostManager.exe`.

## Estructura

| Archivo | Para qué sirve |
|---|---|
| `main.py` | La aplicación completa (lectura, edición segura y la interfaz). |
| `create_exe.py` | Genera el ejecutable con PyInstaller usando el mismo Python que lo lanza. |
| `HostManager.spec` | Configuración de PyInstaller. |

## Autor

Sergio Bernabé
