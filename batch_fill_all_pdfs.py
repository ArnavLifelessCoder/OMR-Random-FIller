"""
Batch OMR Filler - Process ALL PDFs (1sub, 2sub, 3sub)
Generates filled versions for each template
"""

import random
from pathlib import Path
from PIL import Image, ImageDraw
import fitz  # PyMuPDF
import numpy as np
import cv2
import json
from datetime import datetime

# Mark types
MARK_TYPES = {
    'filled': 'Filled circle (ACCEPT)',
    'sloppy': 'Sloppy fill (ACCEPT)',
    'half': 'Half circle (REJECT)',
    'concentric': 'Concentric circles (REJECT)',
    'tick': 'Tick/checkmark (REJECT)',
    'cross': 'Cross/X (REJECT)',
    'dot': 'Small dot (REJECT)',
    'empty': 'No attempt (REJECT)'
}


def draw_filled_circle(draw, cx, cy, radius, noisy=True):
    """Draw a fully filled circle (ACCEPT)"""
    if noisy:
        jitter_x = random.uniform(-radius * 0.05, radius * 0.05)
        jitter_y = random.uniform(-radius * 0.05, radius * 0.05)
        r_var = radius * random.uniform(0.95, 1.0)
    else:
        jitter_x = jitter_y = 0
        r_var = radius
    
    bbox = [
        cx - r_var + jitter_x,
        cy - r_var + jitter_y,
        cx + r_var + jitter_x,
        cy + r_var + jitter_y
    ]
    draw.ellipse(bbox, fill='black', outline='black')


def draw_sloppy_fill(draw, cx, cy, radius):
    """Draw a sloppy/irregular filled circle (ACCEPT but borderline)"""
    points = []
    num_points = 24
    for i in range(num_points):
        angle = (2 * np.pi * i) / num_points
        r = radius * random.uniform(0.7, 0.95)
        x = cx + r * np.cos(angle)
        y = cy + r * np.sin(angle)
        points.append((x, y))
    
    draw.polygon(points, fill='black', outline='black')


def draw_half_circle(draw, cx, cy, radius):
    """Draw a half-filled circle (REJECT - asymmetric)"""
    bbox = [cx - radius, cy - radius, cx + radius, cy + radius]
    draw.pieslice(bbox, start=0, end=180, fill='black', outline='black')


def draw_concentric_circles(draw, cx, cy, radius):
    """Draw concentric circles - outline only (REJECT - low fill ratio)"""
    width = max(2, int(radius * 0.12))
    bbox1 = [cx - radius * 0.9, cy - radius * 0.9, cx + radius * 0.9, cy + radius * 0.9]
    draw.ellipse(bbox1, fill=None, outline='black', width=width)
    
    bbox2 = [cx - radius * 0.5, cy - radius * 0.5, cx + radius * 0.5, cy + radius * 0.5]
    draw.ellipse(bbox2, fill=None, outline='black', width=width)


def draw_tick(draw, cx, cy, radius):
    """Draw a checkmark/tick (REJECT - high aspect ratio, low circularity)"""
    width = max(2, int(radius * 0.2))
    
    x1, y1 = cx - radius * 0.6, cy + radius * 0.1
    x2, y2 = cx - radius * 0.1, cy + radius * 0.6
    x3, y3 = cx + radius * 0.7, cy - radius * 0.5
    
    draw.line([(x1, y1), (x2, y2)], fill='black', width=width, joint='curve')
    draw.line([(x2, y2), (x3, y3)], fill='black', width=width, joint='curve')


def draw_cross(draw, cx, cy, radius):
    """Draw an X/cross mark (REJECT - high aspect ratio, low circularity)"""
    width = max(2, int(radius * 0.2))
    
    x1, y1 = cx - radius * 0.7, cy - radius * 0.7
    x2, y2 = cx + radius * 0.7, cy + radius * 0.7
    x3, y3 = cx + radius * 0.7, cy - radius * 0.7
    x4, y4 = cx - radius * 0.7, cy + radius * 0.7
    
    draw.line([(x1, y1), (x2, y2)], fill='black', width=width)
    draw.line([(x3, y3), (x4, y4)], fill='black', width=width)


def draw_dot(draw, cx, cy, radius):
    """Draw a small dot (REJECT - very low fill ratio)"""
    r = radius * 0.25
    bbox = [cx - r, cy - r, cx + r, cy + r]
    draw.ellipse(bbox, fill='black', outline='black')


def draw_empty(draw, cx, cy, radius):
    """No mark - empty bubble (REJECT)"""
    pass


def draw_mark(draw, mark_type, cx, cy, radius):
    """Draw the specified mark type"""
    mark_functions = {
        'filled': draw_filled_circle,
        'sloppy': draw_sloppy_fill,
        'half': draw_half_circle,
        'concentric': draw_concentric_circles,
        'tick': draw_tick,
        'cross': draw_cross,
        'dot': draw_dot,
        'empty': draw_empty
    }
    
    if mark_type in mark_functions:
        mark_functions[mark_type](draw, cx, cy, radius)


def detect_circles_opencv(image_array, min_radius=6, max_radius=18):
    """
    Detect circles (bubbles) using OpenCV Hough Circle Transform
    More conservative parameters to avoid false positives
    """
    import cv2
    
    # Convert to grayscale
    if len(image_array.shape) == 3:
        gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = image_array
    
    # Apply bilateral filter to preserve edges while reducing noise
    filtered = cv2.bilateralFilter(gray, 9, 75, 75)
    
    # Detect circles with stricter parameters
    circles = cv2.HoughCircles(
        filtered,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=15,  # Increased to avoid detecting overlapping circles
        param1=50,
        param2=35,   # Higher threshold = fewer false positives
        minRadius=min_radius,
        maxRadius=max_radius
    )
    
    detected_bubbles = []
    if circles is not None:
        circles = np.round(circles[0, :]).astype("int")
        
        # Filter out circles that are too close to each other
        for (x, y, r) in circles:
            # Check if this circle is too close to any existing circle
            too_close = False
            for (ex, ey, er) in detected_bubbles:
                dist = np.sqrt((x - ex)**2 + (y - ey)**2)
                if dist < (r + er) * 0.8:  # If circles overlap significantly
                    too_close = True
                    break
            
            if not too_close:
                detected_bubbles.append((x, y, r))
    
    return detected_bubbles


def group_bubbles_by_questions(bubbles, options_per_question=4, tolerance=15):
    """
    Group detected bubbles into questions based on vertical alignment
    """
    if not bubbles:
        return []
    
    # Sort bubbles by Y coordinate (top to bottom), then X (left to right)
    sorted_bubbles = sorted(bubbles, key=lambda b: (b[1], b[0]))
    
    questions = []
    current_row = []
    current_y = sorted_bubbles[0][1]
    
    for bubble in sorted_bubbles:
        x, y, r = bubble
        
        # Check if this bubble is in the same row
        if abs(y - current_y) <= tolerance:
            current_row.append(bubble)
        else:
            # New row - save previous row if it has correct number of options
            if len(current_row) == options_per_question:
                questions.append(current_row)
            elif len(current_row) > 0:
                # Try to split if we have multiple questions in one row
                for i in range(0, len(current_row), options_per_question):
                    group = current_row[i:i+options_per_question]
                    if len(group) == options_per_question:
                        questions.append(group)
            
            # Start new row
            current_row = [bubble]
            current_y = y
    
    # Don't forget the last row
    if len(current_row) == options_per_question:
        questions.append(current_row)
    
    return questions


def fill_pdf_with_marks(input_pdf, output_pdf, fill_strategy='realistic', fill_percentage=0.7):
    """
    Fill a single PDF with random marks
    """
    doc = fitz.open(input_pdf)
    filled_questions = {}
    template_name = Path(input_pdf).stem
    
    print(f"  Processing: {template_name}")
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # Convert to image
        zoom = 2
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to numpy array for OpenCV
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        
        # Detect bubbles using OpenCV with conservative parameters
        print(f"    Page {page_num + 1}: Detecting bubbles...")
        bubbles = detect_circles_opencv(img_array, min_radius=6, max_radius=18)
        
        if not bubbles:
            print(f"    Warning: No bubbles detected on page {page_num + 1}")
            continue
        
        print(f"    Found {len(bubbles)} bubbles")
        
        # Convert to PIL
        img = Image.fromarray(img_array)
        draw = ImageDraw.Draw(img)
        
        # Group bubbles into questions (4 options per question)
        questions = group_bubbles_by_questions(bubbles, options_per_question=4, tolerance=15)
        
        print(f"    Grouped into {len(questions)} questions")
        
        # Fill questions
        filled_count = 0
        for q_idx, question_bubbles in enumerate(questions):
            question_id = f"page{page_num}_q{q_idx}"
            
            # Decide if this question should be filled
            if random.random() > fill_percentage:
                continue
            
            # Choose ONE option
            selected_option = random.randint(0, len(question_bubbles) - 1)
            
            # Choose mark type
            if fill_strategy == 'random':
                mark_type = random.choice(list(MARK_TYPES.keys()))
            elif fill_strategy == 'all_filled':
                mark_type = 'filled'
            elif fill_strategy == 'all_varied':
                mark_type = random.choice(list(MARK_TYPES.keys()))
            elif fill_strategy == 'realistic':
                weights = [0.70, 0.15, 0.03, 0.03, 0.03, 0.03, 0.02, 0.01]
                mark_type = random.choices(list(MARK_TYPES.keys()), weights=weights)[0]
            else:
                mark_type = 'filled'
            
            # Draw mark (coordinates are already scaled for 2x zoom from detection)
            cx, cy, radius = question_bubbles[selected_option]
            
            draw_mark(draw, mark_type, cx, cy, radius)
            
            filled_questions[question_id] = {
                'option': int(selected_option),
                'mark_type': mark_type,
                'coordinates': (int(cx), int(cy), int(radius))
            }
            filled_count += 1
        
        print(f"    Filled {filled_count} questions")
        
        # Convert back to PDF
        img_bytes = img.tobytes()
        new_pix = fitz.Pixmap(fitz.csRGB, pix.width, pix.height, img_bytes, False)
        
        page.clean_contents()
        page.insert_image(page.rect, pixmap=new_pix)
    
    # Save
    doc.save(output_pdf)
    doc.close()
    
    return filled_questions


def batch_process_all_pdfs(num_samples_per_template=10):
    """
    Process all three PDF templates (1sub, 2sub, 3sub)
    """
    
    # Find all template PDFs
    template_pdfs = ['1sub.pdf', '2sub.pdf', '3sub.pdf']
    
    # Check which ones exist
    existing_templates = []
    for pdf in template_pdfs:
        if Path(pdf).exists():
            existing_templates.append(pdf)
        else:
            print(f"Warning: {pdf} not found, skipping...")
    
    if not existing_templates:
        print("Error: No template PDFs found!")
        print("Expected: 1sub.pdf, 2sub.pdf, 3sub.pdf")
        return
    
    print(f"\nFound {len(existing_templates)} templates: {', '.join(existing_templates)}")
    print(f"Generating {num_samples_per_template} samples per template")
    print("="*70)
    
    # Create output directory
    output_dir = Path("generated_omr_samples")
    output_dir.mkdir(exist_ok=True)
    
    all_results = []
    strategies = ['realistic', 'all_varied', 'random']
    
    # Process each template
    for template_pdf in existing_templates:
        template_name = Path(template_pdf).stem
        print(f"\n{'='*70}")
        print(f"Processing Template: {template_name}")
        print(f"{'='*70}")
        
        for i in range(num_samples_per_template):
            strategy = random.choice(strategies)
            fill_pct = random.uniform(0.6, 0.95)
            
            output_filename = f"filled_{template_name}_{i+1:03d}_{strategy}.pdf"
            output_path = output_dir / output_filename
            
            print(f"\nSample {i+1}/{num_samples_per_template}: {output_filename}")
            
            try:
                filled_data = fill_pdf_with_marks(
                    template_pdf,
                    str(output_path),
                    fill_strategy=strategy,
                    fill_percentage=fill_pct
                )
                
                all_results.append({
                    'template': template_name,
                    'file': output_filename,
                    'strategy': strategy,
                    'fill_percentage': fill_pct,
                    'num_filled': len(filled_data),
                    'filled_questions': filled_data
                })
                
                print(f"  ✓ Generated: {output_filename}")
                
            except Exception as e:
                print(f"  ✗ Error: {e}")
                import traceback
                traceback.print_exc()
    
    # Save metadata
    metadata_file = output_dir / 'generation_metadata.json'
    with open(metadata_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n{'='*70}")
    print(f"BATCH PROCESSING COMPLETE")
    print(f"{'='*70}")
    print(f"\nTotal samples generated: {len(all_results)}")
    print(f"Output directory: {output_dir}")
    print(f"Metadata file: {metadata_file}")
    
    # Summary by template
    print(f"\nSummary by template:")
    for template_pdf in existing_templates:
        template_name = Path(template_pdf).stem
        count = sum(1 for r in all_results if r['template'] == template_name)
        print(f"  {template_name}: {count} samples")
    
    # Mark type distribution
    mark_counts = {mark: 0 for mark in MARK_TYPES.keys()}
    total_marks = 0
    
    for result in all_results:
        for q_data in result['filled_questions'].values():
            mark_type = q_data['mark_type']
            mark_counts[mark_type] += 1
            total_marks += 1
    
    print(f"\n{'='*70}")
    print("Mark Type Distribution (All Templates)")
    print(f"{'='*70}")
    for mark_type, count in mark_counts.items():
        percentage = (count / total_marks * 100) if total_marks > 0 else 0
        status = MARK_TYPES[mark_type]
        print(f"{mark_type:12s}: {count:5d} ({percentage:5.1f}%) - {status}")
    print(f"{'Total':12s}: {total_marks:5d}")
    
    return all_results


if __name__ == "__main__":
    import sys
    
    # Get number of samples from command line or use default
    num_samples = 10
    if len(sys.argv) > 1:
        try:
            num_samples = int(sys.argv[1])
        except:
            print(f"Invalid number: {sys.argv[1]}, using default: 10")
    
    print("="*70)
    print("BATCH OMR FILLER - Process All Templates")
    print("="*70)
    print(f"\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Samples per template: {num_samples}")
    print("\nMark Types:")
    for mark_type, description in MARK_TYPES.items():
        print(f"  • {mark_type:12s}: {description}")
    
    # Process all PDFs
    results = batch_process_all_pdfs(num_samples_per_template=num_samples)
    
    print(f"\n{'='*70}")
    print("ALL DONE! 🎉")
    print(f"{'='*70}")
    print("\nNext steps:")
    print("  1. Check generated_omr_samples/ folder")
    print("  2. Review the filled PDFs")
    print("  3. Run your OMR scanner on them")
    print("  4. Use analyze_results.py to compare results")
