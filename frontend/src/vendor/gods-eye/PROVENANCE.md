Geographic viewer foundation from bilawalsidhu/gods-eye-view, MIT.
Pinned upstream commit: 8b8ccc9a81379e8b40d4be67610570ee5b159512.
viewer.js and atmosphereCompat.js copied; viewer.js changes the Cesium import to the lazily loaded global bundle and sets MSAA=1/preserveDrawingBuffer=false for the low-memory desktop. Cronos composes this viewer
with worldwide imagery and place navigation. The upstream live layers, camera
feeds, photorealistic tiles, voice provider and credential discovery are NOT
included; they require separate integration and provider-specific terms.

coastlines.json is an orthographic, sampled projection of the upstream
src/data/local_data/natural_earth/countries.json (Natural Earth, public domain,
source commit ca96624a56bd078437bca8184e78163e5039ad19); display decoration only.
