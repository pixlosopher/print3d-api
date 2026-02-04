"""
Command-line interface for print3d pipeline.

Usage:
    print3d run "a cute robot" --size 50mm
    print3d generate "a robot"
    print3d convert image.png
    print3d upload model.stl
    print3d pricing <model_id>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

try:
    import typer
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    typer = None

from .config import get_config, load_config
from .image_gen import ImageGenerator, ImageStyle
from .mesh_gen import MeshGenerator
from .mesh_utils import validate_mesh, analyze_stl
from .print_api import PrintService
from .pipeline import Pipeline, PipelineStage


# Create app
if typer:
    app = typer.Typer(
        name="print3d",
        help="2D → 3D → Print Pipeline",
        add_completion=False,
    )
    console = Console() if HAS_RICH else None
else:
    app = None
    console = None


def _print(msg: str, style: str = None):
    """Print with optional rich styling."""
    if console and style:
        console.print(msg, style=style)
    else:
        print(msg)


def _print_json(data: dict):
    """Print JSON output."""
    print(json.dumps(data, indent=2))


# ─────────────────────────────────────────────────────────────
# Commands
# ─────────────────────────────────────────────────────────────

if app:
    
    @app.command()
    def run(
        prompt: str = typer.Argument(..., help="What to create"),
        style: str = typer.Option("figurine", "--style", "-s", help="Style: figurine, object, character, sculpture, miniature"),
        size: float = typer.Option(50.0, "--size", help="Target height in mm"),
        output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory"),
        skip_upload: bool = typer.Option(False, "--skip-upload", help="Skip print service upload"),
        as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
    ):
        """
        Run full pipeline: generate image → convert to 3D → get pricing.
        """
        try:
            style_enum = ImageStyle(style.lower())
        except ValueError:
            _print(f"Unknown style: {style}. Using 'figurine'.", "yellow")
            style_enum = ImageStyle.FIGURINE
        
        pipeline = Pipeline.from_env(output)
        
        if not as_json and console:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Starting...", total=None)
                
                def on_progress(stage: PipelineStage, pct: float, msg: str):
                    progress.update(task, description=f"[cyan]{msg}")
                
                result = pipeline.run(
                    prompt=prompt,
                    style=style_enum,
                    size_mm=size,
                    skip_print_upload=skip_upload,
                    on_progress=on_progress,
                )
        else:
            result = pipeline.run(
                prompt=prompt,
                style=style_enum,
                size_mm=size,
                skip_print_upload=skip_upload,
            )
        
        if as_json:
            _print_json(result.to_dict())
        else:
            _print(f"\n✅ Pipeline complete!", "bold green")
            _print(f"   Image: {result.image_path}")
            _print(f"   Mesh:  {result.mesh_path}")
            
            if result.pricing and result.pricing.cheapest:
                _print(f"   Cheapest print: ${result.pricing.cheapest.price:.2f} ({result.pricing.cheapest.name})")
            
            _print(f"   Duration: {result.duration_seconds:.1f}s")
    
    
    @app.command()
    def generate(
        prompt: str = typer.Argument(..., help="What to generate"),
        style: str = typer.Option("figurine", "--style", "-s", help="Style for 3D optimization"),
        output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
        as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
    ):
        """
        Generate a 2D image optimized for 3D conversion.
        """
        try:
            style_enum = ImageStyle(style.lower())
        except ValueError:
            style_enum = ImageStyle.FIGURINE
        
        gen = ImageGenerator()
        result = gen.generate_for_3d(prompt, style_enum, output)
        
        if as_json:
            _print_json(result.to_dict())
        else:
            _print(f"✅ Image generated!", "bold green")
            _print(f"   URL: {result.url}")
            if result.local_path:
                _print(f"   Saved: {result.local_path}")
    
    
    @app.command()
    def convert(
        image: Path = typer.Argument(..., help="Image file or URL"),
        output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory"),
        format: str = typer.Option("stl", "--format", "-f", help="Output format: stl, obj, fbx, glb"),
        as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
    ):
        """
        Convert an image to a 3D model.
        """
        # Determine if it's a URL or file
        image_str = str(image)
        if image_str.startswith(('http://', 'https://')):
            image_url = image_str
        else:
            if not image.exists():
                _print(f"File not found: {image}", "red")
                raise typer.Exit(1)
            # Would need to upload or use local file URL
            _print("Local file support requires uploading to a URL first", "yellow")
            raise typer.Exit(1)
        
        gen = MeshGenerator()
        
        if console:
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
                task = progress.add_task("Converting to 3D...", total=None)
                
                def on_progress(p: int):
                    progress.update(task, description=f"Converting: {p}%")
                
                result = gen.from_image(
                    image_url=image_url,
                    output_dir=output or Path("."),
                    format=format,
                    on_progress=on_progress,
                )
        else:
            result = gen.from_image(image_url=image_url, output_dir=output or Path("."), format=format)
        
        if as_json:
            _print_json(result.to_dict())
        else:
            _print(f"✅ 3D model generated!", "bold green")
            _print(f"   File: {result.local_path}")
            _print(f"   Task ID: {result.task_id}")
    
    
    @app.command()
    def validate(
        mesh: Path = typer.Argument(..., help="Mesh file to validate"),
        as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
    ):
        """
        Validate a mesh file for 3D printing.
        """
        if not mesh.exists():
            _print(f"File not found: {mesh}", "red")
            raise typer.Exit(1)
        
        result = validate_mesh(mesh)
        
        if as_json:
            _print_json(result.to_dict())
        else:
            if result.is_valid:
                _print(f"✅ Mesh is valid!", "bold green")
            else:
                _print(f"❌ Mesh has issues:", "bold red")
                for issue in result.issues:
                    _print(f"   • {issue}", "red")
            
            if result.warnings:
                _print("⚠️  Warnings:", "yellow")
                for warn in result.warnings:
                    _print(f"   • {warn}", "yellow")
            
            if result.info:
                _print(f"\nMesh info:")
                _print(f"   Triangles: {result.info.triangle_count:,}")
                if result.info.dimensions:
                    d = result.info.dimensions
                    _print(f"   Size: {d.width:.2f} × {d.depth:.2f} × {d.height:.2f}")
    
    
    @app.command()
    def upload(
        mesh: Path = typer.Argument(..., help="Mesh file to upload"),
        as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
    ):
        """
        Upload a mesh to the print service.
        """
        if not mesh.exists():
            _print(f"File not found: {mesh}", "red")
            raise typer.Exit(1)
        
        service = PrintService()
        result = service.upload(mesh)
        
        if as_json:
            _print_json(result.to_dict())
        else:
            _print(f"✅ Model uploaded!", "bold green")
            _print(f"   Model ID: {result.model_id}")
            _print(f"   Printable: {'Yes' if result.is_printable else 'No'}")
            if result.volume_cm3:
                _print(f"   Volume: {result.volume_cm3:.2f} cm³")
    
    
    @app.command()
    def pricing(
        model_id: str = typer.Argument(..., help="Model ID from upload"),
        max_price: Optional[float] = typer.Option(None, "--max", help="Max price filter"),
        as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
    ):
        """
        Get pricing for a model.
        """
        service = PrintService()
        result = service.get_pricing(model_id)
        
        materials = result.materials
        if max_price:
            materials = result.filter_by_price(max_price)
        
        if as_json:
            _print_json(result.to_dict())
        else:
            _print(f"💰 Pricing for model {model_id}:\n", "bold")
            
            if console:
                table = Table()
                table.add_column("Material", style="cyan")
                table.add_column("Color")
                table.add_column("Price", justify="right", style="green")
                
                for m in materials[:20]:  # Limit display
                    table.add_row(m.name, m.color, f"${m.price:.2f}")
                
                console.print(table)
            else:
                for m in materials[:20]:
                    print(f"  {m.name} ({m.color}): ${m.price:.2f}")
            
            if len(result.materials) > 20:
                _print(f"\n  ... and {len(result.materials) - 20} more materials")
    
    
    @app.command()
    def config(
        as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
    ):
        """
        Show configuration status.
        """
        cfg = get_config()
        pipeline = Pipeline(cfg)
        status = pipeline.check_config()
        
        if as_json:
            _print_json(status)
        else:
            _print("🔧 Configuration Status:\n", "bold")
            _print(f"   Image Generation: {'✅' if status['image_generation'] else '❌'}")
            _print(f"   Mesh Conversion:  {'✅' if status['mesh_conversion'] else '❌'}")
            _print(f"   Print Service:    {'✅' if status['print_service'] else '❌'}")
            _print(f"   Full Pipeline:    {'✅' if status['full_pipeline'] else '❌'}")
            
            if status['missing']:
                _print("\n⚠️  Missing:", "yellow")
                for item in status['missing']:
                    _print(f"   • {item}", "yellow")


def main():
    """Entry point for CLI."""
    if app is None:
        print("CLI requires typer and rich. Install with:")
        print("  pip install print3d[cli]")
        sys.exit(1)
    
    app()


if __name__ == "__main__":
    main()
