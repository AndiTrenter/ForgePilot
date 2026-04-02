"""
Provider Registry System
Zentrale Verwaltung aller externen Service-Provider
"""
from typing import Optional, List, Dict, Any, Callable
from pydantic import BaseModel, Field, HttpUrl
from enum import Enum


class ProviderCategory(str, Enum):
    """Provider-Kategorien"""
    LLM = "llm"
    DATABASE = "database"
    STORAGE = "storage"
    AUTH = "auth"
    PAYMENT = "payment"
    EMAIL = "email"
    SMS = "sms"
    HOSTING = "hosting"
    CI_CD = "ci_cd"
    MONITORING = "monitoring"
    OTHER = "other"


class FieldType(str, Enum):
    """Feld-Typen für Konfiguration"""
    TEXT = "text"
    SECRET = "secret"
    NUMBER = "number"
    BOOLEAN = "boolean"
    SELECT = "select"
    URL = "url"


class ValidationRule(BaseModel):
    """Validierungs-Regel"""
    pattern: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    required: bool = True
    message: str = "Validation failed"


class FieldDefinition(BaseModel):
    """Feld-Definition für Provider-Konfiguration"""
    name: str
    label: str
    type: FieldType
    description: str
    placeholder: Optional[str] = None
    default: Optional[Any] = None
    validation: Optional[ValidationRule] = None
    options: Optional[List[Dict[str, str]]] = None  # Für SELECT-Felder


class ModelDefinition(BaseModel):
    """LLM-Model-Definition"""
    id: str
    name: str
    context_window: int
    cost_per_1k_input: float
    cost_per_1k_output: float
    capabilities: List[str] = Field(default_factory=list)
    max_output_tokens: Optional[int] = None


class ProviderMetadata(BaseModel):
    """Provider-Metadaten"""
    id: str
    name: str
    description: str
    category: ProviderCategory
    
    # URLs
    homepage_url: HttpUrl
    docs_url: HttpUrl
    create_key_url: HttpUrl
    manage_keys_url: HttpUrl
    status_page_url: Optional[HttpUrl] = None
    
    # Logo / Icon
    logo_url: Optional[HttpUrl] = None
    icon_emoji: Optional[str] = None
    
    # Configuration
    required_fields: List[FieldDefinition] = Field(default_factory=list)
    optional_fields: List[FieldDefinition] = Field(default_factory=list)
    env_var_names: Dict[str, str] = Field(default_factory=dict)
    
    # Capabilities
    capabilities: List[str] = Field(default_factory=list)
    models: List[ModelDefinition] = Field(default_factory=list)  # Für LLM-Provider
    
    # Status
    enabled: bool = False
    configured: bool = False
    
    class Config:
        use_enum_values = True


# ============== PROVIDER DEFINITIONS ==============

OPENAI_PROVIDER = ProviderMetadata(
    id="openai",
    name="OpenAI",
    description="OpenAI GPT Models für Text, Code und mehr",
    category=ProviderCategory.LLM,
    homepage_url="https://openai.com",
    docs_url="https://platform.openai.com/docs",
    create_key_url="https://platform.openai.com/api-keys",
    manage_keys_url="https://platform.openai.com/api-keys",
    status_page_url="https://status.openai.com",
    icon_emoji="🤖",
    required_fields=[
        FieldDefinition(
            name="api_key",
            label="API Key",
            type=FieldType.SECRET,
            description="Ihr OpenAI API Key",
            placeholder="sk-...",
            validation=ValidationRule(
                pattern=r"^sk-[A-Za-z0-9\-_]{48,}$",
                message="Muss mit 'sk-' beginnen"
            )
        )
    ],
    optional_fields=[
        FieldDefinition(
            name="organization_id",
            label="Organization ID",
            type=FieldType.TEXT,
            description="Optional: Organization ID",
            placeholder="org-..."
        )
    ],
    env_var_names={
        "api_key": "OPENAI_API_KEY",
        "organization_id": "OPENAI_ORG_ID"
    },
    capabilities=["text_generation", "code_generation", "embeddings", "chat", "vision"],
    models=[
        ModelDefinition(
            id="gpt-4o",
            name="GPT-4o",
            context_window=128000,
            cost_per_1k_input=0.0025,
            cost_per_1k_output=0.01,
            capabilities=["text", "code", "vision"]
        ),
        ModelDefinition(
            id="gpt-4o-mini",
            name="GPT-4o Mini",
            context_window=128000,
            cost_per_1k_input=0.00015,
            cost_per_1k_output=0.0006,
            capabilities=["text", "code", "vision"]
        ),
    ]
)

ANTHROPIC_PROVIDER = ProviderMetadata(
    id="anthropic",
    name="Anthropic",
    description="Claude Models für anspruchsvolle Aufgaben",
    category=ProviderCategory.LLM,
    homepage_url="https://anthropic.com",
    docs_url="https://docs.anthropic.com",
    create_key_url="https://console.anthropic.com/settings/keys",
    manage_keys_url="https://console.anthropic.com/settings/keys",
    status_page_url="https://status.anthropic.com",
    icon_emoji="🧠",
    required_fields=[
        FieldDefinition(
            name="api_key",
            label="API Key",
            type=FieldType.SECRET,
            description="Ihr Anthropic API Key",
            placeholder="sk-ant-...",
            validation=ValidationRule(
                pattern=r"^sk-ant-[A-Za-z0-9\-_]{40,}$",
                message="Muss mit 'sk-ant-' beginnen"
            )
        )
    ],
    env_var_names={
        "api_key": "ANTHROPIC_API_KEY"
    },
    capabilities=["text_generation", "code_generation", "reasoning", "chat"],
    models=[
        ModelDefinition(
            id="claude-sonnet-4-20250514",
            name="Claude Sonnet 4",
            context_window=200000,
            cost_per_1k_input=0.003,
            cost_per_1k_output=0.015,
            capabilities=["text", "code", "reasoning"]
        ),
        ModelDefinition(
            id="claude-haiku-4-20250611",
            name="Claude Haiku 4",
            context_window=200000,
            cost_per_1k_input=0.0008,
            cost_per_1k_output=0.004,
            capabilities=["text", "code"]
        ),
    ]
)

GOOGLE_PROVIDER = ProviderMetadata(
    id="google",
    name="Google AI",
    description="Gemini Models von Google",
    category=ProviderCategory.LLM,
    homepage_url="https://ai.google.dev",
    docs_url="https://ai.google.dev/docs",
    create_key_url="https://aistudio.google.com/apikey",
    manage_keys_url="https://aistudio.google.com/apikey",
    icon_emoji="✨",
    required_fields=[
        FieldDefinition(
            name="api_key",
            label="API Key",
            type=FieldType.SECRET,
            description="Ihr Google AI API Key",
            placeholder="AI...",
            validation=ValidationRule(
                pattern=r"^AI[A-Za-z0-9\-_]{30,}$",
                message="Muss mit 'AI' beginnen"
            )
        )
    ],
    env_var_names={
        "api_key": "GOOGLE_API_KEY"
    },
    capabilities=["text_generation", "code_generation", "vision", "chat"],
    models=[
        ModelDefinition(
            id="gemini-2.0-flash-exp",
            name="Gemini 2.0 Flash",
            context_window=1000000,
            cost_per_1k_input=0.0,
            cost_per_1k_output=0.0,
            capabilities=["text", "code", "vision"]
        ),
    ]
)

GITHUB_PROVIDER = ProviderMetadata(
    id="github",
    name="GitHub",
    description="GitHub Integration für Repository-Management",
    category=ProviderCategory.CI_CD,
    homepage_url="https://github.com",
    docs_url="https://docs.github.com",
    create_key_url="https://github.com/settings/tokens/new",
    manage_keys_url="https://github.com/settings/tokens",
    icon_emoji="🐙",
    required_fields=[
        FieldDefinition(
            name="token",
            label="Personal Access Token",
            type=FieldType.SECRET,
            description="GitHub PAT mit repo-Rechten",
            placeholder="ghp_...",
            validation=ValidationRule(
                pattern=r"^ghp_[A-Za-z0-9]{36}$",
                message="Muss mit 'ghp_' beginnen"
            )
        )
    ],
    env_var_names={
        "token": "GITHUB_TOKEN"
    },
    capabilities=["repository", "commits", "pull_requests", "actions"]
)


class ProviderRegistry:
    """Zentrale Provider-Registry"""
    
    def __init__(self):
        self._providers: Dict[str, ProviderMetadata] = {}
        self._register_builtin_providers()
    
    def _register_builtin_providers(self):
        """Registriert Built-in Provider"""
        self.register(OPENAI_PROVIDER)
        self.register(ANTHROPIC_PROVIDER)
        self.register(GOOGLE_PROVIDER)
        self.register(GITHUB_PROVIDER)
    
    def register(self, provider: ProviderMetadata):
        """Registriert einen Provider"""
        self._providers[provider.id] = provider
    
    def get(self, provider_id: str) -> Optional[ProviderMetadata]:
        """Holt Provider-Metadaten"""
        return self._providers.get(provider_id)
    
    def list_all(self) -> List[ProviderMetadata]:
        """Listet alle Provider"""
        return list(self._providers.values())
    
    def list_by_category(self, category: ProviderCategory) -> List[ProviderMetadata]:
        """Listet Provider nach Kategorie"""
        return [p for p in self._providers.values() if p.category == category]
    
    def get_llm_providers(self) -> List[ProviderMetadata]:
        """Holt alle LLM-Provider"""
        return self.list_by_category(ProviderCategory.LLM)


# Singleton Instance
_registry: Optional[ProviderRegistry] = None


def get_provider_registry() -> ProviderRegistry:
    """Gibt die globale Provider-Registry zurück"""
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
    return _registry
