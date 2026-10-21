import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
MAIN_FILE = PROJECT_DIR / "main.py"

def main():
    if not MAIN_FILE.exists():
        raise SystemExit(f"No se encuentra el archivo: {MAIN_FILE}")

    # Usa el mismo intérprete de Python para evitar instalar/empaquetar en otro entorno.
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
         "--onefile", "--windowed", "--name", "HostManager", str(MAIN_FILE)],
        cwd=PROJECT_DIR,
        check=True,
    )
    print(f"\nEjecutable creado en: {PROJECT_DIR / 'dist' / 'HostManager.exe'}")

if __name__ == "__main__":
    main()
