class AnalysisResultsTool:
    async def format_for_llm(self, findings: dict) -> str:
        sections = []
        for category, items in findings.items():
            if items:
                sections.append(f"## {category}\n")
                for i, item in enumerate(items, 1):
                    sections.append(f"{i}. {item}\n")
        return "\n".join(sections) if sections else "No findings."
