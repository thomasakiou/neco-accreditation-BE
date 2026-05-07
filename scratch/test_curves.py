from PIL import Image, ImageDraw

def _draw_swooshes(draw, width, height):
    orange = (255, 140, 0)
    yellow = (255, 200, 0)
    light_green = (100, 180, 50)
    dark_green = (0, 80, 40)
    
    # Top swooshes
    # We want a sweep that goes from the left edge (about 20% down) to the top edge (about 80% across)
    
    # Center the circles way down and left, or way up and right?
    # To curve up like a smile, center must be ABOVE the image.
    
    # Dark green: largest, bottom-most of the top group
    # Left edge ~ 0.25 height. Right edge ~ 0.1 height. Middle dips down. Wait, the sample curves *up* in the middle?
    # Looking at the sample, the top curve looks like a smile (convex from bottom) or frown (concave from bottom)?
    # Actually, it's convex from bottom. It arcs UPwards in the middle? No, the sample's top swoosh swoops DOWN from the left edge, then UP to the top-right. So it's a smile.
    # Wait, if it dips down and goes up, then center is ABOVE the image.
    
    draw.ellipse([-width*0.2, -height*2.0, width*1.5, height*0.35], fill=dark_green)
    draw.ellipse([-width*0.3, -height*2.1, width*1.4, height*0.25], fill=light_green)
    draw.ellipse([-width*0.4, -height*2.2, width*1.3, height*0.15], fill=yellow)
    draw.ellipse([-width*0.5, -height*2.3, width*1.2, height*0.08], fill=orange)

    # Bottom swooshes
    # Same thing but rotated 180. Center is BELOW the image.
    draw.ellipse([-width*0.5, height*0.65, width*1.2, height*3.0], fill=dark_green)
    draw.ellipse([-width*0.4, height*0.75, width*1.3, height*3.1], fill=light_green)
    draw.ellipse([-width*0.3, height*0.85, width*1.4, height*3.2], fill=yellow)
    draw.ellipse([-width*0.2, height*0.92, width*1.5, height*3.3], fill=orange)


width, height = 1574, 1115
img = Image.new("RGBA", (width, height), (255, 255, 255, 255))
draw = ImageDraw.Draw(img)
_draw_swooshes(draw, width, height)
img.save("scratch/curves.png")
print("Done")
