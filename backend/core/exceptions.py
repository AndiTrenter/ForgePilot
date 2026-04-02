"""
Custom Exceptions für das ForgePilot System
"""


class ForgePilotException(Exception):
    """Base Exception für alle ForgePilot Exceptions"""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class StateTransitionError(ForgePilotException):
    """Fehler bei ungültiger Zustandsübergabe"""
    pass


class GateViolationError(ForgePilotException):
    """Fehler wenn Completion-Gates nicht erfüllt sind"""
    def __init__(self, message: str, failed_checks: list[str]):
        super().__init__(message, {"failed_checks": failed_checks})
        self.failed_checks = failed_checks


class ProvisioningError(ForgePilotException):
    """Fehler bei Environment-Provisioning"""
    pass


class ToolExecutionError(ForgePilotException):
    """Fehler bei Tool-Ausführung"""
    pass


class ProviderNotConfiguredError(ForgePilotException):
    """Provider ist nicht konfiguriert"""
    pass


class ModelNotAvailableError(ForgePilotException):
    """Angefordertes Model nicht verfügbar"""
    pass


class EvidenceCollectionError(ForgePilotException):
    """Fehler beim Sammeln von Evidence"""
    pass


class ValidationError(ForgePilotException):
    """Validierungsfehler"""
    pass


class AuthorizationError(ForgePilotException):
    """Agent hat keine Berechtigung für diese Aktion"""
    pass
