"""Update _save_state in sim/championship.py with Windows open file fallback."""
import pathlib

ROOT = pathlib.Path(r"c:\Coding\F1Sim2D")
champ_file = ROOT / "sim" / "championship.py"
text = champ_file.read_text(encoding="utf-8")

old_save = """            tmp = self.save_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            os.replace(tmp, self.save_path)
        except Exception:
            pass"""

new_save = """            serialized = json.dumps(payload, indent=2)
            try:
                tmp = self.save_path.with_suffix(".tmp")
                tmp.write_text(serialized, encoding="utf-8")
                os.replace(tmp, self.save_path)
            except (PermissionError, OSError):
                # Fallback on Windows if championship_state.json is held open in an editor or viewer
                self.save_path.write_text(serialized, encoding="utf-8")
                if tmp.exists():
                    try:
                        tmp.unlink()
                    except Exception:
                        pass
        except Exception:
            pass"""

assert old_save in text, "old_save not found"
text = text.replace(old_save, new_save)
champ_file.write_text(text, encoding="utf-8")
print("Successfully updated _save_state in sim/championship.py")

