try:
    # Caso 1: tu CLI expone main()
    from app.cli import main as _entry
except (ImportError, AttributeError):
    # Caso 2: Typer u otro callable llamado app
    from app.cli import app as _entry

if __name__ == "__main__":
    # Typer 'app' es invocable; main() también
    _entry()