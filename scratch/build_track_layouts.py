"""Compatibility entry point for the geographic circuit authoring pipeline.

The former schematic fitting pipeline has been replaced. Source geometry is
never stretched or relaxed to make room for roads or grid boxes.
"""
from build_geographic_layouts import build

if __name__ == "__main__":
    build()
    from build_future_layouts import build as build_returning
    build_returning()
