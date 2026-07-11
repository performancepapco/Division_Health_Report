"""PLI — thin wrapper around the shared PLI/RPLI extraction logic."""
from pipeline.sections import _pli_rpli_common as common

DIVISION_SHEET = "PLI Division Distribution"
DETAIL_SHEET = "PLI Detail"


def validate(section_cfg, path, month_iso):
    return common.validate("pli", section_cfg, path, month_iso, DIVISION_SHEET, DETAIL_SHEET)


def extract(section_cfg, path, month_iso):
    return common.extract(path, DIVISION_SHEET, DETAIL_SHEET)


def merge_cumulative(new_slice, previous_cumulative):
    return common.merge_cumulative(new_slice, previous_cumulative)


def row_count(data):
    return common.row_count(data)
