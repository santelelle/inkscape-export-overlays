# Inkscape Export Layers (modified by santelelle)
With this plugin we can export one (or multiple) images (JPG, PNG or PDF, LaTeX+PDF) from a inkscape svg file. 
Each exported file is a combination of different layers, defined by the tag prefixed to the layer name.

## How it works
**TD;DR**: writing a tag (or composition of tags) in front of a layer name defines a set of layers that can be quickly be exported as a single file. \
Use the `example.svg` file as a quick example.

Use the following tags at the beginning of the layer names to select what to export (Example layer name: `[3/4]layername`). 
The name of the exported image will be the one of the tagged layer (with additional constant suffix/prefix that can be specified in the interface)

**Range tags**:
- `[@N/@M]` select all the layers from the N-th to the M-th. The `@` define an absolute coordinate.
  When using absolute indexing with @ also negative number are allowed, `[@-1]` is the last layer, `[@-2]` is the second lasts and so on. \
  Example: `[@3, @-2]` exports all the layers starting from the absolute 3rd layer (starting from the top) and the second to last layer
- `[N/M]` select all the layers from the N-th to M-th relative to the current layer. \
  Example: `[-2, 3]` exports all the layers starting from the one 2 positions above to the one 3 positions below
- `[/M]`, `[N/]`, `[/]`, `[/@M]`, `[@N/]` same as the two cases above, if one extreme is not specified all the layer in that direction are selected. \
  Example: `[/N]` exports all the layer from the first one to the N-th relative to the current layer \
  Example: `[/@N]` exports all the layer from the first one to the absolute N-th layer \ 
- `[N]` export only the relative N-th layer. \
  Example: `[0]` exports only the current layer
  Example: `[-1]` exports only the layer above the current

**Action tags**:
- `[s]` skip: always skip exporting this layer, even if it's included in a range
- `[p]` persistent: always export this layer, no matter if it's included in ranges

**Concatenation**:
- Multiple tags can be selected separating them with a comma (e.g. `[3/4,5/7,s]`). \
  Example: `[0, @0, @-1]` exports the current, the first and the last layer. \
  Example: `[0, @0/3]` exports the current and all the layers between the first and the 3-rd one after the current layer. \
  Example: `[0, @0/-3]` exports the current and all the layers between the first and the 3-rd one before the current layer.

## Using it
To use the extension once your layers are ready:

1. Go to **Extensions > Export > Export layers**
2. Choose the path you want to save your file to
3. Choose the format of your export (JPG, PNG, PDF, LaTeX+PDF)
