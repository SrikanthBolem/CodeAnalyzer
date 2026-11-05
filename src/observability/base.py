class ObservabilityProvider:
    """Extension point for LangSmith or another tracing backend."""
    def trace_start(self, operation, metadata=None):
        return None

    def trace_end(self, operation, result=None):
        return None

    def record_error(self, operation, error):
        return None
