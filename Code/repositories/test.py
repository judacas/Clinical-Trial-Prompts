from typing import List, Optional
from pydantic import BaseModel
import rich

class TreeNode(BaseModel):
    name: str
    children: Optional[List['TreeNode']] = None
    
node = TreeNode(name="root", children=[TreeNode(name="child1"), TreeNode(name="child2")])
rich.print(node.model_dump_json(indent=4, serialize_as_any=False, by_alias=False))