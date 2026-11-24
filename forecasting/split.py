"""Chronological split. Never shuffle: the model must not see the future."""
VAL_START = "2016-09-01"   # train: before this date
TEST_START = "2016-11-01"  # validation: VAL_START to TEST_START; test: from here on