"""
Advanced OMR Synthetic Data Generator with OpenCV-based bubble detection
Automatically detects circles in OMR PDFs and fills them with various mark types
"""

import random
from pathlib import Path
from PIL import Image, ImageDraw
import fitz  # PyMuPDF
import numpy as np
import cv2
import json

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


def detect_circles_opencv(image_array, min_radius=8, max_radius=25):
    """
    Detect circles (bubbles) using OpenCV Hough Circle Transform
    
    Args:
        image_array: numpy array of the image
        min_radius: minimum bubble radius in pixels
        max_radius: maximum bubble radius in pixels
    
    Returns:
        List of (x, y, radius) tuples
    """
    # Convert to grayscale if needed
    if len(image_array.shape) == 3:
        gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = image_array
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (9, 9), 2)
    
    # Detect circles using Hough Circle Transform
    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1,
        minDist=min_radius * 2,  # Minimum distance between circle centers
        param1=50,  # Canny edge detection threshold
        param2=30,  # Accumulator threshold (lower = more circles detected)
        minRadius=min_radius,
        maxRadius=max_radius
    )
    
    detected_bubbles = []
    if circles is not None:
        circles = np.round(circles[0, :]).astype("int")
        for (x, y, r) in circles:
            detected_bubbles.append((x, y, r))
    
    return detected_bubbles


def group_bubbles_by_questions(bubbles, options_per_question=4, tolerance=10):
    """
    Group detected bubbles into questions based on vertical alignment
    
    Args:
        bubbles: List of (x, y, radius) tuples
        options_per_question: Number of options per question (e.g., 4 for A,B,C,D)
        tolerance: Vertical tolerance for grouping bubbles in same row
    
    Returns:
        List of question groups, each containing option bubbles
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


def fill_omr_sheet_advanced(input_pdf, output_pdf, fill_strategy='realistic', 
                            fill_percentage=0.7, detect_bubbles=True,
                            min_radius=8, max_radius=25):
    """
    Fill OMR sheet with synthetic marks using automatic bubble detection
    
    Args:
        input_pdf: Path to input OMR PDF
        output_pdf: Path to output filled PDF
        fill_strategy: 'random', 'all_filled', 'all_varied', 'realistic'
        fill_percentage: Percentage of questions to fill (0.0 to 1.0)
        detect_bubbles: Use OpenCV to detect bubbles automatically
        min_radius: Minimum bubble radius for detection
        max_radius: Maximum bubble radius for detection
    """
    doc = fitz.open(input_pdf)
    filled_questions = {}
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # Convert PDF page to image for processing
        zoom = 2  # 2x resolution for better detection
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to numpy array for OpenCV
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        
        # Detect bubbles
        if detect_bubbles:
            print(f"  Detecting bubbles on page {page_num + 1}...")
            bubbles = detect_circles_opencv(img_array, min_radius, max_radius)
            print(f"  Found {len(bubbles)} bubbles")
        else:
            # Use predefined grid (fallback)
            bubbles = []
        
        if not bubbles:
            print(f"  No bubbles detected on page {page_num + 1}, skipping...")
            continue
        
        # Group bubbles into questions
        questions = group_bubbles_by_questions(bubbles, options_per_question=4)
        print(f"  Grouped into {len(questions)} questions")
        
        # Convert to PIL Image for drawing
        img = Image.fromarray(img_array)
        draw = ImageDraw.Draw(img)
        
        # Fill questions
        for q_idx, question_bubbles in enumerate(questions):
            question_id = f"page{page_num}_q{q_idx}"
            
            # Decide if this question should be filled
            if random.random() > fill_percentage:
                continue  # Skip this question (no attempt)
            
            # Choose ONE option to mark
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
            
            # Draw the mark
            cx, cy, radius = question_bubbles[selected_option]
            draw_mark(draw, mark_type, cx, cy, radius)
            
            filled_questions[question_id] = {
                'option': selected_option,
                'mark_type': mark_type,
                'coordinates': (cx, cy, radius)
            }
        
        # Convert PIL image back to pixmap
        img_bytes = img.tobytes()
        new_pix = fitz.Pixmap(fitz.csRGB, pix.width, pix.height, img_bytes, False)
        
        # Clear page and insert new image
        page.clean_contents()
        page.insert_image(page.rect, pixmap=new_pix)
    
    # Save filled PDF
    doc.save(output_pdf)
    doc.close()
    
    return filled_questions


def generate_test_dataset_advanced(input_pdf, output_dir, num_samples=10, 
                                   detect_bubbles=True):
    """
    Generate multiple filled OMR sheets for testing with automatic bubble detection
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    strategies = ['realistic', 'all_varied', 'random']
    results = []
    
    for i in range(num_samples):
        strategy = random.choice(strategies)
        fill_pct = random.uniform(0.6, 0.95)
        
        output_pdf = output_dir / f"filled_omr_{i+1:03d}_{strategy}.pdf"
        
        print(f"\nGenerating sample {i+1}/{num_samples}: {output_pdf.name}")
        
        filled_data = fill_omr_sheet_advanced(
            input_pdf,
            str(output_pdf),
            fill_strategy=strategy,
            fill_percentage=fill_pct,
            detect_bubbles=detect_bubbles
        )
        
        results.append({
            'file': output_pdf.name,
            'strategy': strategy,
            'fill_percentage': fill_pct,
            'num_filled': len(filled_data),
            'filled_questions': filled_data
        })
    
    # Save metadata
    metadata_file = output_dir / 'generation_metadata.json'
    with open(metadata_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"Generated {num_samples} samples in {output_dir}")
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
    
    print("\n" + "="*60)
    print("Mark Type Distribution")
    print("="*60)
    for mark_type, count in mark_counts.items():
        percentage = (count / total_marks * 100) if total_marks > 0 else 0
        status = MARK_TYPES[mark_type]
        print(f"{mark_type:12s}: {count:4d} ({percentage:5.1f}%) - {status}")
    print(f"{'Total':12s}: {total_marks:4d}")


if __name__ == "__main__":
    import sys
    
    # Configuration
    INPUT_PDF = "1sub.pdf"  # Change to your OMR template
    OUTPUT_DIR = "generated_omr_samples"
    NUM_SAMPLES = 10
    
    # Check command line arguments
    if len(sys.argv) > 1:
        INPUT_PDF = sys.argv[1]
    if len(sys.argv) > 2:
        NUM_SAMPLES = int(sys.argv[2])
    
    print("=" * 60)
    print("Advanced OMR Synthetic Data Generator")
    print("with OpenCV Bubble Detection")
    print("=" * 60)
    print(f"\nInput PDF: {INPUT_PDF}")
    print(f"Output Directory: {OUTPUT_DIR}")
    print(f"Number of Samples: {NUM_SAMPLES}")
    print("\nMark Types:")
    for mark_type, description in MARK_TYPES.items():
        print(f"  • {mark_type:12s}: {description}")
    print("\n" + "=" * 60)
    
    # Check if input file exists
    if not Path(INPUT_PDF).exists():
        print(f"\nError: Input file '{INPUT_PDF}' not found!")
        print("\nAvailable PDF files:")
        for pdf in Path(".").glob("*.pdf"):
            print(f"  - {pdf.name}")
        sys.exit(1)
    
    # Generate test dataset
    try:
        results = generate_test_dataset_advanced(
            INPUT_PDF, 
            OUTPUT_DIR, 
            NUM_SAMPLES,
            detect_bubbles=True
        )
        
        # Analyze distribution
        analyze_mark_distribution(results)
        
        print("\n" + "=" * 60)
        print("Generation Complete!")
        print("=" * 60)
        print("\nRecommended Thresholds for Scanner:")
        print("  • Fill ratio:    min 0.42 (accept filled/sloppy)")
        print("  • Circularity:   min 0.55 (reject ticks/crosses)")
        print("  • Aspect ratio:  max 1.8  (reject elongated marks)")
        print("  • Edge density:  max 0.55 (reject concentric circles)")
        print("  • Symmetry:      min 0.60 (reject half-circles)")
        print("\nNext Steps:")
        print("  1. Review generated PDFs in output directory")
        print("  2. Test with your OMR scanner")
        print("  3. Adjust thresholds based on results")
        print("  4. Check generation_metadata.json for details")
        
    except Exception as e:
        print(f"\nError during generation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
