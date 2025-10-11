#!/usr/bin/env python
# working with excel sheets

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import final

import pandas as pd
from pandas.core.frame import DataFrame
from pandas.core.series import Series


# Class to parse given term roster (excel) file and encapsulate all of its data.
# User can use the parser object to get specific information about the roster.
@final
class TermRosterParser:
    """
    Parse the term roster and encapsulate its contained data.

    Attributes:
        roster(pandas.core.frame.DataFrame)
        date_row(int)
        name_to_row(dict[str, int])
    """

    NAME_PART_PATTERN = r"\b(?:[A-Z](?:[a-z]+|[-\'][A-Z][a-z]*)+)\b"
    FULLNAME_PATTERN = rf"(?:{NAME_PART_PATTERN}\s+){{1,}}{NAME_PART_PATTERN}"
    REGEX = re.compile(FULLNAME_PATTERN)

    def __init__(self, roster_file: str | Path):
        if isinstance(roster_file, Path):
            roster_path = roster_file
        else:
            roster_path = Path(roster_file)
        if not roster_path.exists():
            raise FileNotFoundError(f'Path "{roster_file}" does not exist')
        if not roster_path.is_file():
            raise ValueError(f'Path "{roster_file}" exists, but is not a file')

        self.roster: DataFrame = pd.read_excel(
            roster_file, sheet_name=-1, engine="openpyxl"
        )
        self.date_row: int = self.find_date_row()

        # Dbg
        sys.stderr.write(f"Date row @{self.date_row}\n")

        # Get mapping of row header to row number (some row headers are names)
        row_header_to_number: dict[str, int] = self.get_row_header_to_row_number_dict()

        # Dbg
        sys.stderr.write(
            f"row-header-to-number has {len(row_header_to_number)} headers\n"
        )

        # Filter-out all the row headers except ones that are (probably) names.
        # If a row header has more than one name, map each name to same row
        # number.
        self.name_to_row: dict[str, int] = self.filter_names_dict(row_header_to_number)

        # Dbg
        sys.stderr.write(f"name-to-row dict has {len(self.name_to_row)} names\n")


    @staticmethod
    def name_matched(s: str) -> bool:
        matched = False
        if isinstance(s, str):
            match = re.match(r"\b[A-Z][a-z'+]+\s+[A-Z][a-z'-]+\b", s)
            matched = match is not None
        return matched

    def filter_names_dict(self, name_to_row: dict[str, int]) -> dict[str, int]:
        """
        Filter out names from a list of possible names. List is from keys of the
        input dictionary.

        Parameters:
            - names_to_row: dict (possible name -> row number in roster)
        Return value:
            - dict with same format as input dict
            - name -> row number in roster
            - if multiple names found in same row each are mapped to same
              row number

        Names have following recognizable properties:
        - Has First name and last name
        - May/may not have a middle name
        - Names are separated by one/more spaces
        - Each name (part) starts with an uppercase letter
        - Subsequent letters are lowercase or hyphen or single-quote
        - Letter following hyphen or single-quote is uppercase
        """
        results: dict[str, int] = {}
        for string, row in name_to_row.items():
            if not isinstance(string, str):
                continue
            matches = self.REGEX.finditer(string)
            fullnames = [match.group() for match in matches]
            if len(fullnames) > 0:
                for fullname in fullnames:
                    results[fullname] = row
        return results

    def find_date_row(self) -> int:
        """
        Determine the row number (row numbers count upwards from 1) with the dates.
        If we cannot figure this out return 0 to indicate a problem.

        Errors:
            Raise TypeError if computed `date_row` is not an integer.
        """
        date_counts = self.roster.apply(
            lambda l: [isinstance(o, datetime) for o in l].count(True), axis=1
        )
        date_row = date_counts.idxmax()
        if not isinstance(date_row, int):
            raise TypeError(f"{date_row} is not an integer")
        return date_row

    def get_row_header_to_row_number_dict(self) -> dict[str, int]:
        """
        Get a mapping of names of people in roster to row number the name is in.
        NOTE: Not all of these 'names' will be actual names, we have to filter out the
        strings to get the names.
        """
        col_to_count: Series = (
            self.roster.select_dtypes(include="object").map(self.name_matched).sum()
        )
        col = col_to_count.idxmax()
        names_col = self.roster[col]
        return dict(zip(names_col, range(len(names_col))))


if __name__ == "__main__":
    from time import perf_counter

    t_start = perf_counter()
    t_load_times = 0
    ROSTER_DIR = "data"
    results: dict[str, dict[str, str | int | None]] = dict()
    roster_dir = Path(ROSTER_DIR)
    for i, roster_file in enumerate(roster_dir.glob("*.xlsx"), 1):
        print(f"Loading roster #{i}: {roster_file.name}")
        t0 = perf_counter()
        parser = TermRosterParser(roster_file)
        delta = perf_counter() - t0
        t_load_times += delta
        print(f"Done in {delta:.3f} seconds")
        print("------------------------------------------------------------")

        date_row = parser.date_row
        results.setdefault(roster_file.name, {})["date_row"] = (
            date_row if date_row else None
        )

    t_end = perf_counter()
    max_len = max(len(k) for k in results)
    print(f"{'Roster File':^{max_len}s}\t{'Date Row':^8s}")
    for filename, result in sorted(results.items()):
        print(f"{filename:>{max_len}}\t{result['date_row']!s:>8s}")

    print(f"\nProgram took {t_end - t_start - t_load_times:.3f} seconds")
