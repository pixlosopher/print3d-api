---
name: print3d
description: Automated pipeline to generate 2D images, convert to 3D models, and send to 3D printing services.
---

# print3d Skill

Generate 2D images → Convert to 3D models → Get print pricing

## Quick Start

```python
from print3d import Pipeline

# Full pipeline
pipeline = Pipeline.from_env()
result = pipeline.run("a cute robot figurine", size_mm=50)

print(f"Mesh: {result.mesh_path}")
print(f"Cheapest: ${result.cheapest_material.price}")
```

## CLI Commands

```bash
# Full pipeline
print3d run "a robot" --size 50

# Individual steps
print3d generate "a robot"      # 2D image
print3d convert <image_url>     # Image → 3D
print3d validate model.stl      # Check mesh
print3d upload model.stl        # Upload to printer
print3d pricing <model_id>      # Get prices

# Check config
print3d config
```

## Pipeline Stages

| Stage | Module | API |
|-------|--------|-----|
| 1. Image Gen | `image_gen.py` | fal.ai / Gemini |
| 2. Image → 3D | `mesh_gen.py` | Meshy.ai |
| 3. Validation | `mesh_utils.py` | Local |
| 4. Upload | `print_api.py` | Shapeways |
| 5. Pricing | `print_api.py` | Shapeways |

## Configuration

Set in `.env` or environment:

```bash
# Required for 3D conversion
MESHY_API_KEY=your_key

# Required for printing
SHAPEWAYS_CLIENT_ID=your_id
SHAPEWAYS_CLIENT_SECRET=your_secret

# Image generation (one of these)
FAL_KEY=your_key
# or
GEMINI_API_KEY=your_key
```

## Styles for 3D

Available styles optimized for 3D conversion:

- `figurine` — Character figures, collectibles
- `object` — Product/object photography style
- `character` — Full-body characters in T-pose
- `sculpture` — Classical sculpture aesthetic
- `miniature` — Tabletop gaming miniatures

## Output Formats

- `stl` — Standard for 3D printing (default)
- `obj` — Universal format with materials
- `fbx` — Animation-ready
- `glb` — Web/AR compatible

## Example: Full Workflow

```python
from print3d import Pipeline, ImageStyle

# Initialize
pipeline = Pipeline.from_env()

# Run with progress
def on_progress(stage, pct, msg):
    print(f"[{pct*100:.0f}%] {msg}")

result = pipeline.run(
    prompt="a steampunk robot with gears and brass",
    style=ImageStyle.FIGURINE,
    size_mm=75,
    on_progress=on_progress,
)

# Check results
if result.is_complete:
    print(f"✅ Success!")
    print(f"   Image: {result.image_path}")
    print(f"   Mesh: {result.mesh_path}")
    
    if result.pricing:
        print(f"   Materials available: {len(result.pricing.materials)}")
        print(f"   Cheapest: ${result.pricing.cheapest.price:.2f}")
        
    # Save full result
    result.save("./output/result.json")
```

## Module Usage

### Just Image Generation

```python
from print3d import ImageGenerator, ImageStyle

gen = ImageGenerator()
result = gen.generate_for_3d("a dragon", ImageStyle.MINIATURE)
print(result.url)
```

### Just 3D Conversion

```python
from print3d import MeshGenerator

gen = MeshGenerator()
result = gen.from_image(
    "https://example.com/image.png",
    output_dir="./models",
    format="stl",
)
print(result.local_path)
```

### Just Mesh Validation

```python
from print3d.mesh_utils import validate_mesh, estimate_print_size

# Validate
result = validate_mesh("model.stl")
print(f"Valid: {result.is_valid}")
print(f"Issues: {result.issues}")

# Estimate size
size = estimate_print_size("model.stl", target_height_mm=50)
print(f"Scaled volume: {size['estimated_volume_mm3']:.2f} mm³")
```

### Just Upload & Price

```python
from print3d import PrintService

service = PrintService()

# Upload
upload = service.upload("model.stl")
print(f"Model ID: {upload.model_id}")

# Get pricing
pricing = service.get_pricing(upload.model_id)
for material in pricing.materials[:5]:
    print(f"  {material.name}: ${material.price:.2f}")
```
