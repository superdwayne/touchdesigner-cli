"""
Disintegration / Deconstruction Effect for TouchDesigner
=========================================================

Paste this entire script into a Text DAT in TouchDesigner, then run it.
It creates a complete point-cloud disintegration effect with:

  - A sphere (or swap for any SOP) scattered into ~5000 points
  - GLSL MAT with vertex displacement that explodes points outward
  - Staggered per-point onset so the dissolution ripples across the surface
  - Ember-orange glow on dying particles with soft circular point sprites
  - LFO-driven animation (adjustable speed via disint_lfo frequency)

Controls (after running):
  - disint_lfo.par.frequency  → speed of disintegration cycle
  - disint_glslmat uniforms   → uProgress, uExplosionForce, uNoiseScale, uNoiseSpeed
  - scatter1.par.force        → point density (higher = more points)

Usage:
  1. Open TouchDesigner
  2. Create a Text DAT, paste this script
  3. Right-click → Run Script
  4. View disint_render or disint_out for the result
"""

# ──────────────────────────────────────────────────────────
# 1. Scene components
# ──────────────────────────────────────────────────────────

# Geometry COMP
geo = op('/project1').create('geometryCOMP', 'disint_geo')
geo.nodeX = 0
geo.nodeY = 0

# Camera
cam = op('/project1').create('cameraCOMP', 'disint_cam')
cam.nodeX = 250
cam.nodeY = 0
cam.par.tx = 0
cam.par.ty = 0.5
cam.par.tz = 4

# Light
light = op('/project1').create('lightCOMP', 'disint_light')
light.nodeX = 500
light.nodeY = 0
light.par.lighttype = 'point'
light.par.tx = 3
light.par.ty = 4
light.par.tz = 3
try:
    light.par.dimmer = 1.2
except:
    pass

# ──────────────────────────────────────────────────────────
# 2. SOP chain inside geometry: Sphere → Scatter → Noise → Sort → Null
# ──────────────────────────────────────────────────────────

sphere = geo.create('sphereSOP', 'sphere1')
sphere.nodeX = 0
sphere.nodeY = 0
sphere.par.rows = 40
sphere.par.cols = 40

scatter = geo.create('scatterSOP', 'scatter1')
scatter.nodeX = 250
scatter.nodeY = 0
try:
    scatter.par.force = 5000
except:
    pass
scatter.inputConnectors[0].connect(sphere.outputConnectors[0])

noise_sop = geo.create('noiseSOP', 'noise_displace')
noise_sop.nodeX = 500
noise_sop.nodeY = 0
noise_sop.par.amp = 0.0  # starts at zero — GLSL handles displacement
try:
    noise_sop.par.type = 'sparse'
    noise_sop.par.period = 1.5
    noise_sop.par.rough = 0.6
except:
    pass
noise_sop.inputConnectors[0].connect(scatter.outputConnectors[0])

sort_sop = geo.create('sortSOP', 'sort1')
sort_sop.nodeX = 750
sort_sop.nodeY = 0
try:
    sort_sop.par.ptsort = 'random'
except:
    pass
sort_sop.inputConnectors[0].connect(noise_sop.outputConnectors[0])

null_sop = geo.create('nullSOP', 'null_geo')
null_sop.nodeX = 1000
null_sop.nodeY = 0
null_sop.inputConnectors[0].connect(sort_sop.outputConnectors[0])
null_sop.render = True
null_sop.display = True

# ──────────────────────────────────────────────────────────
# 3. Animation driver: LFO → Math → Null CHOP
# ──────────────────────────────────────────────────────────

lfo = op('/project1').create('lfoCHOP', 'disint_lfo')
lfo.nodeX = 0
lfo.nodeY = -200
try:
    lfo.par.type = 'ramp'
except:
    pass
lfo.par.frequency = 0.1
lfo.par.amp = 1.0

math_chop = op('/project1').create('mathCHOP', 'disint_math')
math_chop.nodeX = 250
math_chop.nodeY = -200
math_chop.inputConnectors[0].connect(lfo.outputConnectors[0])

null_chop = op('/project1').create('nullCHOP', 'disint_anim')
null_chop.nodeX = 500
null_chop.nodeY = -200
null_chop.inputConnectors[0].connect(math_chop.outputConnectors[0])

# ──────────────────────────────────────────────────────────
# 4. GLSL Material — vertex + pixel shaders
# ──────────────────────────────────────────────────────────

# Vertex shader DAT
vert_dat = op('/project1').create('textDAT', 'disint_vert_code')
vert_dat.nodeX = 0
vert_dat.nodeY = -400
vert_dat.text = '''// Disintegration vertex shader
// Uniforms: uProgress (0=intact, 1=fully disintegrated)
//           uNoiseScale, uNoiseSpeed, uExplosionForce

uniform float uProgress;
uniform float uNoiseScale;
uniform float uNoiseSpeed;
uniform float uExplosionForce;

out Vertex {
    vec4 color;
    float life;
} oVert;

// Simple 3D hash noise
vec3 hash3(vec3 p) {
    p = vec3(dot(p, vec3(127.1, 311.7, 74.7)),
            dot(p, vec3(269.5, 183.3, 246.1)),
            dot(p, vec3(113.5, 271.9, 124.6)));
    return -1.0 + 2.0 * fract(sin(p) * 43758.5453123);
}

void main() {
    // Original position from TD deform
    vec4 worldPos = TDDeform(P);

    // Per-point random direction based on rest position
    vec3 seed = P.xyz * uNoiseScale;
    vec3 randomDir = normalize(hash3(seed));

    // Staggered onset: each point starts disintegrating at a
    // different time based on its position + noise
    float onset = fract(seed.x * 0.37 + seed.y * 0.71 + seed.z * 0.13);
    float localProgress = clamp((uProgress - onset * 0.6) / 0.4, 0.0, 1.0);

    // Ease-in for explosion force
    float force = localProgress * localProgress * uExplosionForce;

    // Displace outward along normal + random direction
    vec3 displacement = (N.xyz * 0.3 + randomDir * 0.7) * force;

    // Add gravity pull downward as particles fly out
    displacement.y -= localProgress * localProgress * uExplosionForce * 0.4;

    // Add turbulence
    float time = uTDGeneral.currentTime.x * uNoiseSpeed;
    vec3 turb = hash3(seed + time) * localProgress * 0.3;
    displacement += turb;

    worldPos.xyz += displacement;

    // Pass life (1=alive, 0=gone) to fragment shader
    oVert.life = 1.0 - localProgress;
    oVert.color = Cd;

    // Scale point size: shrink as they die
    gl_PointSize = mix(1.0, 6.0, oVert.life);

    gl_Position = TDWorldToProj(worldPos);
}
'''

# Pixel shader DAT
pixel_dat = op('/project1').create('textDAT', 'disint_pixel_code')
pixel_dat.nodeX = 250
pixel_dat.nodeY = -400
pixel_dat.text = '''// Disintegration pixel shader
// Renders points as soft circles that fade with life

in Vertex {
    vec4 color;
    float life;
} iVert;

out vec4 fragColor;

void main() {
    // Soft circular point sprite
    vec2 coord = gl_PointCoord * 2.0 - 1.0;
    float dist = dot(coord, coord);
    if (dist > 1.0) discard;

    float softEdge = 1.0 - smoothstep(0.5, 1.0, dist);

    // Color: warm tones as particles disintegrate
    vec3 aliveColor = iVert.color.rgb;
    vec3 dyingColor = vec3(1.0, 0.4, 0.1); // ember orange
    vec3 col = mix(dyingColor, aliveColor, iVert.life);

    // Add glow to dying particles
    float glow = (1.0 - iVert.life) * 0.5;
    col += vec3(glow, glow * 0.3, 0.0);

    // Alpha: fade out with life, combine with soft edge
    float alpha = iVert.life * softEdge;

    fragColor = TDOutputSwizzle(vec4(col, alpha));
}
'''

# GLSL Material
glsl_mat = op('/project1').create('glslMAT', 'disint_glslmat')
glsl_mat.nodeX = 500
glsl_mat.nodeY = -400

# Wire shader DATs to the material
try:
    glsl_mat.par.vertexdat = 'disint_vert_code'
    glsl_mat.par.pixeldat = 'disint_pixel_code'
except:
    pass

# Set up uniforms on the GLSL MAT
# These map to the Vectors/Uniforms page — set via custom parameters or
# bind expressions. Default values provided via the shader's uniform declarations.
try:
    # Create uniform names on the Uniforms page
    glsl_mat.par.uniformname0 = 'uProgress'
    glsl_mat.par.value0x = 0.0
    glsl_mat.par.uniformname1 = 'uNoiseScale'
    glsl_mat.par.value1x = 3.0
    glsl_mat.par.uniformname2 = 'uNoiseSpeed'
    glsl_mat.par.value2x = 0.5
    glsl_mat.par.uniformname3 = 'uExplosionForce'
    glsl_mat.par.value3x = 2.5
except:
    pass

# Bind uProgress to the LFO animation
try:
    glsl_mat.par.value0x.expr = "op('disint_anim')['chan1']"
except:
    pass

# Assign material to geometry
try:
    geo.par.material = 'disint_glslmat'
except:
    pass

# ──────────────────────────────────────────────────────────
# 5. Render TOP chain
# ──────────────────────────────────────────────────────────

render_top = op('/project1').create('renderTOP', 'disint_render')
render_top.nodeX = 0
render_top.nodeY = -600
render_top.par.resolutionw = 1920
render_top.par.resolutionh = 1080

level_top = op('/project1').create('levelTOP', 'disint_level')
level_top.nodeX = 250
level_top.nodeY = -600
level_top.par.brightness1 = 1.1
level_top.par.gamma1 = 1.1
level_top.inputConnectors[0].connect(render_top.outputConnectors[0])

out_top = op('/project1').create('nullTOP', 'disint_out')
out_top.nodeX = 500
out_top.nodeY = -600
out_top.inputConnectors[0].connect(level_top.outputConnectors[0])

print("=== Disintegration effect created! ===")
print("View 'disint_render' or 'disint_out' for the result.")
print("Adjust 'disint_lfo' frequency to control animation speed.")
print("Tweak GLSL MAT uniforms for explosion force, noise, etc.")
