class ChatHistoryTool:
    async def summarize_context(self, messages: list[dict], max_history: int = 10) -> str:
        recent = messages[-max_history:] if messages else []
        if not recent:
            return ""
        lines = []
        for msg in recent:
            role = msg.get("role", "user")
            content = msg.get("content", "")[:200]
            lines.append(f"**{role}**: {content}")
        return "\n".join(lines)
