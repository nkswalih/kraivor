import tiktoken


class SemanticChunker:
    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.enc = tiktoken.get_encoding("cl100k_base")

    async def chunk_file(
        self, file_path: str, content: str, language: str
    ) -> list[dict]:
        if language in ("python", "javascript", "typescript", "jsx", "tsx"):
            chunks = await self._chunk_with_ast(file_path, content, language)
        else:
            chunks = await self._chunk_by_tokens(file_path, content)

        for chunk in chunks:
            chunk["file_path"] = file_path
            chunk["language"] = language
            chunk["token_count"] = len(self.enc.encode(chunk["content"]))

        return chunks

    async def _chunk_with_ast(
        self, file_path: str, content: str, language: str
    ) -> list[dict]:
        try:
            import tree_sitter_python as tspython
            import tree_sitter_javascript as tsjavascript
            import tree_sitter_typescript as tstypescript
            from tree_sitter import Language, Parser

            languages = {
                "python": Language(tspython.language()),
                "javascript": Language(tsjavascript.language()),
                "typescript": Language(tstypescript.language_typescript()),
            }

            if language not in languages:
                return await self._chunk_by_tokens(file_path, content)

            parser = Parser(languages[language])
            tree = parser.parse(bytes(content, "utf-8"))

            chunks = []
            cursor = tree.walk()

            def visit(node):
                if node.type in ("function_definition", "class_definition",
                                  "method_definition", "arrow_function"):
                    start_line = node.start_point[0]
                    end_line = node.end_point[0]
                    chunk_content = content[node.start_byte:node.end_byte]
                    chunks.append({
                        "content": chunk_content,
                        "start_line": start_line + 1,
                        "end_line": end_line + 1,
                    })

                for child in node.children:
                    visit(child)

            visit(tree.root_node)

            if not chunks:
                return await self._chunk_by_tokens(file_path, content)

            return chunks
        except ImportError:
            return await self._chunk_by_tokens(file_path, content)

    async def _chunk_by_tokens(
        self, file_path: str, content: str
    ) -> list[dict]:
        tokens = self.enc.encode(content)
        chunks = []

        for i in range(0, len(tokens), self.chunk_size - self.overlap):
            chunk_tokens = tokens[i: i + self.chunk_size]
            chunk_content = self.enc.decode(chunk_tokens)
            chunks.append({
                "content": chunk_content,
                "start_line": self._offset_to_line(content, i),
                "end_line": self._offset_to_line(
                    content, min(i + self.chunk_size, len(tokens))
                ),
            })

        return chunks

    @staticmethod
    def _offset_to_line(content: str, offset: int) -> int:
        return content[:offset].count("\n") + 1
