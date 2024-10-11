from discord.ext.commands import Converter, BasicFlags
from typing import Optional

class ScriptFlags(BasicFlags):
    allow_role_mentions: bool = False
    allow_everyone_mention: bool = False
    disallow_users_mention: bool = False
    delete_after: Optional[int] = None