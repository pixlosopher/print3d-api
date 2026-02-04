# SKILLS.md - Agent3D Capabilities

## Core Skills

### 1. Text-to-3D-Print Pipeline
**Trigger**: "create/print/generate [object description]"

Converts natural language descriptions into 3D-printable models with pricing.

```python
from print3d import Pipeline
result = Pipeline.from_env().run("a steampunk owl", size_mm=75)
```

**Outputs**:
- PNG image optimized for 3D
- STL/OBJ/GLB mesh file
- Pricing from Shapeways

---

### 2. Image Generation (2D)
**Trigger**: "generate image of [description]"

Creates 2D images optimized for 3D conversion using templates.

**Styles**:
| Style | Best For | Template |
|-------|----------|----------|
| `figurine` | Collectibles, characters | Centered, neutral BG, clean edges |
| `sculpture` | Art pieces | Classical aesthetic, dramatic lighting |
| `character` | Full-body figures | T-pose, full body visible |
| `object` | Products, props | Studio lighting, white background |
| `miniature` | Tabletop gaming | High detail, dynamic pose |

```python
from print3d import ImageGenerator, ImageStyle
result = ImageGenerator().generate("a dragon", ImageStyle.MINIATURE)
```

---

### 3. Image-to-3D Conversion
**Trigger**: "convert [image] to 3D"

Transforms 2D images into 3D meshes.

**Backends**:
- **Meshy.ai** (cloud) - Higher quality, requires API key
- **TripoSR** (local) - Free, runs locally with GPU

```python
from print3d import MeshGenerator
result = MeshGenerator().from_image("image.png", format="stl")
```

---

### 4. Mesh Validation
**Trigger**: "validate/check [mesh file]"

Analyzes 3D models for printability issues.

**Checks**:
- Manifoldness (watertight)
- Dimensions and scale
- Triangle count
- Volume estimation
- Wall thickness

```python
from print3d.mesh_utils import validate_mesh
result = validate_mesh("model.stl")
print(f"Valid: {result.is_valid}, Issues: {result.issues}")
```

---

### 5. Print Service Integration
**Trigger**: "upload/price [mesh file]"

Uploads models to Shapeways and retrieves pricing.

```python
from print3d import PrintService
service = PrintService()
upload = service.upload("model.stl")
pricing = service.get_pricing(upload.model_id)
for mat in pricing.materials[:5]:
    print(f"{mat.name}: ${mat.price}")
```

---

### 6. Agent Job Submission
**Trigger**: REST API call to agent service

Autonomous job processing for AI agents.

```bash
# Submit job
curl -X POST http://localhost:5000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"agent_name": "CreativeBot", "description": "robot with LED eyes"}'

# Check status
curl http://localhost:5000/api/jobs/{job_id}
```

---

### 7. Cost Estimation
**Trigger**: "estimate cost for [size]mm [style]"

Estimates printing costs without full pipeline.

```python
volume_cm3 = (size_mm / 10) ** 3
costs = {
    "PLA Plastic": volume_cm3 * 0.05 + 5,
    "Resin": volume_cm3 * 0.15 + 8,
    "Steel": volume_cm3 * 2.50 + 15
}
```

---

## CLI Skills

```bash
# Full pipeline
print3d run "cute robot" --size 50 --style figurine

# Individual operations
print3d generate "a dragon"              # Image only
print3d convert image.png --format glb   # Image → 3D
print3d validate model.stl               # Check mesh
print3d upload model.stl                 # Upload to printer
print3d pricing MODEL_ID                 # Get prices
print3d config                           # Show configuration
```

---

## Skill Combinations

### Batch Processing
```python
prompts = ["robot", "dragon", "owl"]
for prompt in prompts:
    result = pipeline.run(prompt, size_mm=50)
    print(f"{prompt}: ${result.cheapest_material.price}")
```

### Custom Workflow
```python
# Generate multiple options
images = [image_gen.generate(f"robot style {i}") for i in range(3)]

# User selects best one
chosen = images[0]

# Convert and price
mesh = mesh_gen.from_image(chosen.url)
pricing = print_service.get_pricing(mesh.model_id)
```

### Progress Monitoring
```python
def on_progress(stage, pct, msg):
    print(f"[{stage.value}] {pct*100:.0f}% - {msg}")

result = pipeline.run("robot", on_progress=on_progress)
```

---

## Limitations

- **Image Gen**: Requires FAL_KEY or GEMINI_API_KEY
- **3D Conversion**: Requires MESHY_API_KEY or local GPU
- **Printing**: Requires Shapeways OAuth credentials
- **Size Range**: 10-500mm recommended
- **Mesh Formats**: STL, OBJ, GLB, FBX only
- **Style Options**: figurine, sculpture, object, character, miniature

---

## Integration Points

| Platform | Integration Method |
|----------|-------------------|
| Moltbook | OAuth + REST API (planned) |
| Custom Agents | REST API at /api/jobs |
| Python Apps | Direct import of print3d package |
| CLI Tools | print3d command |
| Web UI | http://localhost:5000 dashboard |
