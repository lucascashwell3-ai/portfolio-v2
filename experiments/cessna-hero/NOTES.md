# Cessna hero prototype — plain-English notes

**What it is:** open `index.html` and you're sitting in a Cessna at golden hour. The engine
spools up, you take off, and you cruise over a sunset coastline with 5 islands — one per
project (DATproof, Modelproof, Skillproof, Warden, Prompt Emporium). Pick a project from the
pill menu (or click its island) and the plane banks over, circles it, and a card slides in
with a "Resume flight" button. Drag to look around. There's a soft engine hum (mute button),
a "Skip intro" button, and screenshots of it in `shots/`.

**What works:** the full loop — intro → takeoff → cruise → fly-to-island → card → resume —
verified in a headless browser with zero console errors. Reduced-motion users get a static
aerial view with clickable islands; browsers without WebGL get a friendly text fallback.
The whole world renders in very few draw calls, so it should hold 60fps on a normal laptop.

**What's rough:** it's programmer-built scenery — charming lofi, but the islands and cockpit
would benefit from a real low-poly artist pass (or purchased models). No mobile-touch polish
yet, no loading screen, and the engine sound is a simple synth.

**What production needs:** move it behind a "Take the flight" button on the portfolio (not the
default landing — it's heavy and quirky), swap island links to real project URLs, an artist
pass on models/textures, real device testing (Safari, phones), and probably a prerendered
video fallback for weak hardware.
