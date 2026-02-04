#!/usr/bin/env python3
"""
Prompt Engineering for 3D Printable Image Generation

Transforms any user input into optimized prompts that produce
clean images suitable for Meshy image-to-3D conversion.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PrintStyle(str, Enum):
    """Pre-defined styles optimized for 3D printing."""
    FIGURINE = "figurine"
    MINIATURE = "miniature"
    SCULPTURE = "sculpture"
    TOY = "toy"
    BUST = "bust"
    PROP = "prop"
    OBJECT = "object"
    JEWELRY = "jewelry"
    MECHANICAL = "mechanical"


@dataclass
class PromptConfig:
    """Configuration for prompt generation."""
    style: PrintStyle = PrintStyle.FIGURINE
    size_hint: str = "palm-sized"  # palm-sized, tabletop, large
    detail_level: str = "medium"   # low, medium, high
    include_base: bool = True      # Add a base/stand
    material_hint: str = "plastic" # plastic, resin, metal


# Core requirements that EVERY prompt should have
CORE_3D_REQUIREMENTS = [
    "3D printable design",
    "solid watertight mesh",
    "clean topology",
    "no floating parts",
    "structurally stable",
]

# Background requirements for clean Meshy processing
BACKGROUND_REQUIREMENTS = [
    "pure white background",
    "studio lighting",
    "centered composition",
    "isolated subject",
    "no shadows on background",
]

# Style-specific enhancements
STYLE_PROMPTS = {
    PrintStyle.FIGURINE: [
        "collectible figurine",
        "display piece",
        "smooth surfaces",
        "balanced proportions",
        "stable standing pose",
    ],
    PrintStyle.MINIATURE: [
        "detailed miniature",
        "tabletop gaming scale",
        "heroic proportions",
        "dynamic but stable pose",
        "thick base for stability",
    ],
    PrintStyle.SCULPTURE: [
        "artistic sculpture",
        "museum quality",
        "organic flowing forms",
        "fine art aesthetic",
        "elegant silhouette",
    ],
    PrintStyle.TOY: [
        "toy design",
        "child-safe rounded edges",
        "chunky durable form",
        "bright appealing design",
        "simple bold shapes",
    ],
    PrintStyle.BUST: [
        "portrait bust",
        "head and shoulders",
        "mounted on pedestal base",
        "classical sculpture style",
        "detailed facial features",
    ],
    PrintStyle.PROP: [
        "prop replica",
        "screen-accurate details",
        "functional appearance",
        "solid construction",
        "display ready",
    ],
    PrintStyle.OBJECT: [
        "functional object",
        "clean industrial design",
        "practical form",
        "geometric precision",
        "manufacturable shape",
    ],
    PrintStyle.JEWELRY: [
        "jewelry piece",
        "intricate but printable details",
        "smooth polished surfaces",
        "elegant delicate design",
        "wearable proportions",
    ],
    PrintStyle.MECHANICAL: [
        "mechanical design",
        "engineering aesthetic",
        "gears and mechanisms visible",
        "industrial steampunk style",
        "functional appearance",
    ],
}

# Negative prompt elements to avoid bad generations
NEGATIVE_PROMPTS = [
    "blurry",
    "low quality", 
    "distorted",
    "multiple objects",
    "busy background",
    "text",
    "watermark",
    "thin fragile parts",
    "disconnected pieces",
    "impossible geometry",
    "transparent parts",
    "complex internal structure",
]


def enhance_prompt(
    user_prompt: str,
    style: PrintStyle = PrintStyle.FIGURINE,
    config: Optional[PromptConfig] = None,
) -> dict:
    """
    Transform a user prompt into an optimized 3D-printable image prompt.
    
    Args:
        user_prompt: The user's original description
        style: The type of 3D print desired
        config: Additional configuration options
        
    Returns:
        dict with 'prompt' and 'negative_prompt' keys
    """
    config = config or PromptConfig(style=style)
    
    # Build the enhanced prompt
    parts = []
    
    # 1. Start with the user's core idea
    parts.append(user_prompt.strip().rstrip('.'))
    
    # 2. Add style-specific enhancements
    style_additions = STYLE_PROMPTS.get(config.style, STYLE_PROMPTS[PrintStyle.FIGURINE])
    parts.extend(style_additions[:3])  # Top 3 style traits
    
    # 3. Add core 3D printing requirements
    parts.extend(CORE_3D_REQUIREMENTS[:3])  # Most important ones
    
    # 4. Add background requirements
    parts.extend(BACKGROUND_REQUIREMENTS[:3])
    
    # 5. Add size/detail hints
    if config.size_hint:
        parts.append(f"{config.size_hint} scale")
    
    if config.include_base:
        parts.append("mounted on simple circular base")
    
    # 6. Quality boosters
    parts.extend([
        "high detail",
        "professional product photography",
        "8K render quality",
    ])
    
    # Build final prompt
    enhanced_prompt = ", ".join(parts)
    
    # Build negative prompt
    negative_prompt = ", ".join(NEGATIVE_PROMPTS)
    
    return {
        "prompt": enhanced_prompt,
        "negative_prompt": negative_prompt,
        "style": config.style.value,
        "original": user_prompt,
    }


def quick_enhance(user_prompt: str, style: str = "figurine") -> str:
    """
    Quick single-string enhancement for simple use cases.
    
    Args:
        user_prompt: What the user wants
        style: One of: figurine, miniature, sculpture, toy, bust, prop, object
        
    Returns:
        Enhanced prompt string ready for image generation
    """
    try:
        print_style = PrintStyle(style.lower())
    except ValueError:
        print_style = PrintStyle.FIGURINE
    
    result = enhance_prompt(user_prompt, style=print_style)
    return result["prompt"]


# Pre-built prompt templates for common use cases
TEMPLATES = {
    "character": lambda name: enhance_prompt(
        f"{name} character",
        style=PrintStyle.FIGURINE,
        config=PromptConfig(include_base=True, detail_level="high")
    ),
    "creature": lambda desc: enhance_prompt(
        f"{desc} creature",
        style=PrintStyle.MINIATURE,
        config=PromptConfig(include_base=True, size_hint="tabletop")
    ),
    "vehicle": lambda desc: enhance_prompt(
        f"{desc} vehicle",
        style=PrintStyle.PROP,
        config=PromptConfig(include_base=True, detail_level="medium")
    ),
    "weapon": lambda desc: enhance_prompt(
        f"{desc} weapon prop",
        style=PrintStyle.PROP,
        config=PromptConfig(include_base=False, size_hint="handheld")
    ),
    "bust": lambda name: enhance_prompt(
        f"portrait bust of {name}",
        style=PrintStyle.BUST,
        config=PromptConfig(include_base=True)
    ),
    "abstract": lambda desc: enhance_prompt(
        f"{desc} abstract sculpture",
        style=PrintStyle.SCULPTURE,
        config=PromptConfig(include_base=True)
    ),
}


def from_template(template_name: str, subject: str) -> dict:
    """
    Generate a prompt using a pre-built template.
    
    Args:
        template_name: One of: character, creature, vehicle, weapon, bust, abstract
        subject: The subject to insert into the template
        
    Returns:
        Enhanced prompt dict
    """
    if template_name not in TEMPLATES:
        available = ", ".join(TEMPLATES.keys())
        raise ValueError(f"Unknown template '{template_name}'. Available: {available}")
    
    return TEMPLATES[template_name](subject)


# CLI interface
if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("Usage: python prompt_engineer.py <prompt> [style]")
        print("Styles: figurine, miniature, sculpture, toy, bust, prop, object, jewelry, mechanical")
        print("\nExample:")
        print('  python prompt_engineer.py "a robot warrior" miniature')
        sys.exit(1)
    
    user_input = sys.argv[1]
    style = sys.argv[2] if len(sys.argv) > 2 else "figurine"
    
    result = enhance_prompt(user_input, style=PrintStyle(style))
    
    print("=" * 60)
    print("ENHANCED PROMPT FOR 3D PRINTING")
    print("=" * 60)
    print(f"\nOriginal: {result['original']}")
    print(f"Style: {result['style']}")
    print(f"\n📝 PROMPT:\n{result['prompt']}")
    print(f"\n🚫 NEGATIVE:\n{result['negative_prompt']}")
    print("=" * 60)
