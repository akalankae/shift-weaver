#!/usr/bin/env python
# working with excel sheets

import sys
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet  # for type checker


def find_date_row(sheet: Worksheet) -> int:
    """
    Determine the row number (row numbers count upwards from 1) with the dates.
    If we cannot figure this out return 0 to indicate a problem.

    MIN_DATE_COLUMNS_IN_ROW is the minimum number of columns next to each other
    in a row with cells having date type values for us to determine that the row
    is the one with dates. For the term roster this number is one half of a pay
    period, which is 7 days.
    """
    MIN_DATE_COLUMNS_IN_ROW = 7
    date_row = 0
    for row in sheet.iter_rows():
        date_count = 0
        for cell in row:
            if cell.is_date:
                date_count += 1
                if date_count == MIN_DATE_COLUMNS_IN_ROW and cell.row:
                    date_row = cell.row
                    break
    return date_row



if __name__ == "__main__":
    from time import perf_counter

    t_start = perf_counter()
    t_load_times = 0
    ROSTER_DIR = "data"
    date_rows: dict[str, int | None] = dict()
    roster_dir = Path(ROSTER_DIR)
    for i, roster_file in enumerate(roster_dir.glob("*.xlsx"), 1):
        print(f"Loading roster #{i}: {roster_file.name}")
        t0 = perf_counter()
        wb = load_workbook(roster_file)
        delta = perf_counter() - t0
        t_load_times += delta
        print(f"Done in {delta:.3f} seconds")
        print("------------------------------------------------------------")
        ws = wb.active
        if not ws:
            sys.stderr.write(f"Couldn't find active sheet of {roster_file.name}\n")
            continue
        date_row = find_date_row(ws)
        date_rows[roster_file.name] = date_row if date_row else None

    t_end = perf_counter()
    max_len = max(len(k) for k in date_rows)
    for filename, date_row in sorted(date_rows.items()):
        print(f"{filename:>{max_len}}: {date_row}")
    print(f"\nProgram took {t_end - t_start - t_load_times:.3f} seconds")
