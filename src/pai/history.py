from typing import Any, Optional
from pydantic.dataclasses import dataclass


class HistoryNode:
    @dataclass
    class UserCode:
        code: str
        result: str

    @dataclass
    class LLMCode:
        prompt: str
        code: str
        result: str
        raw_resp: Any

    @dataclass
    class LLMError:
        prompt: str
        error: str
        raw_resp: Any

    @dataclass
    class LLMMessage:
        prompt: str
        message: str
        raw_resp: Any

    @dataclass
    class Root:
        pass

    Data = UserCode | LLMCode | LLMMessage | LLMError | Root

    data: Data
    children: list["HistoryNode"] = []
    parent: Optional["HistoryNode"] = None
    depth: int = 0

    def __init__(self, data: Data):
        self.data = data
        self.children = []
        self.parent = None
        self.depth = 0

    def add_child(self, child_node):
        child_node.parent = self
        child_node.depth = self.depth + 1
        self.children.append(child_node)


class HistoryTree:
    def __init__(self):
        self.root = HistoryNode(HistoryNode.Root())
        self.cursor = self.root

    def add_node(self, data: HistoryNode.Data):
        """Add a new execution to the history tree."""
        new_node = HistoryNode(data)
        self.cursor.add_child(new_node)
        self.cursor = new_node

    def move_up(self):
        """Move the cursor to the parent node."""
        if self.cursor.parent:
            self.cursor = self.cursor.parent

    def move_to_child(self, index: int):
        """Move the cursor to a specified child node."""
        if 0 <= index < len(self.cursor.children):
            self.cursor = self.cursor.children[index]

    def branch_from(self, node):
        """Set the cursor to a specific node."""
        self.cursor = node

    def current_position(self) -> HistoryNode:
        """Get the current node the cursor is pointing to."""
        return self.cursor

    def lineage(self) -> list[HistoryNode]:
        """Get the lineage of the current node starting from the root."""
        lineage = []
        node = self.cursor
        while node:
            lineage.append(node)
            node = node.parent
        # remove the root node
        lineage.pop()
        # reverse the list so that the root is first
        lineage.reverse()
        return lineage

    def __repr__(self):
        return f"HistoryTree(cursor={self.cursor})"
