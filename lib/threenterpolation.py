# barycentric interpolation tool
# just 3 glyphs

# now, how to get your glyphs in there?
# drag the pointer to a corner and do control-click to get the menu
# select any glyph from any open UFO

import AppKit
import math
import vanilla
from mojo.canvas import Canvas, CanvasGroup
import mojo.drawingTools as ctx
from fontMath.mathGlyph import MathGlyph
from AppKit import NSPasteboardTypeString, NSPasteboard
from fontTools.ufoLib.glifLib import writeGlyphToString
from mojo.UI import SearchList

# https://codeplea.com/triangular-interpolation
def ip(v1, v2, v3, p):
    d = (v2[1]-v3[1])*(v1[0]-v3[0])+(v3[0]-v2[0])*(v1[1]-v3[1])
    w1 = ((v2[1]-v3[1])*(p[0]-v3[0])+(v3[0]-v2[0])*(p[1]-v3[1]))/d
    w2 = ((v3[1]-v1[1])*(p[0]-v3[0])+(v1[0]-v3[0])*(p[1]-v3[1]))/d
    w3 = 1-w1-w2
    return w1, w2, w3

class Threenterpolation(object):
    def __init__(self):
        self.dotSize = 10
        self.glyphs = None
        self.result = None
        self.pointer = None
        self.snap = 5 # snap distance
        self.snapped = None    # index of which point we're snapping on
        self.orientation = 0.3
        self.glyphScale = 0.18
        self.glyphs = [None, None, None]
        self.mGlyphs = None
        self.startDrag = None
        self.p1 = self.p2 = self.p3 = None
        self._factors = None
        s = 400
        self.w = vanilla.Window((s,s), "3nterpolation",minSize=(250,250))
        self.w.c = CanvasGroup((0,0,0,0), delegate=self)
        self.w.bind('resize', self.resize)
        self.w.open()
        self.resize()
        self.w.c.update()
    
    def resize(self, sender=None):
        w = self.w.c.width()
        h = self.w.c.height()
        self.glyphScale = h / 3500
        self.pointer = None
        
    def setGlyphs(self, g1=None, g2=None, g3=None):
        if g1 is None:
            g1 = self.glyphs[0]
        if g2 is None:
            g2 = self.glyphs[1]
        if g3 is None:
            g3 = self.glyphs[2]
        self.glyphs = [g1, g2, g3]
        self.mGlyphs = [None, None, None]
        if g1 is not None:
            self.mGlyphs[0] = g1.toMathGlyph()
        if g2 is not None:
            self.mGlyphs[1] = g2.toMathGlyph()
        if g3 is not None:
            self.mGlyphs[2] = g3.toMathGlyph()
        self.w.c.update()
        
    def acceptsMouseMoved(self):
        return True
    
    def menu(self, item=None):
        m = AppKit.NSMenu.alloc().init()
        items = []
        if self.snapped is not None:
            items.append(dict(title="Set Master", callback=self.menu_setMaster))
        if self.result is not None:
            items.append(dict(title="Copy the result as glyph…", callback=self.menu_copyResult))
            #items.append(dict(title="Make a new font like this…", callback=self.menu_makeFont))
        vanilla.vanillaList.VanillaMenuBuilder(self, items, m)
        return m
    
    def _getMasters(self):
        keys = []
        fonts = []
        masters = []
        for f in AllFonts():
            masters.append(f)
            for g in f.keys():
                fonts.append((f"{g} ({f.info.familyName} {f.info.styleName})", f, g))
        fonts.sort(key=lambda x: x[0])
        keys = [a for a, b, c in fonts]
        return keys, fonts, masters
        
    def menu_setMaster(self, sender):
        # set the master for this glyph
        keys, fonts, _ = self._getMasters()
        # keys = []
        # fonts = []
        # for f in AllFonts():
        #     for g in f.keys():
        #         fonts.append((f"{g} ({f.info.familyName} {f.info.styleName})", f, g))
        # fonts.sort(key=lambda x: x[0])
        # keys = [a for a, b, c in fonts]
        selection = SearchList(keys)
        index = keys.index(selection)
        _, f, name = fonts[index]
        glyph = f[name]
        self.glyphs[self.snapped] = glyph
        self.setGlyphs()
        
    def menu_copyResult(self, sender):
        # copy the result to the clipboard
        if self.result is None:
            print("nothing to copy")
            return
        out = RGlyph()
        out.fromMathGlyph(self.result)
        text = writeGlyphToString("threenterpolation", out, out.drawPoints)
        pb = AppKit.NSPasteboard.generalPasteboard()
        pb.clearContents()
        pb.declareTypes_owner_([
            NSPasteboardTypeString,
        ], None)
        pb.setString_forType_(text,  AppKit.NSPasteboardTypeString)
        
    def mouseDragged(self, event):
        p = event.locationInWindow()
        self.pointer = p.x, p.y
        w = self.w.c.width()
        h = self.w.c.height()
        center = w*.5, h*.5
        modFlags = event.modifierFlags()
        isOption = isShift = isControl = False
        if modFlags & AppKit.NSAlternateKeyMask:
            isOption = True
        if modFlags & AppKit.NSShiftKeyMask:
            isShift = True
        if modFlags & AppKit.NSControlKeyMask:
            isControl = True
        if isShift:
            # naff
            da = 0
            dx = self.startDrag[0] - self.pointer[0]
            if dx < 0:
                da = -0.0001*abs(dx)
            else:
                da = 0.0001*abs(dx)
            self.orientation += da
            self.w.c.update()
        else:
            self.pointer = p.x, p.y
            self.w.c.update()
        self.lastDrag = self.pointer

    def mouseDown(self, event):
        p = event.locationInWindow()
        self.pointer = p.x, p.y
        if self.startDrag is None:
            self.startDrag = self.pointer
        self.mouseDragged(event)

    def becomeFirstResponder(self):
        self.setGlyphs()
        
    def mouseUp(self, event):
        self.startDrag = None

    def closeToPoint(self, pt1, pt2):
        if pt1 is None or pt2 is None:
            return None
        d = math.hypot(pt1[0]-pt2[0], pt1[1]-pt2[1])
        return d < self.snap
        
    def draw(self):
        w = self.w.c.width()
        h = self.w.c.height()
        m = 130
        center = w*.5, h*.5
        d = self.dotSize
        r = min(.5*(h-2*m), .5*(w-2*m))
        if self.pointer is None:
            self.pointer = center

        a1 = self.orientation*math.pi
        a2 = a1+2/3*math.pi
        a3 = a1-2/3*math.pi
        self.p1 = p1 = center[0]+(r*math.sin(a1)), center[1]+(r*math.cos(a1))
        self.p2 = p2 = center[0]+(r*math.sin(a2)), center[1]+(r*math.cos(a2))
        self.p3 = p3 = center[0]+(r*math.sin(a3)), center[1]+(r*math.cos(a3))
        
        self.snapped = None
        if self.closeToPoint(self.p1, self.pointer):
            self.pointer = self.p1
            self.snapped = 0
        if self.closeToPoint(self.p2, self.pointer):
            self.pointer = self.p2
            self.snapped = 1
        if self.closeToPoint(self.p3, self.pointer):
            self.pointer = self.p3
            self.snapped = 2
        
        p1d = p1[0]-.5*d, p1[1]-.5*d, d, d
        p2d = p2[0]-.5*d, p2[1]-.5*d, d, d
        p3d = p3[0]-.5*d, p3[1]-.5*d, d, d

        ctx.save()
        ctx.stroke(.8, .8, .7)
        ctx.strokeWidth(.4)
        ctx.strokeWidth(.8)
        ctx.line(p1, p2)
        ctx.line(p2, p3)
        ctx.line(p3, p1)

        if self.pointer is not None:
            ctx.line(p1, self.pointer)
            ctx.line(p2, self.pointer)
            ctx.line(p3, self.pointer)
        
        ctx.stroke(None)
        ctx.fill(0)
        ctx.oval(*p1d)
        ctx.oval(*p2d)
        ctx.oval(*p3d)
        
        g1, g2, g3 = self.glyphs
        if g1 is not None:
            ctx.save()
            ctx.translate(p1[0], p1[1])
            ctx.scale(self.glyphScale)
            ctx.translate(100, 0)
            ctx.drawGlyph(g1)
            ctx.restore()
        if g2 is not None:
            ctx.save()
            ctx.translate(p2[0], p2[1])
            ctx.scale(self.glyphScale)
            ctx.translate(100, 0)
            ctx.drawGlyph(g2)
            ctx.restore()
        if g3 is not None:
            ctx.save()
            ctx.translate(p3[0], p3[1])
            ctx.scale(self.glyphScale)
            ctx.translate(100, 0)
            ctx.drawGlyph(g3)
            ctx.restore()
        
        if self.pointer:
            ctx.save()
            ctx.fill(1,0,0)
            ctx.stroke(None)
            d = 10
            ctx.oval(self.pointer[0]-.5*d, self.pointer[1]-.5*d, d, d)

            f1, f2, f3 = ip(p1, p2, p3, self.pointer)
            self._factors = f1, f2, f3
            r = None
            if self.mGlyphs is not None:
                if None not in self.mGlyphs:
                    try:
                        self.result = r = f1*self.mGlyphs[0] + f2*self.mGlyphs[1] + f3*self.mGlyphs[2]
                    except IndexError or TypeError:
                        print("Sorry, these glyphs can't interpolate..")
                    if r:
                        ctx.save()
                        ctx.translate(self.pointer[0], self.pointer[1])
                        ctx.scale(self.glyphScale)
                        ctx.translate(100, 0)
                        g = RGlyph()
                        g.fromMathGlyph(r)
                        ctx.drawGlyph(g)
                
                        t = "{:02.2f}, {:02.2f}, {:02.2f}".format(f1, f2, f3)
                        ctx.font("Menlo-Regular")
                        ctx.fontSize(6/self.glyphScale)
                        ctx.text(t, (0,-200))
                        ctx.restore()
            ctx.restore()
        ctx.restore()
    
    def menu_makeFont(self, sender=None):
        # note: we can only make a whole new font if the masters are 3 separate ufos.
        print("making a font?", self._factors)
        _, _, masters = self._getMasters()
        print('masters', masters)
        new = RFont(showInterface=True)
        #self.result = r = f1*self.mGlyphs[0] + f2*self.mGlyphs[1] + f3*self.mGlyphs[2]
        

t = Threenterpolation()
