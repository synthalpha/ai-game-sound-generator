"""Streamlit controller for audio generation.

This controller acts as an adapter between Streamlit UI and the use cases,
maintaining clean architecture principles.
"""

from dataclasses import dataclass

import streamlit as st


@dataclass
class GenerationRequest:
    """Request model for audio generation."""

    mood_tags: list[str]
    genre_tags: list[str]
    instrument_tags: list[str]
    tempo: str | None = None


@dataclass
class GenerationResponse:
    """Response model for audio generation."""

    success: bool
    audio_path: str | None = None
    error_message: str | None = None
    generation_time: float | None = None
    prompt: str | None = None


class StreamlitGeneratorController:
    """Controller for Streamlit audio generation UI.

    This controller follows clean architecture principles:
    - It doesn't contain business logic (that's in use cases)
    - It adapts between UI layer (Streamlit) and use cases
    - It handles UI-specific concerns like session state
    """

    def __init__(self, use_case=None):
        """Initialize the controller."""
        # TODO: 完全なDI実装時にuse_caseを必須にする
        self._use_case = use_case

    def generate_audio(self, request: GenerationRequest) -> GenerationResponse:
        """Generate audio based on selected tags.

        Args:
            request: Generation request with selected tags

        Returns:
            Generation response with audio path or error
        """
        try:
            # Convert tags to prompt
            prompt = self._build_prompt(request)

            if self._use_case:
                # TODO: 実際のuse case実装
                pass

            # 暫定的なモック応答（UIテスト用）
            return GenerationResponse(
                success=True,
                audio_path="generated_audio/sample.wav",
                prompt=prompt,
                generation_time=15.5,
            )

        except Exception as e:
            return GenerationResponse(
                success=False,
                error_message=str(e),
            )

    def _build_prompt(self, request: GenerationRequest) -> str:
        """Build prompt from selected tags.

        Args:
            request: Generation request with tags

        Returns:
            Combined prompt string
        """
        parts = []

        if request.mood_tags:
            parts.append(", ".join(request.mood_tags))
        if request.genre_tags:
            parts.append(", ".join(request.genre_tags))
        if request.instrument_tags:
            parts.append(", ".join(request.instrument_tags))
        if request.tempo:
            parts.append(request.tempo)

        return " ".join(parts) + " game music"

    def save_to_history(self, response: GenerationResponse) -> None:
        """Save generation to session history.

        Args:
            response: Generation response to save
        """
        if "generation_history" not in st.session_state:
            st.session_state.generation_history = []

        st.session_state.generation_history.append(
            {
                "prompt": response.prompt,
                "audio_path": response.audio_path,
                "generation_time": response.generation_time,
            }
        )

    def get_history(self) -> list[dict]:
        """Get generation history from session.

        Returns:
            List of generation history items
        """
        return st.session_state.get("generation_history", [])
