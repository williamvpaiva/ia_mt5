import logging
from typing import Dict, Optional

logger = logging.getLogger("ProgressManager")

class ProgressManager:
    """Gerencia o progresso de tarefas longas (Train, Sync) - SINGLETON REAL"""
    
    _instance = None
    _tasks: Dict[int, Dict] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ProgressManager, cls).__new__(cls)
            cls._tasks = {} # Initialize shared dictionary
        return cls._instance

    def update_progress(self, bot_id: int, task_type: str, progress: int, status: str = ""):
        """Atualiza a porcentagem de uma tarefa"""
        # Garante que bot_id seja tratado consistentemente
        self._tasks[int(bot_id)] = {
            "type": task_type,
            "progress": min(max(progress, 0), 100),
            "status": status
        }
        # print(f"[PROGRESS] Bot {bot_id} -> {progress}% ({status})")

    def get_progress(self, bot_id: int) -> Optional[Dict]:
        """Recupera o progresso de um bot especA?fico"""
        return self._tasks.get(int(bot_id))

    def get_all_progress(self) -> Dict[int, Dict]:
        """Retorna todo o progresso ativo"""
        # print(f"[DEBUG] Fetching all progress. Current size: {len(self._tasks)}")
        return self._tasks

    def clear_progress(self, bot_id: int):
        """Remove rastreamento de um bot"""
        bid = int(bot_id)
        if bid in self._tasks:
            del self._tasks[bid]

# Singleton
progress_manager = ProgressManager()
