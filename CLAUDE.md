# CLAUDE.md - Agent3D Project Context

## Project Overview

**Agent3D** is an AI agent-native 3D printing platform that converts text prompts into physical 3D-printed objects. The pipeline: Text → 2D Image → 3D Model → Print Service.

## Tech Stack

- **Language**: Python 3.10+ with async/await
- **Web Framework**: Flask (REST API)
- **CLI**: Typer
- **Data Validation**: Pydantic + pydantic-settings
- **3D Processing**: Trimesh, PyTorch, TripoSR
- **Package Manager**: uv (with pyproject.toml)

## Project Structure

```
print3d/
├── Core Pipeline
│   ├── config.py          # Pydantic settings from .env
│   ├── image_gen.py       # 2D generation (fal.ai/Gemini)
│   ├── mesh_gen.py        # Image→3D (Meshy.ai API)
│   ├── mesh_utils.py      # Mesh validation (trimesh)
│   ├── print_api.py       # Shapeways integration
│   └── pipeline.py        # Orchestrator (async + sync)
│
├── Services
│   ├── agent_service.py   # Flask + job queue for agents
│   └── web/app.py         # REST API endpoints
│
├── CLI
│   ├── cli.py             # Primary CLI (Typer)
│   └── working_cli.py     # Alternative implementation
│
├── Local 3D (local-3d/)
│   ├── run.py             # TripoSR inference
│   └── tsr/               # TripoSR model code
│
└── Output
    └── output/            # Generated images, meshes, JSON results
```

## Key Commands

```bash
# Install
pip install -e ".[all]"

# Run full pipeline
print3d run "a cute robot" --size 50

# Individual steps
print3d generate "a robot"      # Image only
print3d convert image.png       # Image→3D
print3d validate model.stl      # Check mesh
print3d upload model.stl        # Upload to Shapeways

# Start agent service
python agent_service.py         # http://localhost:5000

# Check config
print3d config
```

## API Keys Required (.env)

```bash
MESHY_API_KEY=          # 3D conversion (required)
FAL_KEY=                # Image gen option A
GEMINI_API_KEY=         # Image gen option B
SHAPEWAYS_CLIENT_ID=    # Printing (optional)
SHAPEWAYS_CLIENT_SECRET=
```

## Architecture Patterns

1. **Lazy Initialization**: Pipeline components init on first use
2. **Async-First**: All API calls are async with sync wrappers
3. **Type-Safe**: Full Pydantic models for all data
4. **Singleton Config**: `get_config()` returns cached instance
5. **Progress Callbacks**: Real-time status via callbacks
6. **Queue-Based Jobs**: Background processing in agent_service

## Code Conventions

- Use `dataclass` for simple DTOs, `Pydantic` for validated models
- Async methods end with `_async`, sync wrappers have same name without suffix
- All paths use `pathlib.Path`
- Enums for fixed choices (ImageStyle, PipelineStage, JobStatus)
- Type hints required on all public functions

## Pipeline Stages

1. `IMAGE_GENERATION` - fal.ai or Gemini → PNG
2. `MESH_CONVERSION` - Meshy.ai or TripoSR → STL/OBJ/GLB
3. `MESH_VALIDATION` - Local trimesh validation
4. `PRINT_UPLOAD` - Shapeways upload
5. `PRICING` - Get material costs

## Testing

```bash
pytest tests/
python test_pipeline.py
python test_simple.py
```

## Output Formats

- **Images**: PNG (optimized for 3D conversion)
- **Meshes**: STL (default), OBJ, GLB, FBX
- **Results**: JSON with full metadata

## Common Patterns

```python
# Library usage
from print3d import Pipeline, ImageStyle
pipeline = Pipeline.from_env()
result = pipeline.run("robot", style=ImageStyle.FIGURINE, size_mm=50)

# Progress tracking
def on_progress(stage, pct, msg):
    print(f"[{pct*100:.0f}%] {msg}")
result = pipeline.run("robot", on_progress=on_progress)

# Partial pipeline
result = pipeline.run_from_image("https://...", size_mm=50)
result = pipeline.run_from_mesh("model.stl")
```

## Debugging

- Check `output/*.json` for pipeline results
- Agent service dashboard: http://localhost:5000
- SQLite DB: `agent_service.db` (job persistence)
- Logs use print statements with emoji prefixes

## Business Context

- Partnership: R2 (40% tech) + Pedro (60% business)
- Target: AI agents via Moltbook integration
- Revenue: Subscription tiers + APC (Agent Print Credits)
- See BUSINESS_PLAN.md for full details
