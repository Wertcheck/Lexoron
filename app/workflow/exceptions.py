"""Ausnahmen der Workflow-State-Machine."""


class InvalidTransitionError(Exception):
    """Wird ausgeloest, wenn ein nicht erlaubter Zustandsuebergang
    versucht wird. Der WorkflowRun bleibt dabei unveraendert."""
