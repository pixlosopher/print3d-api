# MEMORY.md - Agent3D Project State & History

## Current Status (February 2026)

### Implemented
- [x] Full 3D printing pipeline (prompt → print)
- [x] Multiple image generation backends (fal.ai, Gemini)
- [x] Meshy.ai integration for cloud 3D conversion
- [x] Local TripoSR integration (GPU-based)
- [x] Mesh validation with trimesh
- [x] Shapeways API integration
- [x] Flask-based agent service with job queue
- [x] Web dashboard at localhost:5000
- [x] CLI with Typer
- [x] SQLite persistence for jobs
- [x] Business plan defined

### In Progress
- [ ] Premium tier implementation
- [ ] Payment processing (Stripe)
- [ ] Moltbook OAuth integration
- [ ] Business registration (Agent3D LLC)

### Planned
- [ ] Agent collaboration features
- [ ] Design marketplace
- [ ] Mobile monitoring app
- [ ] Enterprise dashboard
- [ ] White-label solutions
- [ ] International expansion

---

## Configuration State

**Active API Keys** (from .env):
- `MESHY_API_KEY` - Configured
- `FAL_KEY` - Configured
- `GEMINI_API_KEY` - Configured
- `SHAPEWAYS_CLIENT_ID` - Configured
- `SHAPEWAYS_CLIENT_SECRET` - Configured

**Output Directory**: `./output/`
**Default Mesh Format**: STL
**Default Size**: 50mm

---

## File Inventory

### Core Pipeline (5 files)
| File | Lines | Purpose |
|------|-------|---------|
| config.py | ~109 | Pydantic settings |
| image_gen.py | ~200 | 2D generation |
| mesh_gen.py | ~250 | Image → 3D |
| mesh_utils.py | ~150 | Validation |
| print_api.py | ~200 | Shapeways |
| pipeline.py | ~435 | Orchestrator |

### Services (3+ variants)
- `agent_service.py` - Main Flask service
- `clean_agent_service.py` - Refined variant
- `premium_agent_service.py` - Enterprise tier
- `web/app.py` - REST endpoints

### CLI (2 variants)
- `cli.py` - Primary (Typer)
- `working_cli.py` - Alternative

### Experimental (many)
- `final_pipeline.py`
- `pipeline_local.py`
- `real_triposr.py`
- `triposr_*.py` (multiple variants)
- `generate_crypto_*.py`

---

## Known Issues

### Technical Debt
1. **Duplicate files**: Multiple versions of similar functionality
   - 3 agent_service variants
   - 2 CLI implementations
   - 5+ TripoSR integration attempts

2. **Inconsistent patterns**: Some files use different approaches
   - Mixed async patterns
   - Various import styles
   - Different error handling

3. **Missing tests**: Test coverage is minimal
   - `tests/` directory exists but sparse
   - Test files at root level

4. **No logging**: Uses print statements with emojis
   - No structured logging
   - No log levels

### API Concerns
1. **Shapeways OAuth**: Token refresh not implemented
2. **Rate limiting**: No rate limit handling
3. **Error recovery**: No retry logic for API failures

---

## Recent Changes

### Latest Session
- Explored complete codebase structure
- Created CLAUDE.md, SKILLS.md, MEMORY.md
- Identified improvement opportunities

### Previous Work
- Built TripoSR local integration
- Created multiple agent service variants
- Developed business plan
- Set up Moltbook skill documentation

---

## Dependencies

**Core** (pyproject.toml):
```
einops, httpx, huggingface-hub, omegaconf, pydantic,
requests, scipy, torch, torchvision, transformers, trimesh
```

**Optional**:
- `typer[all]` - CLI
- `flask` - Web service
- `gradio` - Local 3D UI
- `pytest` - Testing

---

## Environment Notes

- **Virtual Env**: `.venv/` (755MB)
- **Package Manager**: uv with uv.lock
- **Python Version**: 3.10+
- **GPU Required**: For local TripoSR only

---

## Quick Reference

### Start Development
```bash
cd /Users/pedrohernandezbaez/Documents/print3d
source .venv/bin/activate
```

### Run Pipeline
```bash
python -c "from print3d import Pipeline; Pipeline.from_env().run('robot')"
```

### Start Agent Service
```bash
python agent_service.py
```

### Check Config
```bash
print3d config
```

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| Feb 2026 | Use Meshy.ai as primary 3D | Best quality/speed balance |
| Feb 2026 | Add TripoSR fallback | Free local option |
| Feb 2026 | Flask over FastAPI | Simpler, adequate for MVP |
| Feb 2026 | SQLite for jobs | No external DB needed |
| Feb 2026 | Pydantic settings | Type-safe config |

---

## Contacts & Resources

- **Business Plan**: BUSINESS_PLAN.md
- **Skill Docs**: docs/SKILL.md
- **Moltbook Guide**: moltbook_3d_printing_skill.md
- **Shapeways API**: https://developers.shapeways.com
- **Meshy API**: https://docs.meshy.ai
- **TripoSR**: https://github.com/VAST-AI-Research/TripoSR
