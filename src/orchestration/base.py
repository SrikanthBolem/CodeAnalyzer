class AnalysisOrchestrator:
    """Extension point for a future LangGraph-backed workflow."""
    def analyze(self, source, provider):
        raise NotImplementedError
