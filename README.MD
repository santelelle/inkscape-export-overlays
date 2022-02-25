# Inkscape Export Layers (modified by santelelle)

Inkscape extension to export SVG layers as (JPG, PNG, PDF, LaTeX+PDF) images. The exported images can be a combination of multiple layers defined by one layer group per exported image. Layer groups may intersect. This is useful, e.g., to export multi-step overlays for slides.

## How it works
To export your Inkscape file as an image open an inkscape file with multiple layers (otherwise you can simply use the in-built export tool).

At each layer a tag (or multiple of them) can be specified by writing it in front of the layer name.
There are different kind of tags:
- **ranges**: `[N-M]`, `[N/]`, `[/M]`, `[/]`, or `[@N/M]` The layers from the current one minus N to the current one plus M (number increases going up in the inkscape layers view) will we exported. The name of the exported file will be the name of the layer without the tags. If one of the two boundaries is not specified, we assume as limit the first or the last layer. If the modifier @ is used the coordinate is absolute.
- **single**: `[N]` or `[@N]` Export the N-th layer relative to the current one or absolute if @ (e.g. `[a3]`), 0 for exporting the current one
- **actions**: Different special actions can be specified
  - `[s]` skip: the current layer will never be exported, even if inside a specified range elsewhere
  - `[p]` persistent: the current layer will always be exported no matter the specified ranges

When using absolute coordinate, also negative numbers are allowed, `[@-1]` refers to the last layer and `[@-2]` to the second last.
Multiple tags can be concatenated (e.g. `[0/2, 4, p]`)

## Using it
To use the extension once your layers are ready:

1. Go to **Extensions > Export > Export layers**
2. Choose the path you want to save your file to (inkscape does not allow to use a file explorer, sorry)
3. Choose the format of your export (JPG, PNG, PDF, LaTeX+PDF)
