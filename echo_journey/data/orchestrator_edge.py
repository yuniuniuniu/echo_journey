from .orchestrator_node import OrchestratorNode


class OrchestratorEdge:
    def __init__(
        self,
        from_node: OrchestratorNode,
        to_node: OrchestratorNode,
        jump_condition: str,
    ) -> None:
        self.from_node: OrchestratorNode = from_node
        self.to_node: OrchestratorNode = to_node
        self.jump_condition: str = jump_condition

    def is_activated(self) -> bool:
        if self.jump_condition:
            namespace = {"from_node": self.from_node, "to_node": self.to_node}
            exec(self.jump_condition, namespace)
            return namespace["is_activated"]
        else:
            return True
