# The picture set

Six pictures, one sun. Every scene is a vector file (`<name>/scene.svg`) rendered by
`scripts/render-art.mjs` into `public/art/<name>-{640,1280,1920}.{avif,webp}`, so each
picture can be made again from its scene. The light comes from the upper right in every
scene; shadows, rays and hatches lean 18.4° from vertical, the angle of the two cuts in
`public/mark.svg`. Palette: paper `#FAF7F0`, plaster `#F1EBDD`, ink `#1B1814`, sun
`#F2C14E`, amber `#C8842B`, ember `#8F4A1E`, dusk `#17130F`. A little film grain
(`feTurbulence`) on every picture.

These are restrained vector renders, not photographs, and they hold the layout. The
brief's first route (generated stills) was not available in this session, and a path
tracer was judged too heavy for the time. If you commission stills, the briefs are below.

| Name | Section | Subject | Composition and camera | Aspect |
| --- | --- | --- | --- | --- |
| two-cards | 02 Hero | Two identical upright cards on a pale plaster plane. The left casts the shadow you expect. The right casts a shadow that does not match its shape. | Eye level, slightly above; cards a third from each edge; sun off-frame upper right, low; shadows long toward the lower left at 18.4° | 5:4 |
| aperture | 10 Data | A closed matte box with one narrow slit; a single blade of light leaves it. | Three-quarter view, last light: deep umber plate, thin gold rim on the top edge, one blade toward the lower left | 4:3 |
| analemma | 11 Research | Small brass discs pinned to a plaster wall in the sun's figure of eight, each with its own shadow. | Frontal, wall fills the frame; discs the size of coins; day light | 4:3 |
| specimens | 12 Lab | Eleven small forms in a row on a plane. Most cast true shadows; one casts a wrong shadow, one casts two, one casts none. | Low eye level, row across the frame; golden hour | 9:4 |
| seal | 09 Certified | The badge blind-embossed in heavy paper under raking light. | Frontal, paper fills the frame, light from the upper right | 1:1 |
| last-light | 16 Footer | The horizon the name stands on. | Wide, last light on a dusk ground; a thin warm band at the horizon, no blue | 16:5 |

File names for commissioned stills: the same as above, delivered as 1920 px wide
masters; `render-art.mjs` can take a raster master in place of `scene.svg` once one
exists.
