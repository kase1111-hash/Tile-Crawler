#!/usr/bin/env python3
"""
Font Generation Script for Tile-Crawler

Generates the custom TileCrawler font from glyph definitions.

Usage:
    python scripts/generate_font.py [options]

Options:
    --glyphs PATH    Path to glyphs.json (default: data/glyphs.json)
    --output PATH    Output font path (default: frontend/public/fonts/TileCrawler.otf)
    --sprites        Also export individual sprite PNGs
    --sprites-dir    Directory for sprite output (default: frontend/public/sprites)
    --scale N        Scale factor for sprites (default: 2)
    --verbose        Print detailed progress
"""

import argparse
import sys
from pathlib import Path

# Add backend to path
script_dir = Path(__file__).parent
project_root = script_dir.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

from foundry.font_generator import generate_tile_font, export_tile_sprites


def main():
    parser = argparse.ArgumentParser(
        description="Generate TileCrawler font from glyph definitions"
    )
    parser.add_argument(
        "--glyphs",
        type=str,
        default=str(project_root / "data" / "glyphs.json"),
        help="Path to glyphs.json",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(project_root / "frontend" / "public" / "fonts" / "TileCrawler.otf"),
        help="Output font path",
    )
    parser.add_argument(
        "--sprites",
        action="store_true",
        help="Also export individual sprite PNGs",
    )
    parser.add_argument(
        "--sprites-dir",
        type=str,
        default=str(project_root / "frontend" / "public" / "sprites"),
        help="Directory for sprite output",
    )
    parser.add_argument(
        "--scale",
        type=int,
        default=2,
        help="Scale factor for sprites (1=8x8, 2=16x16, etc.)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed progress",
    )

    args = parser.parse_args()

    # Verify input exists
    glyphs_path = Path(args.glyphs)
    if not glyphs_path.exists():
        print(f"Error: Glyphs file not found: {glyphs_path}")
        sys.exit(1)

    # Generate font
    print(f"Generating font from {glyphs_path}")
    print(f"Output: {args.output}")

    try:
        result = generate_tile_font(
            str(glyphs_path),
            args.output,
            font_name="TileCrawler",
        )
        print(f"✓ Generated font: {result}")
    except Exception as e:
        print(f"✗ Font generation failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    # Export sprites if requested
    if args.sprites:
        print(f"\nExporting sprites to {args.sprites_dir}")
        print(f"Scale: {args.scale}x ({8 * args.scale}x{8 * args.scale} pixels)")

        try:
            paths = export_tile_sprites(
                str(glyphs_path),
                args.sprites_dir,
                scale=args.scale,
            )
            print(f"✓ Exported {len(paths)} sprite images")
            if args.verbose:
                for p in paths[:10]:
                    print(f"  - {p}")
                if len(paths) > 10:
                    print(f"  ... and {len(paths) - 10} more")
        except Exception as e:
            print(f"✗ Sprite export failed: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)

    print("\nFont pipeline complete!")


if __name__ == "__main__":
    main()
