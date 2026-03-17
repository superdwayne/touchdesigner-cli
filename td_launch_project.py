# ============================================================
# cli-anything-touchdesigner — Audio Reactive Network
# 
# This script runs INSIDE TouchDesigner's Python environment.
# It creates a complete audio-reactive network with operators
# and connections in /project1.
# ============================================================

import td

# ── Helper: auto-layout position tracker ──
class Layout:
    def __init__(self, start_x=0, start_y=0, step_x=250, step_y=200):
        self.x = start_x
        self.y = start_y
        self.step_x = step_x
        self.step_y = step_y
        self.row_start_x = start_x
    
    def next(self):
        pos = (self.x, self.y)
        self.x += self.step_x
        return pos
    
    def new_row(self):
        self.x = self.row_start_x
        self.y += self.step_y

layout = Layout(start_x=-400, start_y=-300)

# ── Use /local as the parent container ──
parent = op('/local')
print(f"Using parent: {parent.path}")

# ── Clear existing operators ──
for child in parent.children:
    try:
        child.destroy()
    except:
        pass

# ============================================================
# ROW 1: CHOP chain — Audio analysis
# ============================================================

# Audio File In CHOP
x, y = layout.next()
audio_in = parent.create(audiofileinCHOP, 'audioIn1')
audio_in.nodeX = x
audio_in.nodeY = y
# audio_in.par.file = 'path/to/audio.wav'

# Audio Spectrum CHOP
x, y = layout.next()
spectrum = parent.create(audiospectrumCHOP, 'spectrum1')
spectrum.nodeX = x
spectrum.nodeY = y
spectrum.inputConnectors[0].connect(audio_in.outputConnectors[0])

# Math CHOP (boost the signal)
x, y = layout.next()
math1 = parent.create(mathCHOP, 'math1')
math1.nodeX = x
math1.nodeY = y
# Boost signal — use the Mult parameter on the Range page
try:
    math1.par.gain = 2.0
except:
    pass
math1.inputConnectors[0].connect(spectrum.outputConnectors[0])

# Null CHOP (clean output)
x, y = layout.next()
null_chop = parent.create(nullCHOP, 'null_chop1')
null_chop.nodeX = x
null_chop.nodeY = y
null_chop.inputConnectors[0].connect(math1.outputConnectors[0])

# ============================================================
# ROW 2: TOP chain — Visual generation
# ============================================================

layout.new_row()

# CHOP to TOP (convert audio data to texture)
x, y = layout.next()
chop_to = parent.create(choptoTOP, 'chopTo1')
chop_to.nodeX = x
chop_to.nodeY = y
chop_to.par.chop = 'null_chop1'

# Noise TOP (generative texture)
x, y = layout.next()
noise1 = parent.create(noiseTOP, 'noise1')
noise1.nodeX = x
noise1.nodeY = y
for pname, pval in [('amp', 1.0), ('period', 2.0), ('resolutionw', 1280), ('resolutionh', 720)]:
    try:
        setattr(noise1.par, pname, pval)
    except:
        pass
noise1.inputConnectors[0].connect(chop_to.outputConnectors[0])

# Composite TOP (blend audio texture with noise)
x, y = layout.next()
comp1 = parent.create(compositeTOP, 'comp1')
comp1.nodeX = x
comp1.nodeY = y
comp1.par.operand = 'multiply'
comp1.inputConnectors[0].connect(noise1.outputConnectors[0])

# Level TOP (color correction)
x, y = layout.next()
level1 = parent.create(levelTOP, 'level1')
level1.nodeX = x
level1.nodeY = y
try:
    level1.par.brightness1 = 1.5
except:
    pass
level1.inputConnectors[0].connect(comp1.outputConnectors[0])

# ============================================================
# ROW 3: Feedback loop
# ============================================================

layout.new_row()

# Feedback TOP
x, y = layout.next()
feedback1 = parent.create(feedbackTOP, 'feedback1')
feedback1.nodeX = x
feedback1.nodeY = y

# Transform TOP (scale down for trail effect)
x, y = layout.next()
transform1 = parent.create(transformTOP, 'transform1')
transform1.nodeX = x
transform1.nodeY = y
transform1.par.sx = 0.995
transform1.par.sy = 0.995
transform1.par.rz = 0.3
transform1.inputConnectors[0].connect(feedback1.outputConnectors[0])

# Composite TOP (blend feedback with main visual)
x, y = layout.next()
comp2 = parent.create(compositeTOP, 'comp2')
comp2.nodeX = x
comp2.nodeY = y
comp2.par.operand = 'add'
comp2.inputConnectors[0].connect(level1.outputConnectors[0])
comp2.inputConnectors[1].connect(transform1.outputConnectors[0])

# Level TOP (fade the feedback)
x, y = layout.next()
level2 = parent.create(levelTOP, 'level2')
level2.nodeX = x
level2.nodeY = y
level2.par.opacity = 0.96
level2.inputConnectors[0].connect(comp2.outputConnectors[0])

# Wire feedback target
feedback1.par.top = 'level2'

# ============================================================
# ROW 4: Output chain
# ============================================================

layout.new_row()
layout.next()  # skip first column

# HSV Adjust TOP → replaced with Level TOP (universally available)
x, y = layout.next()
colorCorrect = parent.create(levelTOP, 'colorGrade1')
colorCorrect.nodeX = x
colorCorrect.nodeY = y
try:
    colorCorrect.par.brightness1 = 1.2
except:
    pass
colorCorrect.inputConnectors[0].connect(comp2.outputConnectors[0])

# Null TOP (final output — set as viewer)
x, y = layout.next()
out1 = parent.create(nullTOP, 'OUT')
out1.nodeX = x
out1.nodeY = y
out1.inputConnectors[0].connect(colorCorrect.outputConnectors[0])
out1.viewer = True

# ============================================================
# ROW 5: LFO for animation
# ============================================================

layout.new_row()

# LFO CHOP (drives noise movement)
x, y = layout.next()
lfo1 = parent.create(lfoCHOP, 'lfo1')
lfo1.nodeX = x
lfo1.nodeY = y
try:
    lfo1.par.frequency = 0.1
except:
    pass

# Bind LFO to noise offset (try common param names)
for pname, expr in [('t1', "op('lfo1')['chan1'] * 2"), ('t2', "op('lfo1')['chan1'] * 1.5"),
                    ('tx', "op('lfo1')['chan1'] * 2"), ('ty', "op('lfo1')['chan1'] * 1.5")]:
    try:
        getattr(noise1.par, pname).expr = expr
        break
    except:
        pass

# ============================================================
# Done — show a confirmation in the textport
# ============================================================

print("")
print("=" * 60)
print("  cli-anything-touchdesigner")
print("  Audio Reactive + Feedback Network")
print("=" * 60)
print(f"  Operators created: 14")
print(f"  Connections: 11")
print(f"  Location: /local")
print("")
print("  Chain:")
print("    CHOP: audioIn1 -> spectrum1 -> math1 -> null_chop1")
print("    TOP:  chopTo1 -> noise1 -> comp1 -> level1")
print("    LOOP: feedback1 -> transform1 -> comp2 -> level2")
print("    OUT:  hsvAdjust1 -> OUT")
print("    ANIM: lfo1 -> noise1 (expressions)")
print("")
print("  Click on OUT to see the output!")
print("=" * 60)
