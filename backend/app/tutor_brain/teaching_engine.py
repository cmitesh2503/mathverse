class TeachingEngine:
    """
    A deterministic teaching engine flow without LLM dependencies.
    """
    def __init__(self):
        self.current_concept = None

    def start_concept(self, concept):
        self.current_concept = concept
        return f"Starting concept: {self.current_concept}"

    def teach_concept(self):
        if not self.current_concept:
            return "No concept currently started."
        return f"Teaching concept: {self.current_concept}"

    def check_understanding(self):
        if not self.current_concept:
            return "No concept currently started."
        return f"Checking understanding for: {self.current_concept}"

    def teach_again(self):
        if not self.current_concept:
            return "No concept currently started."
        return f"Teaching concept again using a different approach: {self.current_concept}"

    def next_concept(self, next_concept):
        self.current_concept = next_concept
        return f"Moving to next concept: {self.current_concept}"
