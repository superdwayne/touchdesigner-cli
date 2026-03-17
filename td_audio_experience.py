# ============================================================
# cli-anything-touchdesigner — AUDIO EXPERIENCE
#
# A full audio-reactive visual system built in TouchDesigner.
# Uses your live microphone/audio input to drive visuals.
#
# Paste in TD Textport:
#   exec(open('/Users/dwayne/TD-cli/td_audio_experience.py').read())
# ============================================================

parent = op('/local')

# ── Clear existing operators ──
for child in parent.children:
    try:
        child.destroy()
    except:
        pass

# ── Layout helper ──
_cx, _cy, _sx, _sy = -600, -400, 250, 180
def pos(col, row):
    return (_cx + col * _sx, _cy + row * _sy)

def safe_par(operator, **kwargs):
    for k, v in kwargs.items():
        try:
            setattr(operator.par, k, v)
        except:
            pass

# ============================================================
# ROW 0: AUDIO INPUT — live mic/system audio
# ============================================================

audioIn = parent.create(audiodevinCHOP, 'audioIn')
audioIn.nodeX, audioIn.nodeY = pos(0, 0)

# Spectrum analysis
spectrum = parent.create(audiospectrumCHOP, 'spectrum')
spectrum.nodeX, spectrum.nodeY = pos(1, 0)
spectrum.inputConnectors[0].connect(audioIn.outputConnectors[0])

# ============================================================
# ROW 1: FREQUENCY BAND SPLITTING — bass / mid / high
# ============================================================

# Select CHOP — Bass (channels 0-5)
selBass = parent.create(selectCHOP, 'selBass')
selBass.nodeX, selBass.nodeY = pos(0, 1)
safe_par(selBass, channames='[0-5]')
selBass.inputConnectors[0].connect(spectrum.outputConnectors[0])

# Select CHOP — Mid (channels 6-20)
selMid = parent.create(selectCHOP, 'selMid')
selMid.nodeX, selMid.nodeY = pos(1, 1)
safe_par(selMid, channames='[6-20]')
selMid.inputConnectors[0].connect(spectrum.outputConnectors[0])

# Select CHOP — High (channels 21-50)
selHigh = parent.create(selectCHOP, 'selHigh')
selHigh.nodeX, selHigh.nodeY = pos(2, 1)
safe_par(selHigh, channames='[21-50]')
selHigh.inputConnectors[0].connect(spectrum.outputConnectors[0])

# ============================================================
# ROW 2: SMOOTH with Lag CHOPs
# ============================================================

lagBass = parent.create(lagCHOP, 'lagBass')
lagBass.nodeX, lagBass.nodeY = pos(0, 2)
safe_par(lagBass, lag1=0.2, lag2=0.2)
lagBass.inputConnectors[0].connect(selBass.outputConnectors[0])

lagMid = parent.create(lagCHOP, 'lagMid')
lagMid.nodeX, lagMid.nodeY = pos(1, 2)
safe_par(lagMid, lag1=0.1, lag2=0.1)
lagMid.inputConnectors[0].connect(selMid.outputConnectors[0])

lagHigh = parent.create(lagCHOP, 'lagHigh')
lagHigh.nodeX, lagHigh.nodeY = pos(2, 2)
safe_par(lagHigh, lag1=0.05, lag2=0.05)
lagHigh.inputConnectors[0].connect(selHigh.outputConnectors[0])

# Math CHOPs to combine each band into a single value
mathBass = parent.create(mathCHOP, 'mathBass')
mathBass.nodeX, mathBass.nodeY = pos(0, 3)
safe_par(mathBass, chopop='average')
mathBass.inputConnectors[0].connect(lagBass.outputConnectors[0])

mathMid = parent.create(mathCHOP, 'mathMid')
mathMid.nodeX, mathMid.nodeY = pos(1, 3)
safe_par(mathMid, chopop='average')
mathMid.inputConnectors[0].connect(lagMid.outputConnectors[0])

mathHigh = parent.create(mathCHOP, 'mathHigh')
mathHigh.nodeX, mathHigh.nodeY = pos(2, 3)
safe_par(mathHigh, chopop='average')
mathHigh.inputConnectors[0].connect(lagHigh.outputConnectors[0])

# Null outputs for each band
nullBass = parent.create(nullCHOP, 'nullBass')
nullBass.nodeX, nullBass.nodeY = pos(0, 4)
nullBass.inputConnectors[0].connect(mathBass.outputConnectors[0])

nullMid = parent.create(nullCHOP, 'nullMid')
nullMid.nodeX, nullMid.nodeY = pos(1, 4)
nullMid.inputConnectors[0].connect(mathMid.outputConnectors[0])

nullHigh = parent.create(nullCHOP, 'nullHigh')
nullHigh.nodeX, nullHigh.nodeY = pos(2, 4)
nullHigh.inputConnectors[0].connect(mathHigh.outputConnectors[0])

# ============================================================
# ROW 5-7: VISUALS — Bass drives circles, Mid drives noise, High drives lines
# ============================================================

# --- BASS VISUAL: Pulsing circle ---
circBass = parent.create(circleTOP, 'circBass')
circBass.nodeX, circBass.nodeY = pos(0, 5)
safe_par(circBass, resolutionw=1280, resolutionh=720)
try:
    circBass.par.radius.expr = "op('nullBass')['chan1'] * 0.4 + 0.05"
except:
    pass

# --- MID VISUAL: Animated noise field ---
noiseMid = parent.create(noiseTOP, 'noiseMid')
noiseMid.nodeX, noiseMid.nodeY = pos(1, 5)
safe_par(noiseMid, resolutionw=1280, resolutionh=720)
try:
    noiseMid.par.amp.expr = "op('nullMid')['chan1'] * 3 + 0.2"
except:
    pass

# --- HIGH VISUAL: Ramp driven by highs ---
rampHigh = parent.create(rampTOP, 'rampHigh')
rampHigh.nodeX, rampHigh.nodeY = pos(2, 5)
safe_par(rampHigh, resolutionw=1280, resolutionh=720)
try:
    rampHigh.par.phase.expr = "absTime.seconds * 0.3 + op('nullHigh')['chan1'] * 2"
except:
    pass

# ============================================================
# ROW 6: COLOR each band — Level TOPs for tinting
# ============================================================

# Bass = deep red/magenta
lvlBass = parent.create(levelTOP, 'lvlBass')
lvlBass.nodeX, lvlBass.nodeY = pos(0, 6)
safe_par(lvlBass, opacity=1.0)
lvlBass.inputConnectors[0].connect(circBass.outputConnectors[0])

# Mid = green/cyan
lvlMid = parent.create(levelTOP, 'lvlMid')
lvlMid.nodeX, lvlMid.nodeY = pos(1, 6)
safe_par(lvlMid, opacity=1.0)
lvlMid.inputConnectors[0].connect(noiseMid.outputConnectors[0])

# High = blue/white
lvlHigh = parent.create(levelTOP, 'lvlHigh')
lvlHigh.nodeX, lvlHigh.nodeY = pos(2, 6)
safe_par(lvlHigh, opacity=1.0)
lvlHigh.inputConnectors[0].connect(rampHigh.outputConnectors[0])

# ============================================================
# ROW 7: COMPOSITE — Blend all 3 bands together
# ============================================================

# Add bass + mid
addBM = parent.create(compositeTOP, 'addBassMid')
addBM.nodeX, addBM.nodeY = pos(0, 7)
safe_par(addBM, operand='add')
addBM.inputConnectors[0].connect(lvlBass.outputConnectors[0])
addBM.inputConnectors[1].connect(lvlMid.outputConnectors[0])

# Add (bass+mid) + high
addAll = parent.create(compositeTOP, 'addAll')
addAll.nodeX, addAll.nodeY = pos(1, 7)
safe_par(addAll, operand='add')
addAll.inputConnectors[0].connect(addBM.outputConnectors[0])
addAll.inputConnectors[1].connect(lvlHigh.outputConnectors[0])

# ============================================================
# ROW 8: FEEDBACK LOOP — Trails
# ============================================================

feedback = parent.create(feedbackTOP, 'feedback')
feedback.nodeX, feedback.nodeY = pos(0, 8)

xform = parent.create(transformTOP, 'trailXform')
xform.nodeX, xform.nodeY = pos(1, 8)
safe_par(xform, sx=0.997, sy=0.997)
try:
    xform.par.rz.expr = "op('nullBass')['chan1'] * 0.5"
except:
    pass
xform.inputConnectors[0].connect(feedback.outputConnectors[0])

compTrail = parent.create(compositeTOP, 'compTrail')
compTrail.nodeX, compTrail.nodeY = pos(2, 8)
safe_par(compTrail, operand='add')
compTrail.inputConnectors[0].connect(addAll.outputConnectors[0])
compTrail.inputConnectors[1].connect(xform.outputConnectors[0])

levelFade = parent.create(levelTOP, 'trailFade')
levelFade.nodeX, levelFade.nodeY = pos(3, 8)
safe_par(levelFade, opacity=0.93)
levelFade.inputConnectors[0].connect(compTrail.outputConnectors[0])

# Wire feedback
feedback.par.top = 'trailFade'

# ============================================================
# ROW 9: FINAL OUTPUT
# ============================================================

outLevel = parent.create(levelTOP, 'finalLevel')
outLevel.nodeX, outLevel.nodeY = pos(1, 9)
safe_par(outLevel, brightness1=1.1)
outLevel.inputConnectors[0].connect(compTrail.outputConnectors[0])

OUT = parent.create(nullTOP, 'OUT')
OUT.nodeX, OUT.nodeY = pos(2, 9)
OUT.inputConnectors[0].connect(outLevel.outputConnectors[0])
OUT.viewer = True

# ============================================================
# AUDIO SPECTRUM VISUALIZER — CHOP to TOP for waveform display
# ============================================================

chopToViz = parent.create(choptoTOP, 'spectrumViz')
chopToViz.nodeX, chopToViz.nodeY = pos(3, 0)
safe_par(chopToViz, chop='spectrum')

# ============================================================
# Done
# ============================================================

print("")
print("=" * 60)
print("  AUDIO EXPERIENCE")
print("  cli-anything-touchdesigner")
print("=" * 60)
print(f"  Operators: {len(parent.children)}")
print(f"  Location:  /local")
print("")
print("  Signal Flow:")
print("    MIC IN -> Spectrum -> Bass/Mid/High split")
print("    Bass  -> Circle pulse  (low freq throb)")
print("    Mid   -> Noise field   (mid freq texture)")
print("    High  -> Ramp phase    (high freq shimmer)")
print("    All 3 -> Composite -> Feedback trails -> OUT")
print("")
print("  Make some noise! Clap, play music, speak.")
print("  Click OUT node to see the output.")
print("=" * 60)
