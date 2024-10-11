from dataclasses import dataclass
from tools.heal import Heal as bot

@dataclass
class BotStatistics:
    total_files: int = 0
    total_imports: int = 0
    total_classes: int = 0
    lines_used: int = 0
    functions_defined: int = 0
    total_coroutines: int = 0
    user_count: int = 0
    guild_count: int = 0
    uptime: int = 0