"""
Test script to visualize all mark types
Creates a single image showing all mark types for verification
"""

from PIL import Image, ImageDraw, ImageFont
from omr_advanced_filler import (
    draw_filled_circle, draw_sloppy_fill, draw_half_circle,
    draw_concentric_circles, draw_tick, draw_cross, draw_dot,
    MARK_TYPES
)

def create_mark_showcase():
    """Create a showcase image of all mark types"""
    
    # Image dimensions
    width = 800
    height = 600
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    
    # Title
    try:
        font_title = ImageFont.truetype("arial.ttf", 32)
        font_label = ImageFont.truetype("arial.ttf", 16)
    except:
        font_title = ImageFont.load_default()
        font_label = ImageFont.load_default()
    
    draw.text((width//2 - 200, 20), "OMR Mark Types Showcase", fill='black', font=font_title)
    
    # Draw all mark types
    mark_functions = {
        'filled': draw_filled_circle,
        'sloppy': draw_sloppy_fill,
        'half': draw_half_circle,
        'concentric': draw_concentric_circles,
        'tick': draw_tick,
        'cross': draw_cross,
        'dot': draw_dot,
    }
    
    # Layout: 4 marks per row
    marks_per_row = 4
    bubble_radius = 40
    spacing_x = width // marks_per_row
    spacing_y = 150
    start_y = 100
    
    mark_list = list(mark_functions.items())
    
    for idx, (mark_name, mark_func) in enumerate(mark_list):
        row = idx // marks_per_row
        col = idx % marks_per_row
        
        cx = spacing_x * col + spacing_x // 2
        cy = start_y + row * spacing_y
        
        # Draw bubble outline
        draw.ellipse(
            [cx - bubble_radius - 2, cy - bubble_radius - 2,
             cx + bubble_radius + 2, cy + bubble_radius + 2],
            outline='gray',
            width=2
        )
        
        # Draw the mark
        mark_func(draw, cx, cy, bubble_radius)
        
        # Label
        label = MARK_TYPES[mark_name]
        verdict = "✓ ACCEPT" if mark_name in ['filled', 'sloppy'] else "✗ REJECT"
        color = 'green' if mark_name in ['filled', 'sloppy'] else 'red'
        
        # Draw label below bubble
        label_y = cy + bubble_radius + 15
        draw.text((cx - 60, label_y), mark_name.upper(), fill='black', font=font_label)
        draw.text((cx - 60, label_y + 20), verdict, fill=color, font=font_label)
    
    # Add empty bubble example
    idx = len(mark_list)
    row = idx // marks_per_row
    col = idx % marks_per_row
    cx = spacing_x * col + spacing_x // 2
    cy = start_y + row * spacing_y
    
    draw.ellipse(
        [cx - bubble_radius - 2, cy - bubble_radius - 2,
         cx + bubble_radius + 2, cy + bubble_radius + 2],
        outline='gray',
        width=2
    )
    label_y = cy + bubble_radius + 15
    draw.text((cx - 60, label_y), "EMPTY", fill='black', font=font_label)
    draw.text((cx - 60, label_y + 20), "✗ REJECT", fill='red', font=font_label)
    
    # Add footer with threshold info
    footer_y = height - 80
    draw.text((20, footer_y), "Recommended Scanner Thresholds:", fill='black', font=font_label)
    draw.text((20, footer_y + 20), "Fill Ratio ≥ 0.42  |  Circularity ≥ 0.55  |  Aspect Ratio ≤ 1.8", fill='darkblue', font=font_label)
    draw.text((20, footer_y + 40), "Edge Density ≤ 0.55  |  Symmetry ≥ 0.60", fill='darkblue', font=font_label)
    
    return img


def create_comparison_grid():
    """Create a grid showing multiple instances of each mark type"""
    
    width = 1000
    height = 800
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    
    try:
        font_title = ImageFont.truetype("arial.ttf", 24)
        font_label = ImageFont.truetype("arial.ttf", 14)
    except:
        font_title = ImageFont.load_default()
        font_label = ImageFont.load_default()
    
    draw.text((width//2 - 150, 10), "Mark Type Variations", fill='black', font=font_title)
    
    mark_functions = {
        'filled': draw_filled_circle,
        'sloppy': draw_sloppy_fill,
        'half': draw_half_circle,
        'concentric': draw_concentric_circles,
        'tick': draw_tick,
        'cross': draw_cross,
        'dot': draw_dot,
    }
    
    # Layout
    instances_per_mark = 5
    bubble_radius = 25
    spacing_x = 120
    spacing_y = 100
    start_x = 100
    start_y = 60
    
    for row_idx, (mark_name, mark_func) in enumerate(mark_functions.items()):
        # Label for this row
        draw.text((10, start_y + row_idx * spacing_y + 15), 
                 mark_name.upper(), fill='black', font=font_label)
        
        # Draw multiple instances
        for col_idx in range(instances_per_mark):
            cx = start_x + col_idx * spacing_x
            cy = start_y + row_idx * spacing_y + 30
            
            # Bubble outline
            draw.ellipse(
                [cx - bubble_radius - 1, cy - bubble_radius - 1,
                 cx + bubble_radius + 1, cy + bubble_radius + 1],
                outline='lightgray',
                width=1
            )
            
            # Draw mark with variation
            mark_func(draw, cx, cy, bubble_radius)
    
    return img


if __name__ == "__main__":
    print("Generating mark type showcase...")
    
    # Create showcase
    showcase = create_mark_showcase()
    showcase.save("mark_types_showcase.png")
    print("✓ Saved: mark_types_showcase.png")
    
    # Create comparison grid
    comparison = create_comparison_grid()
    comparison.save("mark_types_comparison.png")
    print("✓ Saved: mark_types_comparison.png")
    
    print("\nDone! Open the PNG files to see all mark types.")
    print("\nMark Types:")
    for mark_type, description in MARK_TYPES.items():
        print(f"  • {mark_type:12s}: {description}")
