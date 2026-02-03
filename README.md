# 🖨️ print3d

Automated pipeline: Generate 2D images → Convert to 3D models → Send to 3D printer

## Features

- **Modular design** — Use any step independently
- **Multiple backends** — fal.ai, Gemini for images; Meshy for 3D; Shapeways for printing
- **Type-safe** — Full type hints and Pydantic models
- **CLI included** — Command-line interface for quick use

## Installation

```bash
# Basic install
pip install -e .

# With CLI support
pip install -e ".[cli]"

# With mesh utilities (trimesh)
pip install -e ".[mesh]"

# Everything
pip install -e ".[all]"
```

## Quick Start

### 1. Configure API keys

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 2. Use as library

```python
from print3d import Pipeline

pipeline = Pipeline.from_env()

# Full pipeline: prompt → image → 3D → print pricing
result = pipeline.run(
    prompt="a cute robot with big eyes",
    style="figurine",
    size_mm=50
)

print(f"Image: {result.image_url}")
print(f"3D Model: {result.mesh_path}")
print(f"Cheapest print: ${result.pricing[0].price}")
```

### 3. Use individual modules

```python
from print3d import ImageGenerator, MeshGenerator, PrintService

# Just generate an image
image = ImageGenerator().generate("a robot")

# Just convert image to 3D
mesh = MeshGenerator().from_image(image.url)

# Just upload to printer
upload = PrintService().upload(mesh.local_path)
```

### 4. Use CLI

```bash
# Full pipeline
print3d run "a cute robot" --size 50mm

# Individual steps
print3d generate "a robot"           # Just image
print3d convert image.png            # Image → 3D
print3d upload model.stl             # Upload to printer
print3d pricing <model_id>           # Get prices
```

## Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `MESHY_API_KEY` | Meshy.ai API key | For 3D conversion |
| `SHAPEWAYS_CLIENT_ID` | Shapeways OAuth ID | For printing |
| `SHAPEWAYS_CLIENT_SECRET` | Shapeways OAuth secret | For printing |
| `FAL_KEY` | fal.ai API key | For image gen (option A) |
| `GEMINI_API_KEY` | Google Gemini key | For image gen (option B) |

## Architecture

```
print3d/
├── config.py      # Configuration management
├── image_gen.py   # 2D image generation
├── mesh_gen.py    # Image → 3D conversion (Meshy)
├── mesh_utils.py  # Mesh validation & manipulation
├── print_api.py   # 3D printing service (Shapeways)
├── pipeline.py    # Full pipeline orchestration
└── cli.py         # Command-line interface
```

## API Services Used

- **Image Generation**: [fal.ai](https://fal.ai) (Nano Banana Pro) or [Google Gemini](https://ai.google.dev)
- **3D Conversion**: [Meshy.ai](https://meshy.ai) 
- **3D Printing**: [Shapeways](https://shapeways.com)

## License

MIT
