from typing import Dict, Any, List

TOOL_RETRIEVE_TRANSCRIPTS: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "retrieve_podcast_transcripts",
        "description": "Searches Lenny's Podcast transcript knowledge base for factual evidence, operator case studies, and framework explanations. Always cite the returned guest and timestamp.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Semantic search query describing the product/growth question."
                },
                "episode_slug": {
                    "type": "string",
                    "description": "Optional slug to restrict search to a specific guest or episode (e.g., 'brian-chesky', 'elena-verna')."
                }
            },
            "required": ["query"]
        }
    }
}

TOOL_GENERATE_SHIP30_ESSAY: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "generate_ship30_essay",
        "description": "Synthesizes a structured Ship 30 for 30 essay (~1,250 words) grounded strictly in retrieved podcast insights. Formats with punchy hook, skimmable list body, and actionable takeaway.",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "The specific growth or product topic to write about."
                },
                "core_thesis": {
                    "type": "string",
                    "description": "The central contrarian argument or framework from the podcast transcript."
                },
                "guest_source": {
                    "type": "string",
                    "description": "The guest whose insights anchor the essay (e.g. 'Brian Chesky', 'Elena Verna')."
                }
            },
            "required": ["topic", "core_thesis", "guest_source"]
        }
    }
}

TOOL_CREATE_ARTIFACT: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "create_artifact",
        "description": "Creates an interactive Markdown or HTML/CSS artifact to display in the side-by-side Artifact Viewer.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Descriptive title for the artifact."
                },
                "type": {
                    "type": "string",
                    "enum": ["markdown", "html"],
                    "description": "Format of the artifact: 'markdown' or 'html'."
                },
                "content": {
                    "type": "string",
                    "description": "Complete Markdown or self-contained HTML/CSS content."
                }
            },
            "required": ["title", "type", "content"]
        }
    }
}

ALL_TOOLS: List[Dict[str, Any]] = [
    TOOL_RETRIEVE_TRANSCRIPTS,
    TOOL_GENERATE_SHIP30_ESSAY,
    TOOL_CREATE_ARTIFACT
]
