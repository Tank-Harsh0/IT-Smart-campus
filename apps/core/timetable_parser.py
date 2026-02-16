"""
PDF Timetable Parser for RCTI IT Department
============================================
Parses the department's master timetable PDF into structured slot data.

PDF Format:
- Columns: [Day] | Time | TOLS | IT11 | IT12 | IT13 | IT31 | IT32 | IT33 | IT51 | IT52 | IT53
- Rows grouped by day (MON, TUE, WED, THU, FRI, SAT) — day names are vertical text
- Cell format: SUBJ-INITIALS[ROOM] or SUBJ-BATCH-INITIALS[ROOM]
  e.g. PP-DLL[201A], IIS-IT121-AYL[207], MATH-IT11T1-SPM[201A]
"""

import re
import logging
import pdfplumber

logger = logging.getLogger(__name__)

# Maps class column names to semester numbers
CLASS_SEMESTER_MAP = {
    'IT11': 1, 'IT12': 1, 'IT13': 1,
    'IT21': 2, 'IT22': 2, 'IT23': 2,
    'IT31': 3, 'IT32': 3, 'IT33': 3,
    'IT41': 4, 'IT42': 4, 'IT43': 4,
    'IT51': 5, 'IT52': 5, 'IT53': 5,
    'IT61': 6, 'IT62': 6, 'IT63': 6,
}

# Day abbreviations — includes REVERSED versions (vertical PDF text can extract backwards)
DAY_NORMAL = {'MON': 'MON', 'TUE': 'TUE', 'WED': 'WED', 'THU': 'THU', 'FRI': 'FRI', 'SAT': 'SAT'}
DAY_REVERSED = {'NOM': 'MON', 'EUT': 'TUE', 'DEW': 'WED', 'UHT': 'THU', 'IRF': 'FRI', 'TAS': 'SAT'}
ALL_DAY_CODES = {**DAY_NORMAL, **DAY_REVERSED}

# Standard time slot order per day — used to detect day boundaries
MORNING_SLOTS = {'10:30', '10:00', '09:30', '09:00', '08:30'}

# Regex: SUBJ[-ITxxx]-INITIALS[ROOM]
# Handles: PP-DLL[201A], IIS-IT121-AYL[207], MATH-IT11T1-SPM[201A]
# Group 1 = subject code, Group 2 = batch code (optional, starts with IT), 
# Group 3 = faculty initials, Group 4 = room
CELL_PATTERN = re.compile(
    r'([A-Za-z]+)'                # Subject code (letters only: PP, IIS, MATH)
    r'(?:-(IT\d[A-Za-z0-9]*))?'   # Optional lab batch code (-IT121, -IT11T1)
    r'-([A-Za-z0-9]+)'            # Faculty initials (last segment: DLL, SPM, V1)
    r'\[([^\]]+)\]'               # Room number in brackets [201A]
)

# Regex to extract time ranges like "10:30-11:30" or "02.00-03.00"
TIME_PATTERN = re.compile(r'(\d{1,2})[.:](\d{2})\s*[-–]\s*(\d{1,2})[.:](\d{2})')


def parse_time_range(time_str):
    """Parse '10:30-11:30' or '02.00-03.00' into ('10:30', '11:30') format."""
    if not time_str:
        return None, None
    match = TIME_PATTERN.search(str(time_str))
    if not match:
        return None, None
    sh, sm, eh, em = match.groups()
    start = f"{int(sh):02d}:{sm}"
    end = f"{int(eh):02d}:{em}"
    return start, end


def extract_cell_entries(cell_text):
    """
    Extract all SUBJ-INITIALS[ROOM] entries from a cell.
    Cells may have multiple entries separated by newlines (lab batches).
    Returns list of dicts with subject_code, initials, room, batch_code (or None), is_lab.
    """
    if not cell_text or not cell_text.strip():
        return []
    
    entries = []
    for match in CELL_PATTERN.finditer(cell_text):
        batch_code = match.group(2)  # None if no batch code (lecture)
        entries.append({
            'subject_code': match.group(1).upper(),
            'batch_code': batch_code.upper() if batch_code else None,
            'initials': match.group(3).upper(),
            'room': match.group(4).strip(),
            'is_lab': batch_code is not None,
        })
    return entries


def detect_day(row_cells):
    """
    Check if any cell in the row contains a day name.
    Handles both normal (MON) and reversed (NOM) day names from vertical PDF text.
    """
    for cell in row_cells:
        if not cell:
            continue
        text = str(cell).strip().upper()
        # Direct match
        if text in ALL_DAY_CODES:
            return ALL_DAY_CODES[text]
        # Check if day name is embedded in the cell
        for code, day in ALL_DAY_CODES.items():
            if code in text:
                return day
    return None


def parse_timetable_pdf(pdf_file):
    """
    Main entry point: parse a PDF timetable and return structured slot data.
    
    Returns:
        (slots, warnings) — list of slot dicts and list of warning strings
    """
    slots = []
    warnings = []
    
    try:
        pdf = pdfplumber.open(pdf_file)
    except Exception as e:
        logger.error(f"Failed to open PDF: {e}")
        return slots, [f"Failed to open PDF: {e}"]
    
    for page_num, page in enumerate(pdf.pages):
        tables = page.extract_tables()
        
        if not tables:
            warnings.append(f"Page {page_num + 1}: No tables found")
            continue
        
        # Use the largest table on the page
        table = max(tables, key=lambda t: len(t) * len(t[0]) if t and t[0] else 0)
        
        if not table or len(table) < 2:
            warnings.append(f"Page {page_num + 1}: Table too small")
            continue
        
        # ── Step 1: Find header row with class columns (IT11, IT12, etc.) ──
        header_row = None
        header_idx = None
        
        for idx, row in enumerate(table):
            row_text = [str(c).strip().upper() if c else '' for c in row]
            class_matches = sum(1 for cell in row_text if cell in CLASS_SEMESTER_MAP)
            if class_matches >= 2:
                header_row = row_text
                header_idx = idx
                break
        
        if header_row is None:
            warnings.append(f"Page {page_num + 1}: Could not find header row with class names")
            continue
        
        # ── Step 2: Map columns ──
        col_class_map = {}  # {col_index: 'IT11'}
        time_col = None
        
        for col_idx, cell in enumerate(header_row):
            clean = cell.strip().upper()
            if clean in CLASS_SEMESTER_MAP:
                col_class_map[col_idx] = clean
            elif 'TIME' in clean:
                time_col = col_idx
        
        # Fallback: if no 'TIME' header found, find the column that has time-like values
        if time_col is None:
            for col_idx in range(min(3, len(header_row))):
                if col_idx in col_class_map:
                    continue
                # Check first few data rows for time patterns
                for check_row in range(header_idx + 1, min(header_idx + 4, len(table))):
                    cell_val = str(table[check_row][col_idx]) if table[check_row][col_idx] else ''
                    if TIME_PATTERN.search(cell_val):
                        time_col = col_idx
                        break
                if time_col is not None:
                    break
        
        if time_col is None:
            time_col = 1  # Last resort: column 1 (observed in real PDFs)
        
        logger.info(f"Page {page_num + 1}: {len(col_class_map)} class columns, time in col {time_col}")
        
        # ── Step 3: Assign days to rows ──
        # The table has 7 time slots per day (TOLS 1-7). Day names appear as
        # vertical text in col 0 at varying positions (not the first row of
        # each day!). Strategy: split rows into day-groups by detecting when
        # TOLS resets to '1', then match each group to a day.
        
        DAY_ORDER = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
        
        # Find the TOLS column (slot number column, usually col 2)
        tols_col = None
        for col_idx, cell in enumerate(header_row):
            if 'TOL' in cell.upper():
                tols_col = col_idx
                break
        
        # Split data rows into day groups using TOLS resets
        day_groups = []   # list of lists: [[row_idx, ...], ...]
        current_group = []
        
        for row_idx in range(header_idx + 1, len(table)):
            row = table[row_idx]
            if not row:
                continue
            
            # Check if this row has a time value (is a data row)
            time_cell = str(row[time_col]).strip() if row[time_col] else ''
            if not TIME_PATTERN.search(time_cell):
                continue  # Skip non-data rows
            
            # Check TOLS value to detect day boundary
            tols_val = ''
            if tols_col is not None and len(row) > tols_col:
                tols_val = str(row[tols_col]).strip() if row[tols_col] else ''
            
            if tols_val == '1' and current_group:
                # TOLS reset to 1 → new day group
                day_groups.append(current_group)
                current_group = []
            
            current_group.append(row_idx)
        
        if current_group:
            day_groups.append(current_group)
        
        # Collect day markers from col 0 for each group
        group_day_markers = {}
        for group_idx, group_rows in enumerate(day_groups):
            for row_idx in group_rows:
                row = table[row_idx]
                detected = detect_day([row[0]] if row else [])
                if detected:
                    group_day_markers[group_idx] = detected
                    break
        
        # Build the row → day map
        row_day_map = {}
        for group_idx, group_rows in enumerate(day_groups):
            # Use marker if found, otherwise use DAY_ORDER position
            if group_idx in group_day_markers:
                day = group_day_markers[group_idx]
            elif group_idx < len(DAY_ORDER):
                day = DAY_ORDER[group_idx]
            else:
                continue  # Extra groups beyond SAT
            
            for row_idx in group_rows:
                row_day_map[row_idx] = day
        
        # ── Step 4: Extract slots from each row ──
        for row_idx in range(header_idx + 1, len(table)):
            row = table[row_idx]
            if not row:
                continue
            
            current_day = row_day_map.get(row_idx)
            if not current_day:
                continue
            
            # Get time
            time_cell = str(row[time_col]).strip() if row[time_col] else ''
            start_time, end_time = parse_time_range(time_cell)
            
            if not start_time:
                continue  # Skip rows without time
            
            # Parse each class column
            for col_idx, class_name in col_class_map.items():
                if col_idx >= len(row):
                    continue
                
                cell_text = str(row[col_idx]) if row[col_idx] else ''
                entries = extract_cell_entries(cell_text)
                semester = CLASS_SEMESTER_MAP[class_name]
                
                for entry in entries:
                    slots.append({
                        'day': current_day,
                        'start_time': start_time,
                        'end_time': end_time,
                        'class_name': class_name,
                        'semester': semester,
                        'subject_code': entry['subject_code'],
                        'initials': entry['initials'],
                        'room': entry['room'],
                        'batch_code': entry['batch_code'],
                        'is_lab': entry['is_lab'],
                    })
    
    pdf.close()
    logger.info(f"Parsed {len(slots)} timetable slots from PDF")
    return slots, warnings
