import ctypes
import ipaddress
import os
import shutil
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk


HOSTS_PATH = Path(r"C:\Windows\System32\drivers\etc\hosts")


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin():
    """Relanza la aplicación con permisos elevados en Windows."""
    if not getattr(sys, "frozen", False):
        params = " ".join(f'"{arg}"' for arg in sys.argv)
        executable = sys.executable
        script = f'"{Path(__file__).resolve()}"'
        args = f"{script} {params}".strip()
    else:
        executable = sys.executable
        args = " ".join(f'"{arg}"' for arg in sys.argv[1:])
    try:
        result = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", executable, args, None, 1
        )
        return result > 32
    except Exception:
        return False


class HostManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Host Manager")
        self.root.geometry("950x600")
        self.root.minsize(760, 420)
        self.hosts_path = HOSTS_PATH
        self.entries = []
        self._build_ui()
        self.load_hosts()

        if not is_admin():
            self.root.after(250, self._ask_for_admin)

    def _ask_for_admin(self):
        if messagebox.askyesno(
            "Permisos de administrador",
            "Para modificar el archivo hosts se necesitan permisos de administrador.\n\n"
            "¿Quieres reiniciar Host Manager como administrador?"
        ):
            if relaunch_as_admin():
                self.root.destroy()
            else:
                messagebox.showwarning(
                    "Permisos",
                    "No se pudo solicitar la elevación. Cierra la aplicación y ejecútala "
                    "manualmente como administrador."
                )

    def _build_ui(self):
        toolbar = ttk.Frame(self.root, padding=(10, 10, 10, 5))
        toolbar.pack(fill=tk.X)

        ttk.Button(toolbar, text="Recargar", command=self.load_hosts).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="Añadir host", command=self.add_host_dialog).pack(side=tk.LEFT, padx=6)
        ttk.Button(toolbar, text="Crear copia de seguridad", command=self.backup_hosts).pack(side=tk.LEFT, padx=6)

        self.status_var = tk.StringVar(value="Preparado")
        ttk.Label(self.root, textvariable=self.status_var, padding=(12, 3)).pack(fill=tk.X)

        frame = ttk.Frame(self.root, padding=(10, 5, 10, 10))
        frame.pack(fill=tk.BOTH, expand=True)

        columns = ("ip", "hostname", "estado", "descripcion")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="extended")
        self.tree.heading("ip", text="IP")
        self.tree.heading("hostname", text="Nombre de host")
        self.tree.heading("estado", text="Estado")
        self.tree.heading("descripcion", text="Descripción")
        self.tree.column("ip", width=145, minwidth=120)
        self.tree.column("hostname", width=260, minwidth=160)
        self.tree.column("estado", width=110, minwidth=90, anchor=tk.CENTER)
        self.tree.column("descripcion", width=300, minwidth=140)

        self.tree.tag_configure("inactive", foreground="#888888")
        self.tree.tag_configure("active", foreground="#202020")

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        actions = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        actions.pack(fill=tk.X)
        ttk.Button(actions, text="Desactivar seleccionados", command=self.disable_selected).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(actions, text="Activar seleccionados", command=self.enable_selected).pack(side=tk.LEFT, padx=6)
        ttk.Button(actions, text="Eliminar seleccionados", command=self.delete_selected).pack(side=tk.LEFT, padx=6)

        note = (
            "Los hosts desactivados aparecen en gris. Las líneas de comentarios que no contienen "
            "una entrada IP/host se conservan sin mostrarse."
        )
        ttk.Label(self.root, text=note, wraplength=900, padding=(12, 0, 12, 4)).pack(fill=tk.X)

        # Firma del creador
        ttk.Label(
            self.root,
            text="Creado por Sergio Bernabé",
            anchor=tk.E,
            padding=(12, 0, 12, 8),
            font=("Segoe UI", 9, "italic"),
        ).pack(fill=tk.X)

    @staticmethod
    def _parse_host_line(line, line_index):
        """Devuelve una entrada si la línea contiene IP + hostname, activa o comentada."""
        stripped = line.strip()
        if not stripped:
            return None

        active = True
        candidate = stripped

        if candidate.startswith("#"):
            active = False
            candidate = candidate[1:].lstrip()
            # Un comentario normal no es una entrada de hosts.
            if not candidate:
                return None

        # Separa comentario final opcional; la parte previa debe empezar con una IP válida.
        parts = candidate.split("#", 1)
        host_part = parts[0].strip()
        description = parts[1].strip() if len(parts) > 1 else ""
        tokens = host_part.split()
        if len(tokens) < 2:
            return None

        ip_text = tokens[0]
        try:
            ipaddress.ip_address(ip_text)
        except ValueError:
            return None

        return {
            "line_index": line_index,
            "ip": ip_text,
            "hostname": tokens[1],
            "aliases": tokens[2:],
            "description": description,
            "active": active,
            "original_line": line,
        }

    def load_hosts(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.entries.clear()

        try:
            with self.hosts_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
                lines = f.readlines()
        except OSError as exc:
            messagebox.showerror(
                "No se pudo leer hosts",
                f"No se pudo leer el archivo:\n{self.hosts_path}\n\n{exc}"
            )
            self.status_var.set("Error al leer el archivo hosts")
            return

        for index, line in enumerate(lines):
            entry = self._parse_host_line(line, index)
            if entry is None:
                continue
            self.entries.append(entry)
            state = "Activo" if entry["active"] else "Desactivado"
            tag = "active" if entry["active"] else "inactive"
            aliases = " ".join(entry["aliases"])
            hostname_display = entry["hostname"] + (f" {aliases}" if aliases else "")
            self.tree.insert(
                "", tk.END,
                iid=str(index),
                values=(entry["ip"], hostname_display, state, entry["description"]),
                tags=(tag,)
            )

        active_count = sum(1 for e in self.entries if e["active"])
        inactive_count = len(self.entries) - active_count
        self.status_var.set(
            f"{active_count} activos · {inactive_count} desactivados · "
            f"{len(self.entries)} entradas detectadas"
        )

    def _read_lines(self):
        with self.hosts_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
            return f.readlines()

    def _write_lines_safely(self, lines):
        """
        Crea una copia de seguridad y escribe sobre el archivo existente.

        En Windows, sustituir hosts con os.replace() puede fallar porque el archivo
        temporal no hereda necesariamente la ACL del archivo protegido. Abrir el
        archivo original en modo escritura conserva sus permisos; la copia permite
        recuperar el contenido si algo sale mal.
        """
        backup = self._make_backup()
        content = "".join(lines)
        try:
            # Se escribe sobre el archivo existente para conservar sus ACL/permisos.
            with self.hosts_path.open("w", encoding="utf-8", newline="") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
        except Exception:
            # Intentar restaurar el contenido original desde la copia de seguridad.
            try:
                with backup.open("r", encoding="utf-8", errors="replace", newline="") as src:
                    original_content = src.read()
                with self.hosts_path.open("w", encoding="utf-8", newline="") as dst:
                    dst.write(original_content)
                    dst.flush()
                    os.fsync(dst.fileno())
            except Exception:
                pass
            raise

    def _make_backup(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = self.hosts_path.with_name(f"hosts.backup_{timestamp}")
        shutil.copy2(self.hosts_path, backup)
        return backup

    def backup_hosts(self):
        try:
            backup = self._make_backup()
            messagebox.showinfo("Copia creada", f"Copia de seguridad creada:\n{backup}")
        except OSError as exc:
            messagebox.showerror("Error", f"No se pudo crear la copia:\n{exc}")

    def _selected_entries(self):
        selected = self.tree.selection()
        result = []
        for iid in selected:
            try:
                index = int(iid)
                entry = next((e for e in self.entries if e["line_index"] == index), None)
                if entry:
                    result.append(entry)
            except (ValueError, TypeError):
                continue
        return result

    def add_host_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Añadir host")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        fields = {}
        labels = [("IP", "ip"), ("Nombre de host", "hostname"), ("Descripción (opcional)", "description")]
        for row, (label, key) in enumerate(labels):
            ttk.Label(dialog, text=label).grid(row=row, column=0, sticky=tk.W, padx=12, pady=7)
            entry = ttk.Entry(dialog, width=38)
            entry.grid(row=row, column=1, padx=12, pady=7)
            fields[key] = entry

        def save():
            ip = fields["ip"].get().strip()
            hostname = fields["hostname"].get().strip()
            description = fields["description"].get().strip()
            if not ip or not hostname:
                messagebox.showerror("Datos incompletos", "Introduce una IP y un nombre de host.", parent=dialog)
                return
            try:
                ipaddress.ip_address(ip)
            except ValueError:
                messagebox.showerror("IP no válida", "Introduce una dirección IPv4 o IPv6 válida.", parent=dialog)
                return
            if any(c.isspace() for c in hostname) or "#" in hostname:
                messagebox.showerror("Nombre no válido", "El nombre de host no puede contener espacios ni '#'.", parent=dialog)
                return
            try:
                lines = self._read_lines()
                for line in lines:
                    parsed = self._parse_host_line(line, -1)
                    if parsed and parsed["active"] and parsed["ip"] == ip and hostname in [parsed["hostname"], *parsed["aliases"]]:
                        messagebox.showwarning("Entrada duplicada", "Ese host ya existe y está activo.", parent=dialog)
                        return
                newline = "\r\n" if any(line.endswith("\r\n") for line in lines) else "\n"
                if lines and not lines[-1].endswith(("\n", "\r")):
                    lines[-1] += newline
                suffix = f" # {description}" if description else ""
                lines.append(f"{ip}\t{hostname}{suffix}{newline}")
                self._write_lines_safely(lines)
                dialog.destroy()
                self.load_hosts()
            except OSError as exc:
                messagebox.showerror("Error", f"No se pudo añadir el host:\n{exc}", parent=dialog)

        buttons = ttk.Frame(dialog)
        buttons.grid(row=3, column=0, columnspan=2, pady=10)
        ttk.Button(buttons, text="Guardar", command=save).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons, text="Cancelar", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        fields["ip"].focus_set()

    def _change_selected(self, make_active):
        entries = self._selected_entries()
        if not entries:
            messagebox.showwarning("Sin selección", "Selecciona una o más entradas.")
            return
        try:
            lines = self._read_lines()
            changed = 0
            for entry in entries:
                idx = entry["line_index"]
                if idx >= len(lines):
                    continue
                line = lines[idx]
                parsed = self._parse_host_line(line, idx)
                if not parsed or parsed["active"] == make_active:
                    continue
                body = line.lstrip()
                if make_active:
                    # Quita únicamente el primer marcador de comentario.
                    leading = line[:len(line) - len(line.lstrip())]
                    body = body.lstrip()[1:].lstrip()
                    lines[idx] = leading + body
                else:
                    leading = line[:len(line) - len(line.lstrip())]
                    lines[idx] = leading + "# " + body
                changed += 1
            if changed:
                self._write_lines_safely(lines)
            self.load_hosts()
            self.status_var.set(f"{changed} entrada(s) {'activada(s)' if make_active else 'desactivada(s)'}")
        except OSError as exc:
            messagebox.showerror("Error", f"No se pudo modificar el archivo hosts:\n{exc}")

    def disable_selected(self):
        self._change_selected(False)

    def enable_selected(self):
        self._change_selected(True)

    def delete_selected(self):
        entries = self._selected_entries()
        if not entries:
            messagebox.showwarning("Sin selección", "Selecciona una o más entradas.")
            return
        if not messagebox.askyesno(
            "Confirmar eliminación",
            f"¿Eliminar definitivamente {len(entries)} entrada(s) seleccionada(s)?\n"
            "Se creará una copia de seguridad antes de guardar."
        ):
            return
        try:
            lines = self._read_lines()
            indexes = {entry["line_index"] for entry in entries}
            new_lines = [line for i, line in enumerate(lines) if i not in indexes]
            self._write_lines_safely(new_lines)
            self.load_hosts()
        except OSError as exc:
            messagebox.showerror("Error", f"No se pudieron eliminar las entradas:\n{exc}")


if __name__ == "__main__":
    root = tk.Tk()
    app = HostManager(root)
    root.mainloop()
