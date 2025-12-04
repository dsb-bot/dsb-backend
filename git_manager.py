import os
import subprocess
from utils import logger

class GitManager:
    def __init__(self, user, token, repo_name, repo_dir):
        self.user = user
        self.token = token
        self.repo_name = repo_name
        self.repo_dir = repo_dir
        
        # URL mit Token für Auth
        self.remote_url = f"https://{self.user}:{self.token}@github.com/{self.user}/{self.repo_name}.git"

    def initialize_repo(self):
        git_folder = os.path.join(self.repo_dir, ".git")

        if os.path.exists(git_folder):
            logger.info(f"Repo gefunden in {self.repo_dir}. Führe Sync durch...")
            try:
                self._run_git(["pull", "origin", "main"]) 
            except Exception as e:
                logger.warning(f"Git Pull fehlgeschlagen. Möglicherweise kein Remote-Branch oder keine Änderungen.")

        else:
            logger.info(f"Repo nicht gefunden. Clone {self.repo_name}...")
            parent_dir = os.path.dirname(self.repo_dir)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir)
            
            try:
                subprocess.run(["git", "clone", self.remote_url, self.repo_dir], check=True, capture_output=True)
                logger.info("Git Clone erfolgreich.")
            except subprocess.CalledProcessError as e:
                logger.critical(f"Git Clone fehlgeschlagen. Stdout: {e.stdout.strip()}, Stderr: {e.stderr.strip()}")
                raise e

    def push_changes(self, message="Automated update"):
        try:
            self._run_git(["remote", "set-url", "origin", self.remote_url])
            
            status = self._run_git(["status", "--porcelain"], capture_output=True)
            if not status.stdout.strip():
                logger.debug("Keine Änderungen zum Pushen gefunden.")
                return 

            self._run_git(["add", "."])
            self._run_git(["commit", "-m", message])
            self._run_git(["push", "origin", "main"])
            logger.info("Git Push erfolgreich.")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Git Push Fehler: {e.cmd} - {e.stderr.strip()}")
        except Exception as e:
            logger.error(f"Allgemeiner Git Push Fehler: {e}")

    def _run_git(self, args, capture_output=False):
        """Hilfsfunktion um Git Befehle im richtigen Ordner auszuführen."""
        return subprocess.run(
            ["git"] + args, 
            cwd=self.repo_dir, 
            check=True, 
            capture_output=capture_output,
            text=True
        )