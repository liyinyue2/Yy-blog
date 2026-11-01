# Kindred — Delivery Checklist

- [x] **Self-contained hero document.** Delivered one `index.html` containing all Kindred markup, CSS, inline SVG artwork, and vanilla JavaScript. The only external resources are Inter from Google Fonts and the supplied Higgsfield source sheet; it retains a full-viewport `section.hero`, a 660px minimum height, clipped overflow, and a canvas rendered every frame rather than a video or GIF.

- [x] **Editorial interface and responsive content.** Recreated the warm off-white monochrome hierarchy using the supplied tokens: centered Kindred navigation and brand mark, five desktop links, Sign In pill, two-line headline, exact supporting copy, rainbow-underlit Join the circle CTA, and the six named fictional partner lockups. At ≤760px links hide, brand and Sign In are spaced apart, copy moves to 20%, and logos wrap into two rows.

- [x] **Live five-level LED halftone hands.** Loaded the prescribed sheet with `crossOrigin="anonymous"`, sliced the four prescribed crop rectangles into 420px tiles, sampled pose A and pose B through two tiny field canvases, and turned source luminance into quantized black dot sizes on horizontal scanline rows. DPR-capped canvas and grid measurements recompute after resize.

- [x] **Specified continuous and glitch motion.** Delivered 20-second counter-phase hand reach, breath, roll and shimmer; the given left/right time windows drive seeded dot-by-dot pose dissolves with flickering transition fronts and occasional row displacement; the center fade and quiet zone protect copy; `window.__render` is exposed; and portrait hands are lower, wider, and beneath the CTA.

- [x] **Static serving and validation.** Provided `/manus-routes.json`, ran the page on the project port, verified its route manifest, inspected desktop and mobile renders, and completed an independent implementation audit.
