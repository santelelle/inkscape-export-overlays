# Inkscape Export Layers

Inkscape extension to export SVG layers as (JPG, PNG, PDF, LaTeX+PDF) images. The exported images can be a combination of multiple layers defined by one layer group per exported image. Layer groups may intersect. This is useful, e.g., to export multi-step overlays for slides.

## How it works
To export your Inkscape file as an image open an inkscape file with multiple layers (otherwise you can simply use the in-built export tool).

Layers are assigned frames (virtual groups of layers) that are number from `1` to `n`. For each frame `i`, an image is exported that contains all fixed layers and all layers that are active in frame `i`.

There are two options for your layers when exporting:
-  **numbered**: If a layer label starts with `[i-j]`, `[i-]` or `[-j]`, this layer will be active in frames `i` to `j`. The default values `i=1` and `j=∞` are used when `i` and `j` are not given, respectively. Multiple intervals can be separated by `,`. For example, `[2-4,6-]` will print the corresponding layer on frames 2,3,4 and on frame 6 until the last frame. Technically, the matching regular expression is `\[(\d*-\d*(,\d*-\d*)*)\]`.
- **fixed**: If a layer label starts with `[fixed]`, this layer will always be exported and combined with other layers. It is very useful for backgrounds or fixed elements. This is a more readable version of `[-]`.

The maximum number of frames is the maximum value of `i` and `j` of all numbered layers.

## Using it
To use the extension once your layers are ready:

1. Go to **Extensions > Export > Export layers**
2. Choose the path you want to save your file to (inkscape does not allow to use a file explorer, sorry)
3. Choose the format of your export (JPG, PNG, PDF, LaTeX+PDF)
