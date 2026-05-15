"""
OMR Synthetic Data Generator
Fills OMR sheets with various mark types for threshold analysis
"""

import random
from pathlib import Path
from PIL import Image, ImageDraw
import fitz  # PyMuPDF
import numpy as np

# Mark types based on your requirements
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
    # Create irregular polygon that roughly fills the circle
    points = []
    num_points = 24
    for i in range(num_points):
        angle = (2 * np.pi * i) / num_points
        # Vary radius randomly for each point
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
    # Outer circle
    width = max(2, int(radius * 0.12))
    bbox1 = [cx - radius * 0.9, cy - radius * 0.9, cx + radius * 0.9, cy + radius * 0.9]
    draw.ellipse(bbox1, fill=None, outline='black', width=width)
    
    # Inner circle
    bbox2 = [cx - radius * 0.5, cy - radius * 0.5, cx + radius * 0.5, cy + radius * 0.5]
    draw.ellipse(bbox2, fill=None, outline='black', width=width)


def draw_tick(draw, cx, cy, radius):
    """Draw a checkmark/tick (REJECT - high aspect ratio, low circularity)"""
    width = max(2, int(radius * 0.2))
    
    # Tick mark coordinates
    x1, y1 = cx - radius * 0.6, cy + radius * 0.1
    x2, y2 = cx - radius * 0.1, cy + radius * 0.6
    x3, y3 = cx + radius * 0.7, cy - radius * 0.5
    
    draw.line([(x1, y1), (x2, y2)], fill='black', width=width, joint='curve')
    draw.line([(x2, y2), (x3, y3)], fill='black', width=width, joint='curve')


def draw_cross(draw, cx, cy, radius):
    """Draw an X/cross mark (REJECT - high aspect ratio, low circularity)"""
    width = max(2, int(radius * 0.2))
    
    # Diagonal lines
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
    pass  # Do nothing


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


def detect_bubbles_simple(image, min_radius=10, max_radius=30):
    """
    Simple bubble detection - looks for circular regions
    Returns list of (x, y, radius) tuples
    
    For production, you'd use more sophisticated detection like:
    - Hough Circle Transform
    - Template matching
    - Pre-defined coordinates from template
    """
    # This is a placeholder - in real implementation, you'd detect actual bubbles
    # For now, we'll create a grid pattern typical of OMR sheets
    
    width, height = image.size
    bubbles = []
    
    # Typical OMR layout: questions in rows, options in columns
    # Adjust these based on your actual OMR template
    num_questions = 50  # Adjust based on your sheet
    options_per_question = 4  # A, B, C, D
    
    start_x = 100
    start_y = 150
    question_spacing = 30
    option_spacing = 40
    bubble_radius = 12
    
    for q in range(num_questions):
        y = start_y + q * question_spacing
        if y > height - 50:  # Don't go beyond page
            break
            
        for opt in range(options_per_question):
            x = start_x + opt * option_spacing
            bubbles.append((x, y, bubble_radius))
    
    return bubbles


def detect_bubbles_from_pdf_annotations(pdf_path):
    """
    Detect bubbles from PDF annotations or form fields
    More accurate than image-based detection
    """
    doc = fitz.open(pdf_path)
    bubbles_by_page = {}
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        bubbles = []
        
        # Try to find circles/annotations
        # This is a simplified version - adjust based on your PDF structure
        
        # For demonstration, create a standard grid
        # In production, parse actual PDF structure
        page_rect = page.rect
        width = page_rect.width
        height = page_rect.height
        
        # Standard OMR layout
        num_questions = 50
        options_per_question = 4
        
        start_x = 100
        start_y = 150
        question_spacing = 15
        option_spacing = 30
        bubble_radius = 8
        
        for q in range(num_questions):
            y = start_y + q * question_spacing
            if y > height - 50:
                break
                
            for opt in range(options_per_question):
                x = start_x + opt * option_spacing
                bubbles.append((x, y, bubble_radius))
        
        bubbles_by_page[page_num] = bubbles
    
    doc.close()
    return bubbles_by_page


def fill_omr_sheet(input_pdf, output_pdf, fill_strategy='random', fill_percentage=0.7):
    """
    Fill OMR sheet with synthetic marks
    
    Args:
        input_pdf: Path to input OMR PDF
        output_pdf: Path to output filled PDF
        fill_strategy: 'random', 'all_filled', 'all_varied', 'realistic'
        fill_percentage: Percentage of questions to fill (0.0 to 1.0)
    """
    doc = fitz.open(input_pdf)
    
    # Detect bubbles
    bubbles_by_page = detect_bubbles_from_pdf_annotations(input_pdf)
    
    # Track which questions have been filled (one answer per question)
    filled_questions = {}
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        bubbles = bubbles_by_page.get(page_num, [])
        
        if not bubbles:
            continue
        
        # Convert PDF page to image
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x resolution
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        draw = ImageDraw.Draw(img)
        
        # Group bubbles by question (assuming 4 options per question)
        options_per_question = 4
        questions = []
        for i in range(0, len(bubbles), options_per_question):
            question_bubbles = bubbles[i:i+options_per_question]
            if len(question_bubbles) == options_per_question:
                questions.append(question_bubbles)
        
        # Fill questions
        for q_idx, question_bubbles in enumerate(questions):
            question_id = f"page{page_num}_q{q_idx}"
            
            # Decide if this question should be filled
            if random.random() > fill_percentage:
                continue  # Skip this question (no attempt)
            
            # Choose ONE option to mark (only one answer per question)
            selected_option = random.randint(0, len(question_bubbles) - 1)
            
            # Choose mark type based on strategy
            if fill_strategy == 'random':
                mark_type = random.choice(list(MARK_TYPES.keys()))
            elif fill_strategy == 'all_filled':
                mark_type = 'filled'
            elif fill_strategy == 'all_varied':
                mark_type = random.choice(list(MARK_TYPES.keys()))
            elif fill_strategy == 'realistic':
                # Realistic: mostly filled/sloppy, occasionally wrong marks
                weights = [0.70, 0.15, 0.03, 0.03, 0.03, 0.03, 0.02, 0.01]
                mark_type = random.choices(list(MARK_TYPES.keys()), weights=weights)[0]
            else:
                mark_type = 'filled'
            
            # Draw the mark on the selected option only
            cx, cy, radius = question_bubbles[selected_option]
            # Scale coordinates for 2x resolution
            cx_scaled = cx * 2
            cy_scaled = cy * 2
            radius_scaled = radius * 2
            
            draw_mark(draw, mark_type, cx_scaled, cy_scaled, radius_scaled)
            
            filled_questions[question_id] = {
                'option': selected_option,
                'mark_type': mark_type
            }
        
        # Convert image back to PDF
        img_bytes = img.tobytes()
        img_pdf = fitz.Pixmap(fitz.csRGB, pix.width, pix.height, img_bytes, pix.alpha)
        page.insert_image(page.rect, pixmap=img_pdf)
    
    # Save filled PDF
    doc.save(output_pdf)
    doc.close()
    
    return filled_questions


def generate_test_dataset(input_pdf, output_dir, num_samples=10):
    """
    Generate multiple filled OMR sheets for testing
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    strategies = ['realistic', 'all_varied', 'random']
    
    results = []
    
    for i in range(num_samples):
        strategy = random.choice(strategies)
        fill_pct = random.uniform(0.6, 0.95)
        
        output_pdf = output_dir / f"filled_omr_{i+1:03d}_{strategy}.pdf"
        
        print(f"Generating sample {i+1}/{num_samples}: {output_pdf.name}")
        
        filled_data = fill_omr_sheet(
            input_pdf,
            str(output_pdf),
            fill_strategy=strategy,
            fill_percentage=fill_pct
        )
        
        results.append({
            'file': output_pdf.name,
            'strategy': strategy,
            'fill_percentage': fill_pct,
            'filled_questions': filled_data
        })
    
    # Save metadata
    import json
    metadata_file = output_dir / 'generation_metadata.json'
    with open(metadata_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nGenerated {num_samples} samples in {output_dir}")
    print(f"Metadata saved to {metadata_file}")
    
    return results


def analyze_mark_distribution(results):
    """Analyze the distribution of mark types in generated samples"""
    mark_counts = {mark: 0 for mark in MARK_TYPES.keys()}
    total_marks = 0
    
    for result in results:
        for q_data in result['filled_questions'].values():
            mark_type = q_data['mark_type']
            mark_counts[mark_type] += 1
            total_marks += 1
    
    print("\n=== Mark Type Distribution ===")
    for mark_type, count in mark_counts.items():
        percentage = (count / total_marks * 100) if total_marks > 0 else 0
        status = MARK_TYPES[mark_type]
        print(f"{mark_type:12s}: {count:4d} ({percentage:5.1f}%) - {status}")
    print(f"{'Total':12s}: {total_marks:4d}")


if __name__ == "__main__":
    # Configuration
    INPUT_PDF = "1sub.pdf"  # Change to your OMR template
    OUTPUT_DIR = "generated_omr_samples"
    NUM_SAMPLES = 20
    
    print("=" * 60)
    print("OMR Synthetic Data Generator")
    print("=" * 60)
    print("\nMark Types:")
    for mark_type, description in MARK_TYPES.items():
        print(f"  • {mark_type:12s}: {description}")
    print("\n" + "=" * 60)
    
    # Check if input file exists
    if not Path(INPUT_PDF).exists():
        print(f"\nError: Input file '{INPUT_PDF}' not found!")
        print("Available PDF files:")
        for pdf in Path(".").glob("*.pdf"):
            print(f"  - {pdf.name}")
        exit(1)
    
    # Generate test dataset
    results = generate_test_dataset(INPUT_PDF, OUTPUT_DIR, NUM_SAMPLES)
    
    # Analyze distribution
    analyze_mark_distribution(results)
    
    print("\n" + "=" * 60)
    print("Generation complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Review generated PDFs in the output directory")
    print("2. Use these samples to test your OMR scanner")
    print("3. Adjust thresholds based on the analysis:")
    print("   - Fill ratio: min 0.42 (to accept filled/sloppy)")
    print("   - Circularity: min 0.55 (to reject ticks/crosses)")
    print("   - Aspect ratio: max 1.8 (to reject elongated marks)")
    print("   - Edge density: max 0.55 (to reject concentric circles)")
    print("   - Symmetry: min 0.60 (to reject half-circles)")
