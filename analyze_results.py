"""
Analyze OMR scanner results and compare with ground truth
Helps tune thresholds by showing false positives/negatives
"""

import json
from pathlib import Path
from collections import defaultdict
import sys


def load_ground_truth(metadata_file):
    """Load ground truth from generation metadata"""
    with open(metadata_file, 'r') as f:
        data = json.load(f)
    return data


def analyze_scanner_accuracy(ground_truth, scanner_results):
    """
    Compare scanner results with ground truth
    
    Args:
        ground_truth: List of dicts from generation_metadata.json
        scanner_results: Dict mapping filename to detected answers
                        Format: {'filled_omr_001.pdf': {'page0_q0': 2, 'page0_q1': 0, ...}}
    
    Returns:
        Analysis dict with accuracy metrics
    """
    
    total_questions = 0
    correct_detections = 0
    false_positives = 0  # Scanner detected mark that shouldn't be accepted
    false_negatives = 0  # Scanner missed valid mark
    
    mark_type_stats = defaultdict(lambda: {'total': 0, 'detected': 0, 'missed': 0})
    
    for sample in ground_truth:
        filename = sample['file']
        
        if filename not in scanner_results:
            print(f"Warning: No scanner results for {filename}")
            continue
        
        scanner_answers = scanner_results[filename]
        ground_truth_data = sample['filled_questions']
        
        for question_id, gt_data in ground_truth_data.items():
            total_questions += 1
            
            gt_option = gt_data['option']
            gt_mark_type = gt_data['mark_type']
            
            # Should this mark be accepted?
            should_accept = gt_mark_type in ['filled', 'sloppy']
            
            # Did scanner detect it?
            scanner_detected = question_id in scanner_answers
            
            if scanner_detected:
                scanner_option = scanner_answers[question_id]
                
                if should_accept and scanner_option == gt_option:
                    # Correct detection
                    correct_detections += 1
                    mark_type_stats[gt_mark_type]['detected'] += 1
                elif not should_accept:
                    # False positive - detected wrong mark type
                    false_positives += 1
                    mark_type_stats[gt_mark_type]['detected'] += 1
                elif scanner_option != gt_option:
                    # Wrong option detected (shouldn't happen with our data)
                    false_positives += 1
            else:
                if should_accept:
                    # False negative - missed valid mark
                    false_negatives += 1
                    mark_type_stats[gt_mark_type]['missed'] += 1
                # else: correctly rejected invalid mark
            
            mark_type_stats[gt_mark_type]['total'] += 1
    
    # Calculate metrics
    accuracy = correct_detections / total_questions if total_questions > 0 else 0
    precision = correct_detections / (correct_detections + false_positives) if (correct_detections + false_positives) > 0 else 0
    recall = correct_detections / (correct_detections + false_negatives) if (correct_detections + false_negatives) > 0 else 0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    return {
        'total_questions': total_questions,
        'correct_detections': correct_detections,
        'false_positives': false_positives,
        'false_negatives': false_negatives,
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1_score': f1_score,
        'mark_type_stats': dict(mark_type_stats)
    }


def print_analysis_report(analysis):
    """Print formatted analysis report"""
    
    print("\n" + "="*70)
    print("OMR SCANNER ACCURACY ANALYSIS")
    print("="*70)
    
    print(f"\nTotal Questions Analyzed: {analysis['total_questions']}")
    print(f"Correct Detections:       {analysis['correct_detections']}")
    print(f"False Positives:          {analysis['false_positives']} (accepted wrong marks)")
    print(f"False Negatives:          {analysis['false_negatives']} (missed valid marks)")
    
    print("\n" + "-"*70)
    print("PERFORMANCE METRICS")
    print("-"*70)
    print(f"Accuracy:   {analysis['accuracy']*100:6.2f}%  (overall correctness)")
    print(f"Precision:  {analysis['precision']*100:6.2f}%  (of detected marks, how many correct)")
    print(f"Recall:     {analysis['recall']*100:6.2f}%  (of valid marks, how many detected)")
    print(f"F1 Score:   {analysis['f1_score']*100:6.2f}%  (harmonic mean of precision/recall)")
    
    print("\n" + "-"*70)
    print("MARK TYPE BREAKDOWN")
    print("-"*70)
    print(f"{'Mark Type':<15} {'Total':<8} {'Detected':<10} {'Missed':<8} {'Detection Rate'}")
    print("-"*70)
    
    for mark_type, stats in analysis['mark_type_stats'].items():
        total = stats['total']
        detected = stats['detected']
        missed = stats['missed']
        rate = (detected / total * 100) if total > 0 else 0
        
        # Color coding
        if mark_type in ['filled', 'sloppy']:
            status = "✓ SHOULD DETECT"
            target = "HIGH"
        else:
            status = "✗ SHOULD REJECT"
            target = "LOW"
        
        print(f"{mark_type:<15} {total:<8} {detected:<10} {missed:<8} {rate:6.2f}%  {status}")
    
    print("\n" + "="*70)
    print("RECOMMENDATIONS")
    print("="*70)
    
    # Provide recommendations based on results
    if analysis['false_positives'] > analysis['false_negatives']:
        print("\n⚠ High False Positives - Scanner is too lenient")
        print("   → INCREASE thresholds (fill ratio, circularity, symmetry)")
        print("   → DECREASE max thresholds (aspect ratio, edge density)")
    elif analysis['false_negatives'] > analysis['false_positives']:
        print("\n⚠ High False Negatives - Scanner is too strict")
        print("   → DECREASE thresholds (fill ratio, circularity, symmetry)")
        print("   → INCREASE max thresholds (aspect ratio, edge density)")
    else:
        print("\n✓ Balanced performance")
    
    # Specific mark type recommendations
    stats = analysis['mark_type_stats']
    
    if stats.get('filled', {}).get('missed', 0) > 0:
        print("\n⚠ Missing filled circles - DECREASE fill ratio threshold")
    
    if stats.get('sloppy', {}).get('missed', 0) > 0:
        print("\n⚠ Missing sloppy fills - DECREASE circularity/symmetry thresholds")
    
    if stats.get('tick', {}).get('detected', 0) > 0:
        print("\n⚠ Accepting ticks - INCREASE circularity threshold or DECREASE aspect ratio max")
    
    if stats.get('cross', {}).get('detected', 0) > 0:
        print("\n⚠ Accepting crosses - INCREASE circularity threshold or DECREASE aspect ratio max")
    
    if stats.get('half', {}).get('detected', 0) > 0:
        print("\n⚠ Accepting half circles - INCREASE symmetry threshold")
    
    if stats.get('concentric', {}).get('detected', 0) > 0:
        print("\n⚠ Accepting concentric circles - DECREASE edge density max or INCREASE fill ratio min")
    
    if stats.get('dot', {}).get('detected', 0) > 0:
        print("\n⚠ Accepting dots - INCREASE fill ratio threshold")
    
    print("\n" + "="*70)


def create_sample_scanner_results():
    """
    Create sample scanner results for demonstration
    In real usage, this would come from your actual OMR scanner
    """
    
    # This is just an example - replace with your actual scanner output
    scanner_results = {
        'filled_omr_001_realistic.pdf': {
            'page0_q0': 2,  # Detected option 2 for question 0
            'page0_q1': 0,  # Detected option 0 for question 1
            # ... more questions
        },
        'filled_omr_002_random.pdf': {
            'page0_q0': 1,
            'page0_q2': 3,
            # ... more questions
        }
    }
    
    return scanner_results


def main():
    """Main analysis function"""
    
    if len(sys.argv) < 2:
        print("Usage: python analyze_results.py <metadata_file> [scanner_results_file]")
        print("\nExample:")
        print("  python analyze_results.py generated_omr_samples/generation_metadata.json scanner_output.json")
        print("\nNote: scanner_results_file should be JSON with format:")
        print('  {"filename.pdf": {"page0_q0": 2, "page0_q1": 0, ...}, ...}')
        sys.exit(1)
    
    metadata_file = sys.argv[1]
    
    if not Path(metadata_file).exists():
        print(f"Error: Metadata file not found: {metadata_file}")
        sys.exit(1)
    
    # Load ground truth
    print(f"Loading ground truth from {metadata_file}...")
    ground_truth = load_ground_truth(metadata_file)
    print(f"Loaded {len(ground_truth)} samples")
    
    # Load scanner results
    if len(sys.argv) >= 3:
        scanner_results_file = sys.argv[2]
        if Path(scanner_results_file).exists():
            with open(scanner_results_file, 'r') as f:
                scanner_results = json.load(f)
            print(f"Loaded scanner results from {scanner_results_file}")
        else:
            print(f"Error: Scanner results file not found: {scanner_results_file}")
            sys.exit(1)
    else:
        print("\nNo scanner results provided - using sample data for demonstration")
        scanner_results = create_sample_scanner_results()
    
    # Analyze
    analysis = analyze_scanner_accuracy(ground_truth, scanner_results)
    
    # Print report
    print_analysis_report(analysis)
    
    # Save analysis to file
    output_file = Path(metadata_file).parent / 'analysis_report.json'
    with open(output_file, 'w') as f:
        json.dump(analysis, f, indent=2)
    print(f"\nDetailed analysis saved to: {output_file}")


if __name__ == "__main__":
    main()
