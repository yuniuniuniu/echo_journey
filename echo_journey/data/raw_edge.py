class RawEdge:
    def __init__(self):
        self.invalid: bool = False
        self.to_node_index: int | str = ""
        self.from_node_index: int | str = ""
        self.jump_condition: str = ""

    def from_dict(self, raw_edge_dict: dict):
        self.invalid = raw_edge_dict["invalid"]
        self.to_node_index = raw_edge_dict["to_node_index"]
        self.from_node_index = raw_edge_dict["from_node_index"]
        self.jump_condition = raw_edge_dict["jump_condition"]
