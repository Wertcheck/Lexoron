"""Prompt-Bibliothek: 'Vorlagen & Muster' -> 'Standard-Prompts' (Schritt 3, Teil 2)."""

from app.prompt_library.rendering import extract_variables, render_template
from app.prompt_library.schema import PromptTemplateInput
from app.prompt_library.service import PromptTemplateService
from app.prompt_library.system_prompts import SYSTEM_PROMPT_REFERENCES, SystemPromptReference

__all__ = [
    "PromptTemplateService",
    "PromptTemplateInput",
    "render_template",
    "extract_variables",
    "SYSTEM_PROMPT_REFERENCES",
    "SystemPromptReference",
]
