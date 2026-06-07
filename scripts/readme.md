# Scripts

All parameters are taken from config file, by default scripts_cfg.toml.

Step 1. Generate SVG from an image.

```
python scripts/image_to_svg.py -o data/x.svg data/x.png
```

Step 2. Generate GCode-like text file from SVG.

```
python scripts/svg_to_gcode.py data/x.svg data/x.gcode
```

Step 3. Stream GCode line-by-line to MC.

```

```

You can run tests with

```
python -m unittest discover -s test -p 'test_*.py'
```
